from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from services.api.app.db.base import Base
from services.api.app.models.common import new_id, utc_now


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        Index("ix_agents_state_last_active", "state", "last_active_at"),
        Index("ix_agents_cohort_state", "primary_cohort_id", "state"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    account_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    archetype: Mapped[str] = mapped_column(String(64), nullable=False)
    persona_prompt_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    primary_cohort_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agent_cohorts.id", ondelete="SET NULL"), nullable=True
    )
    faction_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("factions.id", ondelete="SET NULL"), nullable=True
    )
    belief_vector: Mapped[list[float]] = mapped_column(JSON, default=list, nullable=False)
    influence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cadence_policy: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    budget_policy: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    budget_state: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    safety_policy: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_memory_compacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentPromptVersion(Base):
    __tablename__ = "agent_prompt_versions"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_agent_prompt_versions_name_version"),
        Index("ix_agent_prompt_versions_name_active", "name", "is_active"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    planning_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    style_guide: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentMemory(Base):
    __tablename__ = "agent_memories"
    __table_args__ = (
        Index("ix_agent_memories_agent_type_created_at", "agent_id", "memory_type", "created_at"),
        Index("ix_agent_memories_agent_importance", "agent_id", "importance_score"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    importance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentCohort(Base):
    __tablename__ = "agent_cohorts"
    __table_args__ = (
        Index("ix_agent_cohorts_state_created_at", "state", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    scenario: Mapped[str] = mapped_column(String(120), default="baseline", nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    cadence_multiplier: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    budget_multiplier: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentCohortMembership(Base):
    __tablename__ = "agent_cohort_memberships"
    __table_args__ = (
        UniqueConstraint("cohort_id", "agent_id", name="uq_agent_cohort_memberships"),
        Index("ix_agent_cohort_memberships_agent_id", "agent_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    cohort_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agent_cohorts.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), default="member", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AgentTurnLog(Base):
    __tablename__ = "agent_turn_logs"
    __table_args__ = (
        Index("ix_agent_turn_logs_agent_created_at", "agent_id", "created_at"),
        Index("ix_agent_turn_logs_status_created_at", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    generated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)
    token_cost: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_ref_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    output_ref_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


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
