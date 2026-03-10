from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.api.app.models.agent import AgentTurnLog
from services.api.app.models.enums import OutboxStatus
from services.api.app.models.eventing import OutboxMessage
from services.api.app.models.ml import ConsumerCheckpoint
from services.api.app.models.simulation import CalibrationSnapshot, ControlPlaneJob, ExperimentRun


def render_metrics(session: Session) -> str:
    lines: list[str] = []
    outbox_pending = session.scalar(
        select(func.count()).select_from(OutboxMessage).where(OutboxMessage.status == OutboxStatus.PENDING.value)
    ) or 0
    _append_metric(lines, "unscripted_outbox_pending", "Pending outbox messages.", "gauge", float(outbox_pending))

    checkpoint = session.get(ConsumerCheckpoint, "projection-consumer")
    lag_seconds = 0.0
    if checkpoint and checkpoint.last_event_at:
        last_event_at = _as_utc(checkpoint.last_event_at)
        lag_seconds = max(0.0, (datetime.now(UTC) - last_event_at).total_seconds())
    _append_metric(lines, "unscripted_consumer_lag_seconds", "Projection consumer lag in seconds.", "gauge", lag_seconds)

    job_counts = Counter(
        row
        for row in session.scalars(select(ControlPlaneJob.status))
    )
    _append_header(lines, "unscripted_control_plane_jobs_total", "Control plane job totals by status.", "gauge")
    for status, count in sorted(job_counts.items()):
        lines.append(f'unscripted_control_plane_jobs_total{{status="{_escape_label(status)}"}} {count}')

    blocked_turns = session.scalar(
        select(func.count()).select_from(AgentTurnLog).where(AgentTurnLog.status == "blocked")
    ) or 0
    _append_metric(
        lines,
        "unscripted_agent_turn_blocks_total",
        "Total agent turns blocked by runtime policy or budgets.",
        "counter",
        float(blocked_turns),
    )

    latest_calibrations = _latest_calibrations_by_model(session)
    _append_header(lines, "unscripted_calibration_sample_size", "Latest calibration sample size by model.", "gauge")
    _append_header(lines, "unscripted_last_calibration_timestamp_seconds", "Latest calibration completion time by model.", "gauge")
    for model_name, snapshot in sorted(latest_calibrations.items()):
        sample_size = float(snapshot.calibration_json.get("sample_size", 0))
        lines.append(f'unscripted_calibration_sample_size{{model="{_escape_label(model_name)}"}} {sample_size}')
        lines.append(
            "unscripted_last_calibration_timestamp_seconds"
            f'{{model="{_escape_label(model_name)}"}} {snapshot.created_at.timestamp():.0f}'
        )

    active_experiments = session.scalar(
        select(func.count()).select_from(ExperimentRun).where(ExperimentRun.state == "active")
    ) or 0
    _append_metric(
        lines,
        "unscripted_active_experiments",
        "Number of active experiments.",
        "gauge",
        float(active_experiments),
    )
    return "\n".join(lines) + "\n"


def _append_metric(lines: list[str], name: str, help_text: str, metric_type: str, value: float) -> None:
    _append_header(lines, name, help_text, metric_type)
    lines.append(f"{name} {value}")


def _append_header(lines: list[str], name: str, help_text: str, metric_type: str) -> None:
    lines.append(f"# HELP {name} {help_text}")
    lines.append(f"# TYPE {name} {metric_type}")


def _latest_calibrations_by_model(session: Session) -> dict[str, CalibrationSnapshot]:
    rows = list(session.scalars(select(CalibrationSnapshot).order_by(CalibrationSnapshot.created_at.desc())))
    latest: dict[str, CalibrationSnapshot] = {}
    for row in rows:
        latest.setdefault(row.model_name, row)
    return latest


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
