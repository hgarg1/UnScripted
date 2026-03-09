from datetime import datetime

from pydantic import BaseModel, Field


class AgentPromptVersionResponse(BaseModel):
    id: str
    name: str
    version: int
    system_prompt: str
    planning_notes: str
    style_guide: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateAgentPromptVersionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    system_prompt: str = Field(min_length=1)
    planning_notes: str = ""
    style_guide: str = ""
    activate: bool = True


class AgentCohortResponse(BaseModel):
    id: str
    name: str
    description: str
    scenario: str
    state: str
    cadence_multiplier: float
    budget_multiplier: float
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateAgentCohortRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    scenario: str = Field(default="baseline", max_length=120)
    cadence_multiplier: float = Field(default=1.0, ge=0.1, le=10.0)
    budget_multiplier: float = Field(default=1.0, ge=0.1, le=10.0)


class CreateAgentRequest(BaseModel):
    handle: str = Field(min_length=3, max_length=40)
    display_name: str = Field(min_length=1, max_length=120)
    archetype: str = Field(min_length=1, max_length=64)
    bio: str = Field(default="", max_length=280)
    prompt_version_id: str | None = None
    cohort_id: str | None = None
    belief_vector: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    posts_per_day: int = Field(default=4, ge=1, le=100)
    daily_tokens: int = Field(default=5000, ge=100, le=100000)
    dm_enabled: bool = False


class AssignAgentCohortRequest(BaseModel):
    cohort_id: str
    role: str = Field(default="member", max_length=32)


class ExecuteAgentTurnRequest(BaseModel):
    force_action: str | None = Field(default=None, max_length=32)
    target_topic: str | None = Field(default=None, max_length=120)


class AgentMemoryResponse(BaseModel):
    id: str
    memory_type: str
    summary: str
    importance_score: float
    metadata_json: dict
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentTurnLogResponse(BaseModel):
    id: str
    action: str
    confidence: float
    reason: str
    generated_text: str | None
    status: str
    token_cost: int
    output_ref_type: str | None
    output_ref_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentResponse(BaseModel):
    id: str
    user_id: str
    handle: str
    display_name: str
    archetype: str
    persona_prompt_ref: str
    primary_cohort_id: str | None
    faction_id: str | None
    influence_score: float
    state: str
    last_active_at: datetime | None
    budget_state: dict
    memory_count: int


class AgentExecutionResponse(BaseModel):
    log: AgentTurnLogResponse
    created_post_id: str | None = None
    created_comment_id: str | None = None
    created_dm_id: str | None = None
    created_follow_target_id: str | None = None
    created_like_target_id: str | None = None


class AgentListResponse(BaseModel):
    items: list[AgentResponse]


class AgentMemoriesResponse(BaseModel):
    items: list[AgentMemoryResponse]


class AgentTurnLogsResponse(BaseModel):
    items: list[AgentTurnLogResponse]
