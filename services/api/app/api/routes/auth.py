from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from services.api.app.db.session import get_db_session
from services.api.app.models.social import Profile
from services.api.app.schemas.auth import (
    AuthenticatedUserResponse,
    InviteCodeResponse,
    InviteLoginRequest,
    LogoutResponse,
    SessionResponse,
)
from services.api.app.services.auth import (
    create_or_consume_invite,
    get_active_session_token,
    get_current_user,
)
from services.api.app.services.events import append_event

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def _build_auth_response(user, profile, raw_token, token_record) -> AuthenticatedUserResponse:
    return AuthenticatedUserResponse(
        id=user.id,
        handle=user.handle,
        display_name=user.display_name,
        role=user.role,
        bio=profile.bio if profile else "",
        is_agent_account=user.is_agent_account,
        session=SessionResponse(token=raw_token, expires_at=token_record.expires_at),
    )


@router.post("/invite-login", response_model=AuthenticatedUserResponse, status_code=status.HTTP_201_CREATED)
def invite_login(
    payload: InviteLoginRequest,
    session: Session = Depends(get_db_session),
) -> AuthenticatedUserResponse:
    user, profile, token_record, raw_token = create_or_consume_invite(
        session,
        invite_code=payload.invite_code,
        handle=payload.handle,
        display_name=payload.display_name,
        bio=payload.bio,
        consent_version=payload.consent_version,
    )
    append_event(
        session,
        aggregate_type="session",
        aggregate_id=token_record.id,
        actor_type="human",
        actor_id=user.id,
        event_type="session_issued",
        provenance_type="human",
        payload={"invite_code": payload.invite_code, "role": user.role},
    )
    session.commit()
    return _build_auth_response(user, profile, raw_token, token_record)


@router.get("/session", response_model=AuthenticatedUserResponse)
def get_session(
    user=Depends(get_current_user),
    token_record=Depends(get_active_session_token),
    session: Session = Depends(get_db_session),
) -> AuthenticatedUserResponse:
    profile = session.get(Profile, user.id)
    session.commit()
    return _build_auth_response(user, profile, "redacted", token_record)


@router.post("/logout", response_model=LogoutResponse)
def logout(
    token_record=Depends(get_active_session_token),
    session: Session = Depends(get_db_session),
) -> LogoutResponse:
    token_record.revoked_at = datetime.now(UTC)
    session.commit()
    return LogoutResponse(revoked=True)
