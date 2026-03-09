from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.core.auth import RequestActor, get_request_actor
from services.api.app.core.config import get_settings
from services.api.app.db.session import get_db_session
from services.api.app.models.auth import InviteCode, SessionToken
from services.api.app.models.enums import AccountStatus
from services.api.app.models.social import Profile, User


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _default_session_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=14)


def _is_expired(expires_at: datetime) -> bool:
    now = datetime.now(UTC)
    if expires_at.tzinfo is None:
        return expires_at < now.replace(tzinfo=None)
    return expires_at < now


def issue_session(session: Session, *, user: User) -> tuple[str, SessionToken]:
    raw_token = secrets.token_urlsafe(32)
    record = SessionToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=_default_session_expiry(),
    )
    session.add(record)
    session.flush()
    return raw_token, record


def create_or_consume_invite(
    session: Session, *, invite_code: str, handle: str, display_name: str, bio: str, consent_version: str
) -> tuple[User, Profile, SessionToken, str]:
    invite = session.scalar(select(InviteCode).where(InviteCode.code == invite_code))
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="invite code not found")
    if invite.expires_at and invite.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invite code expired")

    user = session.scalar(select(User).where(User.handle == handle))
    if user:
        profile = session.get(Profile, user.id)
        if user.invite_code_id and user.invite_code_id != invite.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invite does not match account")
        if not user.invite_code_id:
            user.invite_code_id = invite.id
    else:
        if invite.use_count >= invite.max_uses:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invite code exhausted")
        user = User(
            auth_subject=f"local:{handle}",
            handle=handle,
            display_name=display_name,
            email_hash=hashlib.sha256(f"{handle}@local".encode("utf-8")).hexdigest(),
            role=invite.role,
            consent_version=consent_version,
            invite_code_id=invite.id,
        )
        profile = Profile(account=user, bio=bio)
        session.add_all([user, profile])
        session.flush()
        invite.use_count += 1

    if user.status != AccountStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="account disabled")

    user.display_name = display_name
    user.consent_version = consent_version
    if profile and bio:
        profile.bio = bio
    raw_token, token_record = issue_session(session, user=user)
    return user, profile, token_record, raw_token


def _resolve_user_from_session(session: Session, token: str) -> User:
    hashed = _hash_token(token)
    token_record = session.scalar(select(SessionToken).where(SessionToken.token_hash == hashed))
    if not token_record or token_record.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session")
    if _is_expired(token_record.expires_at):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session expired")

    token_record.last_used_at = datetime.now(UTC)
    user = session.get(User, token_record.user_id)
    if not user or user.status != AccountStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="account unavailable")
    return user


def get_current_user(
    session: Session = Depends(get_db_session),
    authorization: str | None = Header(default=None, alias="Authorization"),
    actor: RequestActor = Depends(get_request_actor),
) -> User:
    settings = get_settings()
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        return _resolve_user_from_session(session, token)

    if settings.env == "development":
        from services.api.app.services.accounts import ensure_user_for_actor

        return ensure_user_for_actor(session, actor)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")


def get_active_session_token(
    session: Session = Depends(get_db_session),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> SessionToken:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
    token = authorization.removeprefix("Bearer ").strip()
    hashed = _hash_token(token)
    token_record = session.scalar(select(SessionToken).where(SessionToken.token_hash == hashed))
    if not token_record or token_record.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session")
    return token_record
