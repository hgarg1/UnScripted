from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from services.api.app.db.base import Base
from services.api.app.models.common import new_id, utc_now


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (Index("ix_agents_state_last_active", "state", "last_active_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    account_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    archetype: Mapped[str] = mapped_column(String(64), nullable=False)
    persona_prompt_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    belief_vector: Mapped[list[float]] = mapped_column(JSON, default=list, nullable=False)
    influence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cadence_policy: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    budget_policy: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    safety_policy: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Faction(Base):
    __tablename__ = "factions"
    __table_args__ = (Index("ix_factions_cohesion_score", "cohesion_score"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    origin_type: Mapped[str] = mapped_column(String(32), default="seeded", nullable=False)
    belief_centroid: Mapped[list[float]] = mapped_column(JSON, default=list, nullable=False)
    cohesion_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    visibility: Mapped[str] = mapped_column(String(16), default="internal", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Relationship(Base):
    __tablename__ = "relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_account_id", "target_account_id", name="uq_relationships_source_target"
        ),
        Index("ix_relationships_source_affinity", "source_account_id", "affinity_score"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    affinity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trust_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hostility_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_interaction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    relationship_state: Mapped[str] = mapped_column(String(32), default="neutral", nullable=False)
