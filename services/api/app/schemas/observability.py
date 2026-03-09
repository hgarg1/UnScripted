from datetime import datetime

from pydantic import BaseModel


class FactionDetailResponse(BaseModel):
    id: str
    name: str
    origin_type: str
    cohesion_score: float
    visibility: str
    member_count: int
    avg_influence: float
    dominant_archetypes: list[str]
    sample_handles: list[str]
    scenario_mix: list[str]
    belief_centroid: list[float]
    created_at: datetime


class ObservabilityMetricResponse(BaseModel):
    key: str
    value: float
    label: str


class ProvenanceSliceResponse(BaseModel):
    scope: str
    human: int
    agent: int
    mixed: int
    system: int


class ModelRolloutStateResponse(BaseModel):
    registry_state: str
    count: int


class ObservabilityOverviewResponse(BaseModel):
    metrics: list[ObservabilityMetricResponse]
    provenance: list[ProvenanceSliceResponse]
    rollouts: list[ModelRolloutStateResponse]
    factions: list[FactionDetailResponse]
