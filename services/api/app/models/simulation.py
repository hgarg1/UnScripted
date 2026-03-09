from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from services.api.app.db.base import Base
from services.api.app.models.common import new_id, utc_now


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"
    __table_args__ = (
        Index("ix_experiment_runs_state_created_at", "state", "created_at"),
        Index("ix_experiment_runs_target_cohort", "target_cohort_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    scenario_key: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    target_cohort_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agent_cohorts.id", ondelete="SET NULL"), nullable=True
    )
    configuration_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ScenarioInjection(Base):
    __tablename__ = "scenario_injections"
    __table_args__ = (
        Index("ix_scenario_injections_state_created_at", "state", "created_at"),
        Index("ix_scenario_injections_target_cohort", "target_cohort_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    experiment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("experiment_runs.id", ondelete="SET NULL"), nullable=True
    )
    target_cohort_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agent_cohorts.id", ondelete="SET NULL"), nullable=True
    )
    injection_type: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CalibrationSnapshot(Base):
    __tablename__ = "calibration_snapshots"
    __table_args__ = (
        Index("ix_calibration_snapshots_model_created_at", "model_name", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    calibration_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    drift_summary_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
