from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.core.config import get_settings
from services.api.app.db.session import get_db_session
from services.api.app.models import AccountRole
from services.api.app.models.ml import ModelEvaluation
from services.api.app.models.simulation import CalibrationSnapshot, ControlPlaneJob, ExperimentRun, ScenarioInjection
from services.api.app.models.social import User
from services.api.app.schemas.simulation import (
    AdvancedEvaluationResponse,
    CalibrationSnapshotResponse,
    ControlPlaneJobResponse,
    CreateExperimentRunRequest,
    CreateScenarioInjectionRequest,
    ExperimentRunResponse,
    InternalAgentTurnRequest,
    InternalCalibrationRunRequest,
    InternalExperimentTickRequest,
    ManagedCalibrationRequest,
    ManagedExperimentTickRequest,
    RunCalibrationRequest,
    ScenarioInjectionResponse,
)
from services.api.app.services.auth import get_current_user
from services.api.app.services.simulation import (
    apply_scenario_injection,
    create_advanced_evaluation_report,
    create_control_plane_job,
    create_experiment_run,
    create_scenario_injection,
    list_control_plane_jobs,
    run_micro_batch_calibration,
    run_agent_turn_job,
    run_calibration_job,
    run_experiment_tick_job,
)

router = APIRouter(prefix="/v1/admin", tags=["simulation"])
internal_router = APIRouter(prefix="/v1/internal/control-plane", tags=["internal-control-plane"])
settings = get_settings()


def _require_admin(user: User) -> None:
    if user.role not in {AccountRole.ADMIN.value, AccountRole.RESEARCHER.value, AccountRole.MODERATOR.value}:
        raise HTTPException(status_code=403, detail="admin access required")


def _require_service_token(service_token: str | None) -> None:
    if service_token != settings.service_token:
        raise HTTPException(status_code=401, detail="invalid service token")


@router.get("/experiments", response_model=list[ExperimentRunResponse])
def list_experiments(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ExperimentRunResponse]:
    _require_admin(current_user)
    rows = list(session.scalars(select(ExperimentRun).order_by(ExperimentRun.created_at.desc())))
    session.commit()
    return [ExperimentRunResponse.model_validate(row) for row in rows]


@router.get("/control-plane/jobs", response_model=list[ControlPlaneJobResponse])
def get_control_plane_jobs(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ControlPlaneJobResponse]:
    _require_admin(current_user)
    rows = list_control_plane_jobs(session)
    session.commit()
    return [ControlPlaneJobResponse.model_validate(row) for row in rows]


@router.post("/experiments", response_model=ExperimentRunResponse, status_code=status.HTTP_201_CREATED)
def create_experiment(
    payload: CreateExperimentRunRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ExperimentRunResponse:
    _require_admin(current_user)
    experiment = create_experiment_run(
        session,
        name=payload.name,
        scenario_key=payload.scenario_key,
        target_cohort_id=payload.target_cohort_id,
        configuration_json=payload.configuration_json,
        start_immediately=payload.start_immediately,
    )
    session.commit()
    return ExperimentRunResponse.model_validate(experiment)


@router.get("/scenario-injections", response_model=list[ScenarioInjectionResponse])
def list_injections(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ScenarioInjectionResponse]:
    _require_admin(current_user)
    rows = list(session.scalars(select(ScenarioInjection).order_by(ScenarioInjection.created_at.desc())))
    session.commit()
    return [ScenarioInjectionResponse.model_validate(row) for row in rows]


@router.post("/scenario-injections", response_model=ScenarioInjectionResponse, status_code=status.HTTP_201_CREATED)
def create_injection(
    payload: CreateScenarioInjectionRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ScenarioInjectionResponse:
    _require_admin(current_user)
    injection = create_scenario_injection(
        session,
        experiment_id=payload.experiment_id,
        target_cohort_id=payload.target_cohort_id,
        injection_type=payload.injection_type,
        payload_json=payload.payload_json,
        apply_now=payload.apply_now,
    )
    session.commit()
    return ScenarioInjectionResponse.model_validate(injection)


@router.post("/scenario-injections/{injection_id}/apply", response_model=ScenarioInjectionResponse)
def apply_injection(
    injection_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ScenarioInjectionResponse:
    _require_admin(current_user)
    injection = session.get(ScenarioInjection, injection_id)
    if injection is None:
        raise HTTPException(status_code=404, detail="scenario injection not found")
    injection = apply_scenario_injection(session, injection=injection)
    session.commit()
    return ScenarioInjectionResponse.model_validate(injection)


@router.get("/calibrations", response_model=list[CalibrationSnapshotResponse])
def list_calibrations(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[CalibrationSnapshotResponse]:
    _require_admin(current_user)
    rows = list(session.scalars(select(CalibrationSnapshot).order_by(CalibrationSnapshot.created_at.desc()).limit(50)))
    session.commit()
    return [CalibrationSnapshotResponse.model_validate(row) for row in rows]


@router.post("/calibrations/run", response_model=CalibrationSnapshotResponse, status_code=status.HTTP_201_CREATED)
def run_calibration(
    payload: RunCalibrationRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> CalibrationSnapshotResponse:
    _require_admin(current_user)
    try:
        _, snapshot, _ = run_calibration_job(
            session,
            model_name=payload.model_name,
            requested_by=current_user.id,
            include_report=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return CalibrationSnapshotResponse.model_validate(snapshot)


@router.post("/calibrations/managed-run", response_model=ControlPlaneJobResponse, status_code=status.HTTP_201_CREATED)
def run_managed_calibration(
    payload: ManagedCalibrationRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ControlPlaneJobResponse:
    _require_admin(current_user)
    try:
        job, _, _ = run_calibration_job(
            session,
            model_name=payload.model_name,
            requested_by=current_user.id,
            include_report=payload.include_report,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return ControlPlaneJobResponse.model_validate(job)


@router.post("/experiments/{experiment_id}/tick", response_model=ControlPlaneJobResponse, status_code=status.HTTP_201_CREATED)
def run_experiment_tick(
    experiment_id: str,
    payload: ManagedExperimentTickRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ControlPlaneJobResponse:
    _require_admin(current_user)
    try:
        job, _ = run_experiment_tick_job(
            session,
            experiment_id=experiment_id,
            requested_by=current_user.id,
            include_followup_report=payload.include_followup_report,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return ControlPlaneJobResponse.model_validate(job)


@router.post("/evaluations/{model_name}/advanced-report", response_model=AdvancedEvaluationResponse)
def create_advanced_report(
    model_name: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AdvancedEvaluationResponse:
    _require_admin(current_user)
    try:
        evaluation = create_advanced_evaluation_report(session, model_name=model_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return AdvancedEvaluationResponse(
        evaluation_id=evaluation.id,
        model_version_id=evaluation.model_version_id,
        eval_type=evaluation.eval_type,
        metrics_json=evaluation.metrics_json,
        decision=evaluation.decision,
    )


@internal_router.post("/agents/{agent_id}/turn", response_model=ControlPlaneJobResponse)
def run_internal_agent_turn(
    agent_id: str,
    payload: InternalAgentTurnRequest,
    x_unscripted_service_token: str | None = Header(default=None, alias="x-unscripted-service-token"),
    session: Session = Depends(get_db_session),
) -> ControlPlaneJobResponse:
    _require_service_token(x_unscripted_service_token)
    job, _ = run_agent_turn_job(
        session,
        agent_id=agent_id,
        requested_by="service-temporal",
        force_action=payload.force_action,
        target_topic=payload.target_topic,
        job_id=payload.job_id,
    )
    session.commit()
    return ControlPlaneJobResponse.model_validate(job)


@internal_router.post("/experiments/{experiment_id}/tick", response_model=ControlPlaneJobResponse)
def run_internal_experiment_tick(
    experiment_id: str,
    payload: InternalExperimentTickRequest,
    x_unscripted_service_token: str | None = Header(default=None, alias="x-unscripted-service-token"),
    session: Session = Depends(get_db_session),
) -> ControlPlaneJobResponse:
    _require_service_token(x_unscripted_service_token)
    try:
        job, _ = run_experiment_tick_job(
            session,
            experiment_id=experiment_id,
            requested_by="service-temporal",
            include_followup_report=payload.include_followup_report,
            job_id=payload.job_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return ControlPlaneJobResponse.model_validate(job)


@internal_router.post("/calibrations/run", response_model=ControlPlaneJobResponse)
def run_internal_calibration(
    payload: InternalCalibrationRunRequest,
    x_unscripted_service_token: str | None = Header(default=None, alias="x-unscripted-service-token"),
    session: Session = Depends(get_db_session),
) -> ControlPlaneJobResponse:
    _require_service_token(x_unscripted_service_token)
    try:
        job, _, _ = run_calibration_job(
            session,
            model_name=payload.model_name,
            requested_by="service-temporal",
            include_report=payload.include_report,
            job_id=payload.job_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return ControlPlaneJobResponse.model_validate(job)
