from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from services.api.app.db.session import get_db_session
from services.api.app.models import AccountRole
from services.api.app.models.game import GuessGameGuess
from services.api.app.models.ml import TrendSnapshot
from services.api.app.models.social import User
from services.api.app.schemas.game import (
    GuessGameScoreResponse,
    GuessResultResponse,
    GuessableAccountResponse,
    GuessableAccountsResponse,
    SubmitGuessRequest,
)
from services.api.app.schemas.observability import FactionDetailResponse, ObservabilityOverviewResponse
from services.api.app.services.auth import get_current_user
from services.api.app.services.observability import (
    build_guess_score,
    build_observability_overview,
    list_factions,
    list_guessable_accounts,
    rebuild_factions,
)

router = APIRouter(prefix="/v1", tags=["observability"])


def _require_admin(user: User) -> None:
    if user.role not in {AccountRole.ADMIN.value, AccountRole.RESEARCHER.value, AccountRole.MODERATOR.value}:
        raise HTTPException(status_code=403, detail="admin access required")


@router.get("/admin/observability/overview", response_model=ObservabilityOverviewResponse)
def get_observability_overview(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ObservabilityOverviewResponse:
    _require_admin(current_user)
    response = build_observability_overview(session)
    session.commit()
    return ObservabilityOverviewResponse(**response)


@router.get("/admin/factions", response_model=list[FactionDetailResponse])
def get_factions(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[FactionDetailResponse]:
    _require_admin(current_user)
    rows = list_factions(session)
    session.commit()
    return [FactionDetailResponse(**row) for row in rows]


@router.post("/admin/factions/rebuild", response_model=list[FactionDetailResponse])
def rebuild_faction_assignments(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[FactionDetailResponse]:
    _require_admin(current_user)
    rows = rebuild_factions(session)
    session.commit()
    return [FactionDetailResponse(**row) for row in rows]


@router.get("/trends", response_model=list[dict])
def get_public_trends(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    _ = current_user
    rows = list(
        session.scalars(
            select(TrendSnapshot).where(TrendSnapshot.promoted.is_(True)).order_by(desc(TrendSnapshot.created_at)).limit(12)
        )
    )
    session.commit()
    return [
        {
            "id": row.id,
            "topic_key": row.topic_key,
            "volume": row.volume,
            "synthetic_share": row.synthetic_share,
            "coordination_score": row.coordination_score,
            "promoted": row.promoted,
        }
        for row in rows
    ]


@router.get("/game/guessable-accounts", response_model=GuessableAccountsResponse)
def get_guessable_accounts(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> GuessableAccountsResponse:
    items = list_guessable_accounts(session, viewer_id=current_user.id)
    session.commit()
    return GuessableAccountsResponse(items=[GuessableAccountResponse(**item) for item in items])


@router.get("/game/score", response_model=GuessGameScoreResponse)
def get_guess_score(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> GuessGameScoreResponse:
    response = build_guess_score(session, viewer_id=current_user.id)
    session.commit()
    return GuessGameScoreResponse(**response)


@router.post("/game/guesses", response_model=GuessResultResponse)
def submit_guess(
    payload: SubmitGuessRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> GuessResultResponse:
    target = session.get(User, payload.target_account_id)
    if target is None:
        raise HTTPException(status_code=404, detail="account not found")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="cannot guess self")

    existing = session.scalar(
        select(GuessGameGuess).where(
            GuessGameGuess.user_id == current_user.id,
            GuessGameGuess.target_account_id == target.id,
        )
    )
    was_correct = payload.guessed_is_agent == target.is_agent_account
    if existing is None:
        guess = GuessGameGuess(
            user_id=current_user.id,
            target_account_id=target.id,
            guessed_is_agent=payload.guessed_is_agent,
            was_correct=was_correct,
        )
        session.add(guess)
        session.commit()
        session.refresh(guess)
    else:
        existing.guessed_is_agent = payload.guessed_is_agent
        existing.was_correct = was_correct
        session.commit()
        guess = existing
    return GuessResultResponse(
        id=guess.id,
        target_account_id=target.id,
        guessed_is_agent=guess.guessed_is_agent,
        was_correct=guess.was_correct,
        actual_account_type="agent" if target.is_agent_account else "human",
        created_at=guess.created_at,
    )
