from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ml.common.bootstrap_pipeline import MODEL_CATALOG, ensure_bootstrap_models, train_bootstrap_model
from services.api.app.db.session import get_db_session
from services.api.app.models import AccountRole
from services.api.app.models.ml import (
    ConsumerCheckpoint,
    DatasetManifest,
    FeatureSnapshot,
    InferenceLog,
    ModelEvaluation,
    ModelVersion,
    TrendSnapshot,
)
from services.api.app.models.social import User
from services.api.app.schemas.ml import (
    BootstrapModelRequest,
    ConsumerCheckpointResponse,
    DatasetManifestResponse,
    FeatureSnapshotResponse,
    InferenceLogResponse,
    ModelEvaluationResponse,
    ModelRegistryResponse,
    ModelVersionResponse,
    PipelineRunResponse,
    PromoteModelRequest,
    TrendSnapshotResponse,
)
from services.api.app.services.auth import get_current_user
from services.api.app.services.ml import promote_model
from services.api.app.services.pipeline import run_pipeline_cycle

router = APIRouter(prefix="/v1/admin", tags=["ml"])


def _require_admin(user: User) -> None:
    if user.role not in {AccountRole.ADMIN.value, AccountRole.RESEARCHER.value, AccountRole.MODERATOR.value}:
        raise HTTPException(status_code=403, detail="admin access required")


@router.post("/pipeline/run-cycle", response_model=PipelineRunResponse)
def run_pipeline(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> PipelineRunResponse:
    _require_admin(current_user)
    relayed, consumed, trend_count = run_pipeline_cycle(session)
    return PipelineRunResponse(relayed_count=relayed, consumed_count=consumed, trend_count=trend_count)


@router.get("/pipeline/checkpoints", response_model=list[ConsumerCheckpointResponse])
def list_checkpoints(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ConsumerCheckpointResponse]:
    _require_admin(current_user)
    rows = list(session.scalars(select(ConsumerCheckpoint).order_by(ConsumerCheckpoint.updated_at.desc())))
    session.commit()
    return [ConsumerCheckpointResponse.model_validate(row) for row in rows]


@router.get("/models", response_model=ModelRegistryResponse)
def list_models(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ModelRegistryResponse:
    _require_admin(current_user)
    ensure_bootstrap_models(session)
    session.commit()
    datasets = list(session.scalars(select(DatasetManifest).order_by(DatasetManifest.created_at.desc()).limit(20)))
    models = list(session.scalars(select(ModelVersion).order_by(ModelVersion.created_at.desc()).limit(20)))
    evaluations = list(session.scalars(select(ModelEvaluation).order_by(ModelEvaluation.created_at.desc()).limit(20)))
    session.commit()
    return ModelRegistryResponse(
        datasets=[DatasetManifestResponse.model_validate(row) for row in datasets],
        models=[ModelVersionResponse.model_validate(row) for row in models],
        evaluations=[ModelEvaluationResponse.model_validate(row) for row in evaluations],
    )


@router.post("/models/bootstrap", response_model=ModelVersionResponse, status_code=status.HTTP_201_CREATED)
def bootstrap_model(
    payload: BootstrapModelRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ModelVersionResponse:
    _require_admin(current_user)
    if payload.model_name not in MODEL_CATALOG:
        raise HTTPException(status_code=400, detail="unknown model")
    model = train_bootstrap_model(
        session,
        model_name=payload.model_name,
        provenance_policy=payload.provenance_policy,
        registry_state=payload.registry_state,
    )
    session.commit()
    return ModelVersionResponse.model_validate(model)


@router.post("/models/{model_id}/promote", response_model=ModelVersionResponse)
def promote_model_version(
    model_id: str,
    payload: PromoteModelRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ModelVersionResponse:
    _require_admin(current_user)
    try:
        model = promote_model(session, model_id=model_id, registry_state=payload.registry_state)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    session.commit()
    return ModelVersionResponse.model_validate(model)


@router.get("/model-evaluations", response_model=list[ModelEvaluationResponse])
def list_model_evaluations(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ModelEvaluationResponse]:
    _require_admin(current_user)
    rows = list(session.scalars(select(ModelEvaluation).order_by(ModelEvaluation.created_at.desc()).limit(limit)))
    session.commit()
    return [ModelEvaluationResponse.model_validate(row) for row in rows]


@router.get("/inference-logs", response_model=list[InferenceLogResponse])
def list_inference_logs(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[InferenceLogResponse]:
    _require_admin(current_user)
    rows = list(session.scalars(select(InferenceLog).order_by(InferenceLog.created_at.desc()).limit(limit)))
    session.commit()
    return [InferenceLogResponse.model_validate(row) for row in rows]


@router.get("/trends", response_model=list[TrendSnapshotResponse])
def list_trends(
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[TrendSnapshotResponse]:
    _require_admin(current_user)
    rows = list(session.scalars(select(TrendSnapshot).order_by(desc(TrendSnapshot.created_at)).limit(limit)))
    session.commit()
    return [TrendSnapshotResponse.model_validate(row) for row in rows]


@router.get("/features/{entity_type}/{entity_id}", response_model=list[FeatureSnapshotResponse])
def list_feature_snapshots(
    entity_type: str,
    entity_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[FeatureSnapshotResponse]:
    _require_admin(current_user)
    rows = list(
        session.scalars(
            select(FeatureSnapshot)
            .where(FeatureSnapshot.entity_type == entity_type, FeatureSnapshot.entity_id == entity_id)
            .order_by(FeatureSnapshot.observed_at.desc())
            .limit(limit)
        )
    )
    session.commit()
    return [FeatureSnapshotResponse.model_validate(row) for row in rows]
