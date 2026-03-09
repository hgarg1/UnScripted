from datetime import datetime

from pydantic import BaseModel, Field


class ExperimentRunResponse(BaseModel):
    id: str
    name: str
    scenario_key: str
    state: str
    target_cohort_id: str | None
    configuration_json: dict
    metrics_json: dict
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateExperimentRunRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scenario_key: str = Field(min_length=1, max_length=120)
    target_cohort_id: str | None = None
    configuration_json: dict = Field(default_factory=dict)
    start_immediately: bool = True


class ScenarioInjectionResponse(BaseModel):
    id: str
    experiment_id: str | None
    target_cohort_id: str | None
    injection_type: str
    state: str
    payload_json: dict
    applied_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateScenarioInjectionRequest(BaseModel):
    experiment_id: str | None = None
    target_cohort_id: str | None = None
    injection_type: str = Field(min_length=1, max_length=64)
    payload_json: dict = Field(default_factory=dict)
    apply_now: bool = True


class CalibrationSnapshotResponse(BaseModel):
    id: str
    model_name: str
    window_start: datetime
    window_end: datetime
    calibration_json: dict
    drift_summary_json: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class RunCalibrationRequest(BaseModel):
    model_name: str = Field(min_length=3, max_length=120)


class AdvancedEvaluationResponse(BaseModel):
    evaluation_id: str
    model_version_id: str | None
    eval_type: str
    metrics_json: dict
    decision: str
