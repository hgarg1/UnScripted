from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from services.api.app.db.base import Base
from services.api.app.models.common import new_id, utc_now


class GuessGameGuess(Base):
    __tablename__ = "guess_game_guesses"
    __table_args__ = (
        UniqueConstraint("user_id", "target_account_id", name="uq_guess_game_guesses_user_target"),
        Index("ix_guess_game_guesses_user_created_at", "user_id", "created_at"),
        Index("ix_guess_game_guesses_target_created_at", "target_account_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    guessed_is_agent: Mapped[bool] = mapped_column(Boolean, nullable=False)
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
