from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ml.common.scoring import calibrate_prediction
from services.api.app.models.agent import Agent, AgentCohort, AgentMemory
from services.api.app.models.common import utc_now
from services.api.app.models.eventing import Event
from services.api.app.models.ml import InferenceLog, ModelEvaluation, ModelVersion
from services.api.app.models.simulation import CalibrationSnapshot, ControlPlaneJob, ExperimentRun, ScenarioInjection
from services.api.app.models.social import User
from services.api.app.services.events import append_event


def create_experiment_run(
    session: Session,
    *,
    name: str,
    scenario_key: str,
    target_cohort_id: str | None,
    configuration_json: dict,
    start_immediately: bool,
) -> ExperimentRun:
    experiment = ExperimentRun(
        name=name,
        scenario_key=scenario_key,
        target_cohort_id=target_cohort_id,
        configuration_json=configuration_json,
        state="active" if start_immediately else "draft",
        started_at=utc_now() if start_immediately else None,
    )
    session.add(experiment)
    session.flush()
    return experiment


def list_control_plane_jobs(session: Session, *, limit: int = 50) -> list[ControlPlaneJob]:
    return list(
        session.scalars(select(ControlPlaneJob).order_by(ControlPlaneJob.created_at.desc()).limit(limit))
    )


def create_control_plane_job(
    session: Session,
    *,
    workflow_name: str,
    job_type: str,
    target_ref: str,
    requested_by: str,
    payload_json: dict,
) -> ControlPlaneJob:
    job = ControlPlaneJob(
        workflow_name=workflow_name,
        job_type=job_type,
        target_ref=target_ref,
        requested_by=requested_by,
        payload_json=payload_json,
        result_json={},
    )
    session.add(job)
    session.flush()
    return job


def mark_control_plane_job_running(session: Session, *, job: ControlPlaneJob) -> ControlPlaneJob:
    job.status = "running"
    job.started_at = utc_now()
    session.flush()
    return job


def complete_control_plane_job(session: Session, *, job: ControlPlaneJob, result_json: dict) -> ControlPlaneJob:
    job.status = "completed"
    job.result_json = result_json
    job.finished_at = utc_now()
    job.error_message = None
    session.flush()
    return job


def fail_control_plane_job(session: Session, *, job: ControlPlaneJob, error_message: str) -> ControlPlaneJob:
    job.status = "failed"
    job.error_message = error_message
    job.finished_at = utc_now()
    session.flush()
    return job


def create_scenario_injection(
    session: Session,
    *,
    experiment_id: str | None,
    target_cohort_id: str | None,
    injection_type: str,
    payload_json: dict,
    apply_now: bool,
) -> ScenarioInjection:
    injection = ScenarioInjection(
        experiment_id=experiment_id,
        target_cohort_id=target_cohort_id,
        injection_type=injection_type,
        payload_json=payload_json,
        state="applied" if apply_now else "pending",
        applied_at=utc_now() if apply_now else None,
    )
    session.add(injection)
    session.flush()
    if apply_now:
        apply_scenario_injection(session, injection=injection)
    return injection


def apply_scenario_injection(session: Session, *, injection: ScenarioInjection) -> ScenarioInjection:
    agents = _target_agents(session, injection.target_cohort_id)
    for agent, user, cohort in agents:
        if injection.injection_type == "belief-shift":
            delta = injection.payload_json.get("delta", [])
            agent.belief_vector = _apply_vector_delta(agent.belief_vector, delta)
        elif injection.injection_type == "cadence-spike":
            multiplier = float(injection.payload_json.get("multiplier", 1.5))
            posts_per_day = float(agent.cadence_policy.get("posts_per_day", 1))
            agent.cadence_policy = {**agent.cadence_policy, "posts_per_day": round(posts_per_day * multiplier, 2)}
        elif injection.injection_type == "budget-boost":
            delta_tokens = int(injection.payload_json.get("delta_tokens", 500))
            daily_tokens = int(agent.budget_policy.get("daily_tokens", 0))
            agent.budget_policy = {**agent.budget_policy, "daily_tokens": daily_tokens + delta_tokens}
        elif injection.injection_type == "scenario-override":
            new_scenario = str(injection.payload_json.get("scenario", "baseline"))
            if cohort is not None:
                cohort.scenario = new_scenario

        session.add(
            AgentMemory(
                agent_id=agent.id,
                memory_type="scenario",
                summary=f"injection {injection.injection_type} applied",
                importance_score=0.75,
                metadata_json={"injection_id": injection.id, "payload": injection.payload_json},
            )
        )
        append_event(
            session,
            aggregate_type="agent",
            aggregate_id=agent.id,
            actor_type="system",
            actor_id=user.id,
            event_type="scenario_injected",
            provenance_type="system",
            payload={"injection_id": injection.id, "injection_type": injection.injection_type},
        )

    injection.state = "applied"
    injection.applied_at = utc_now()
    session.flush()
    return injection


def active_scenario_pressure(session: Session, *, agent: Agent) -> tuple[float, str | None]:
    if not agent.primary_cohort_id:
        return 0.0, None
    rows = list(
        session.scalars(
            select(ScenarioInjection)
            .where(
                ScenarioInjection.target_cohort_id == agent.primary_cohort_id,
                ScenarioInjection.state == "applied",
            )
            .order_by(ScenarioInjection.applied_at.desc(), ScenarioInjection.created_at.desc())
            .limit(5)
        )
    )
    if not rows:
        return 0.0, None
    pressure = 0.0
    latest_type = rows[0].injection_type
    for row in rows:
        if row.injection_type == "belief-shift":
            pressure += 0.15
        elif row.injection_type == "cadence-spike":
            pressure += 0.2
        elif row.injection_type == "budget-boost":
            pressure += 0.1
        elif row.injection_type == "scenario-override":
            pressure += 0.25
    return min(1.0, pressure), latest_type


def run_micro_batch_calibration(session: Session, *, model_name: str) -> CalibrationSnapshot:
    now = datetime.now(UTC)
    window_start = now - timedelta(hours=4)
    model_versions = list(session.scalars(select(ModelVersion).where(ModelVersion.model_name == model_name)))
    if not model_versions:
        raise ValueError("model not found")
    model_ids = [row.id for row in model_versions]
    logs = list(
        session.scalars(
            select(InferenceLog)
            .where(
                InferenceLog.model_version_id.in_(model_ids) if model_ids else False,
                InferenceLog.created_at >= window_start,
            )
        )
    )
    recent_scores = [
        float(log.prediction_json.get("score", 0.0))
        for log in logs
        if isinstance(log.prediction_json, dict)
    ]
    avg_score = sum(recent_scores) / len(recent_scores) if recent_scores else 0.0
    offset = round(0.5 - avg_score, 4) if recent_scores else 0.0
    scale = round(1.0 + min(0.15, len(logs) / 500.0), 4)
    snapshot = CalibrationSnapshot(
        model_name=model_name,
        window_start=window_start,
        window_end=now,
        calibration_json={"offset": offset, "scale": scale, "sample_size": len(logs)},
        drift_summary_json={
            "avg_score": round(avg_score, 4),
            "prediction_volume": len(logs),
            "window_hours": 4,
        },
    )
    session.add(snapshot)
    session.flush()

    active_model = session.scalar(
        select(ModelVersion).where(ModelVersion.model_name == model_name, ModelVersion.registry_state == "active")
    )
    evaluation = ModelEvaluation(
        model_version_id=active_model.id if active_model else model_versions[0].id,
        dataset_ref=f"calibration:{model_name}:{window_start.isoformat()}",
        eval_type="micro-batch-calibration",
        metrics_json={"offset": offset, "scale": scale, "sample_size": len(logs)},
        decision="pass" if len(logs) >= 1 else "review",
    )
    session.add(evaluation)
    session.flush()
    return snapshot


def run_calibration_job(
    session: Session,
    *,
    model_name: str,
    requested_by: str,
    include_report: bool = True,
    job_id: str | None = None,
) -> tuple[ControlPlaneJob, CalibrationSnapshot, ModelEvaluation | None]:
    job = session.get(ControlPlaneJob, job_id) if job_id else None
    if job is None:
        job = create_control_plane_job(
            session,
            workflow_name="calibration-sweep",
            job_type="model-calibration",
            target_ref=model_name,
            requested_by=requested_by,
            payload_json={"model_name": model_name, "include_report": include_report},
        )
    mark_control_plane_job_running(session, job=job)
    try:
        snapshot = run_micro_batch_calibration(session, model_name=model_name)
        evaluation = create_advanced_evaluation_report(session, model_name=model_name) if include_report else None
        complete_control_plane_job(
            session,
            job=job,
            result_json={
                "model_name": model_name,
                "calibration_id": snapshot.id,
                "evaluation_id": evaluation.id if evaluation else None,
                "sample_size": snapshot.calibration_json.get("sample_size", 0),
            },
        )
        return job, snapshot, evaluation
    except Exception as exc:
        fail_control_plane_job(session, job=job, error_message=str(exc))
        raise


def run_agent_turn_job(
    session: Session,
    *,
    agent_id: str,
    requested_by: str,
    force_action: str | None = None,
    target_topic: str | None = None,
    job_id: str | None = None,
) -> tuple[ControlPlaneJob, object]:
    from services.api.app.services.agents import execute_agent_turn

    job = session.get(ControlPlaneJob, job_id) if job_id else None
    if job is None:
        job = create_control_plane_job(
            session,
            workflow_name="agent-cadence",
            job_type="agent-turn",
            target_ref=agent_id,
            requested_by=requested_by,
            payload_json={"agent_id": agent_id, "force_action": force_action, "target_topic": target_topic},
        )
    mark_control_plane_job_running(session, job=job)
    try:
        result = execute_agent_turn(
            session,
            agent_id=agent_id,
            force_action=force_action,
            target_topic=target_topic,
        )
        complete_control_plane_job(
            session,
            job=job,
            result_json={
                "agent_id": agent_id,
                "turn_log_id": result.log.id,
                "turn_status": result.log.status,
                "action": result.log.action,
                "output_ref_type": result.log.output_ref_type,
                "output_ref_id": result.log.output_ref_id,
            },
        )
        return job, result
    except Exception as exc:
        fail_control_plane_job(session, job=job, error_message=str(exc))
        raise


def run_agent_dispatch_job(
    session: Session,
    *,
    requested_by: str,
    limit: int = 5,
    job_id: str | None = None,
) -> tuple[ControlPlaneJob, list[dict[str, str]]]:
    from services.api.app.services.agents import execute_agent_turn

    job = session.get(ControlPlaneJob, job_id) if job_id else None
    if job is None:
        job = create_control_plane_job(
            session,
            workflow_name="agent-dispatch",
            job_type="agent-dispatch",
            target_ref="agents:active",
            requested_by=requested_by,
            payload_json={"limit": limit},
        )
    mark_control_plane_job_running(session, job=job)

    rows = list(
        session.execute(
            select(Agent, AgentCohort)
            .outerjoin(AgentCohort, AgentCohort.id == Agent.primary_cohort_id)
            .where(Agent.state == "active")
            .order_by(Agent.last_active_at.asc(), Agent.influence_score.asc())
            .limit(limit)
        ).all()
    )
    dispatched: list[dict[str, str]] = []
    try:
        for agent, cohort in rows:
            result = execute_agent_turn(
                session,
                agent_id=agent.id,
                target_topic=cohort.scenario if cohort else None,
            )
            dispatched.append(
                {
                    "agent_id": agent.id,
                    "turn_log_id": result.log.id,
                    "status": result.log.status,
                    "action": result.log.action,
                }
            )
        complete_control_plane_job(
            session,
            job=job,
            result_json={
                "dispatch_count": len(dispatched),
                "blocked_count": sum(1 for row in dispatched if row["status"] == "blocked"),
                "turns": dispatched,
            },
        )
        return job, dispatched
    except Exception as exc:
        fail_control_plane_job(session, job=job, error_message=str(exc))
        raise


def create_advanced_evaluation_report(session: Session, *, model_name: str) -> ModelEvaluation:
    model = session.scalar(
        select(ModelVersion)
        .where(ModelVersion.model_name == model_name)
        .order_by(ModelVersion.promoted_at.desc(), ModelVersion.created_at.desc())
    )
    if model is None:
        raise ValueError("model not found")

    calibration = session.scalar(
        select(CalibrationSnapshot)
        .where(CalibrationSnapshot.model_name == model_name)
        .order_by(CalibrationSnapshot.created_at.desc())
    )
    relevant_logs = list(
        session.scalars(
            select(InferenceLog)
            .where(InferenceLog.model_version_id == model.id)
            .order_by(InferenceLog.created_at.desc())
            .limit(200)
        )
    )
    task_breakdown = Counter(log.task_type for log in relevant_logs)
    avg_score = (
        sum(float(log.prediction_json.get("score", 0.0)) for log in relevant_logs if isinstance(log.prediction_json, dict))
        / len(relevant_logs)
        if relevant_logs
        else 0.0
    )
    metrics = {
        "log_volume": len(relevant_logs),
        "avg_score": round(avg_score, 4),
        "task_breakdown": dict(task_breakdown),
        "calibration_offset": calibration.calibration_json.get("offset", 0.0) if calibration else 0.0,
        "calibration_scale": calibration.calibration_json.get("scale", 1.0) if calibration else 1.0,
    }
    evaluation = ModelEvaluation(
        model_version_id=model.id,
        dataset_ref=f"advanced-eval:{model_name}:{datetime.now(UTC).isoformat()}",
        eval_type="advanced-evaluation-report",
        metrics_json=metrics,
        decision="pass" if metrics["log_volume"] >= 1 else "review",
    )
    session.add(evaluation)
    session.flush()
    return evaluation


def run_experiment_tick_job(
    session: Session,
    *,
    experiment_id: str,
    requested_by: str,
    include_followup_report: bool = False,
    job_id: str | None = None,
) -> tuple[ControlPlaneJob, ScenarioInjection]:
    experiment = session.get(ExperimentRun, experiment_id)
    if experiment is None:
        raise ValueError("experiment not found")

    job = session.get(ControlPlaneJob, job_id) if job_id else None
    if job is None:
        job = create_control_plane_job(
            session,
            workflow_name="scheduled-experiment",
            job_type="experiment-tick",
            target_ref=experiment.id,
            requested_by=requested_by,
            payload_json={"experiment_id": experiment.id, "include_followup_report": include_followup_report},
        )
    mark_control_plane_job_running(session, job=job)

    try:
        if experiment.state == "draft":
            experiment.state = "active"
            experiment.started_at = utc_now()

        injection = _build_experiment_injection(
            session,
            experiment=experiment,
            apply_now=True,
        )
        tick_count = int(experiment.metrics_json.get("ticks_run", 0)) + 1
        experiment.metrics_json = {
            **experiment.metrics_json,
            "ticks_run": tick_count,
            "last_tick_at": utc_now().isoformat(),
            "last_job_id": job.id,
            "last_injection_id": injection.id,
        }
        if include_followup_report:
            target_model = str(experiment.configuration_json.get("target_model", "conversation-escalation"))
            report = create_advanced_evaluation_report(session, model_name=target_model)
            experiment.metrics_json["last_followup_evaluation_id"] = report.id

        complete_control_plane_job(
            session,
            job=job,
            result_json={
                "experiment_id": experiment.id,
                "injection_id": injection.id,
                "ticks_run": tick_count,
                "scenario_key": experiment.scenario_key,
            },
        )
        return job, injection
    except Exception as exc:
        fail_control_plane_job(session, job=job, error_message=str(exc))
        raise


def latest_calibration(session: Session, *, model_name: str) -> CalibrationSnapshot | None:
    return session.scalar(
        select(CalibrationSnapshot)
        .where(CalibrationSnapshot.model_name == model_name)
        .order_by(CalibrationSnapshot.created_at.desc())
    )


def calibrated_score(session: Session, *, model_name: str, raw_score: float) -> float:
    calibration = latest_calibration(session, model_name=model_name)
    if calibration is None:
        return raw_score
    calibrated = calibrate_prediction(
        raw_score,
        offset=float(calibration.calibration_json.get("offset", 0.0)),
        scale=float(calibration.calibration_json.get("scale", 1.0)),
    )
    if model_name in {"coordination-anomaly", "conversation-escalation"}:
        return min(1.0, calibrated)
    return calibrated


def _build_experiment_injection(
    session: Session,
    *,
    experiment: ExperimentRun,
    apply_now: bool,
) -> ScenarioInjection:
    injection_type, payload_json = _derive_experiment_injection(experiment)
    return create_scenario_injection(
        session,
        experiment_id=experiment.id,
        target_cohort_id=experiment.target_cohort_id,
        injection_type=injection_type,
        payload_json=payload_json,
        apply_now=apply_now,
    )


def _target_agents(session: Session, target_cohort_id: str | None) -> list[tuple[Agent, User, AgentCohort | None]]:
    stmt = select(Agent, User, AgentCohort).join(User, User.id == Agent.account_user_id).outerjoin(
        AgentCohort, AgentCohort.id == Agent.primary_cohort_id
    )
    if target_cohort_id:
        stmt = stmt.where(Agent.primary_cohort_id == target_cohort_id)
    return list(session.execute(stmt).all())


def _apply_vector_delta(vector: list[float], delta: list[float]) -> list[float]:
    width = max(len(vector), len(delta))
    updated = []
    for idx in range(width):
        lhs = vector[idx] if idx < len(vector) else 0.0
        rhs = delta[idx] if idx < len(delta) else 0.0
        updated.append(round(lhs + rhs, 4))
    return updated


def _derive_experiment_injection(experiment: ExperimentRun) -> tuple[str, dict]:
    config = experiment.configuration_json or {}
    if experiment.scenario_key == "escalation-pressure":
        return "cadence-spike", {"multiplier": float(config.get("multiplier", 1.6))}
    if experiment.scenario_key == "consensus-tilt":
        return "belief-shift", {"delta": config.get("delta", [0.25, -0.05, 0.1])}
    if experiment.scenario_key == "budget-surge":
        return "budget-boost", {"delta_tokens": int(config.get("delta_tokens", 400))}
    return "scenario-override", {"scenario": experiment.scenario_key}
