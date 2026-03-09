from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.db.session import get_db_session
from services.api.app.models import AccountRole
from services.api.app.models.ml import ModelEvaluation
from services.api.app.models.simulation import CalibrationSnapshot, ExperimentRun, ScenarioInjection
from services.api.app.models.social import User
from services.api.app.schemas.simulation import (
    AdvancedEvaluationResponse,
    CalibrationSnapshotResponse,
    CreateExperimentRunRequest,
    CreateScenarioInjectionRequest,
    ExperimentRunResponse,
    RunCalibrationRequest,
    ScenarioInjectionResponse,
)
from services.api.app.services.auth import get_current_user
from services.api.app.services.simulation import (
    apply_scenario_injection,
    create_advanced_evaluation_report,
    create_experiment_run,
    create_scenario_injection,
    run_micro_batch_calibration,
)

router = APIRouter(prefix="/v1/admin", tags=["simulation"])


def _require_admin(user: User) -> None:
    if user.role not in {AccountRole.ADMIN.value, AccountRole.RESEARCHER.value, AccountRole.MODERATOR.value}:
        raise HTTPException(status_code=403, detail="admin access required")


@router.get("/experiments", response_model=list[ExperimentRunResponse])
def list_experiments(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ExperimentRunResponse]:
    _require_admin(current_user)
    rows = list(session.scalars(select(ExperimentRun).order_by(ExperimentRun.created_at.desc())))
    session.commit()
    return [ExperimentRunResponse.model_validate(row) for row in rows]


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
        snapshot = run_micro_batch_calibration(session, model_name=payload.model_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return CalibrationSnapshotResponse.model_validate(snapshot)


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
