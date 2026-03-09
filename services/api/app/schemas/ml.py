from datetime import datetime

from pydantic import BaseModel, Field


class ConsumerCheckpointResponse(BaseModel):
    consumer_name: str
    last_event_id: str | None
    last_outbox_id: str | None
    last_event_at: datetime | None
    processed_count: int
    metadata_json: dict
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatasetManifestResponse(BaseModel):
    id: str
    model_name: str
    dataset_ref: str
    provenance_policy: str
    feature_set_version: str
    row_count: int
    status: str
    manifest_json: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelVersionResponse(BaseModel):
    id: str
    model_name: str
    task_type: str
    registry_state: str
    artifact_uri: str
    feature_set_version: str
    training_dataset_ref: str
    metrics_json: dict
    created_at: datetime
    promoted_at: datetime | None

    model_config = {"from_attributes": True}


class ModelEvaluationResponse(BaseModel):
    id: str
    model_version_id: str
    dataset_ref: str
    eval_type: str
    metrics_json: dict
    decision: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InferenceLogResponse(BaseModel):
    id: str
    model_version_id: str | None
    task_type: str
    subject_type: str
    subject_id: str
    request_features_ref: str
    prediction_json: dict
    latency_ms: int
    decision_path: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TrendSnapshotResponse(BaseModel):
    id: str
    window_start: datetime
    window_end: datetime
    topic_key: str
    volume: int
    velocity: float
    synthetic_share: float
    coordination_score: float
    promoted: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class FeatureSnapshotResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    feature_set: str
    feature_version: str
    observed_at: datetime
    features_json: dict
    source_window: str

    model_config = {"from_attributes": True}


class BootstrapModelRequest(BaseModel):
    model_name: str = Field(min_length=3, max_length=120)
    provenance_policy: str = Field(default="mixed", max_length=64)
    registry_state: str | None = Field(default=None, max_length=32)


class PromoteModelRequest(BaseModel):
    registry_state: str = Field(default="active", max_length=32)


class PipelineRunResponse(BaseModel):
    relayed_count: int
    consumed_count: int
    trend_count: int


class ModelRegistryResponse(BaseModel):
    datasets: list[DatasetManifestResponse]
    models: list[ModelVersionResponse]
    evaluations: list[ModelEvaluationResponse]

