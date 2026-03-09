from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from ml.common.agent_planner import AgentTurnContext as PlannerContext
from ml.common.agent_planner import estimate_token_cost, generate_text, plan_turn
from services.api.app.core.config import get_settings


settings = get_settings()
app = FastAPI(title="UnScripted Synthetic Engine")


class AgentTurnContext(BaseModel):
    agent_id: str
    influence_score: float
    available_budget_tokens: int
    pending_mentions: int
    target_topic: str | None = None
    trust_delta: float = 0.0
    hostility_delta: float = 0.0


class AgentTurnPlan(BaseModel):
    action: str
    confidence: float
    should_generate_text: bool
    reason: str


class AgentGeneratedContent(BaseModel):
    action: str
    text: str
    token_cost: int


def _check_service_token(service_token: str | None) -> None:
    if service_token != settings.service_token:
        raise HTTPException(status_code=401, detail="invalid service token")


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/agents/plan-turn", response_model=AgentTurnPlan)
def plan_agent_turn(
    payload: AgentTurnContext,
    x_unscripted_service_token: str | None = Header(default=None, alias="x-unscripted-service-token"),
) -> AgentTurnPlan:
    _check_service_token(x_unscripted_service_token)
    planner_context = PlannerContext(
        agent_id=payload.agent_id,
        handle=payload.agent_id,
        archetype="unspecified",
        influence_score=payload.influence_score,
        available_budget_tokens=payload.available_budget_tokens,
        pending_mentions=payload.pending_mentions,
        recent_engagement=0,
        trust_delta=payload.trust_delta,
        hostility_delta=payload.hostility_delta,
        target_topic=payload.target_topic,
    )
    plan = plan_turn(planner_context)
    return AgentTurnPlan(
        action=plan.action,
        confidence=plan.confidence,
        should_generate_text=plan.should_generate_text,
        reason=plan.reason,
    )


@app.post("/v1/agents/generate-content", response_model=AgentGeneratedContent)
def generate_agent_content(
    payload: AgentTurnContext,
    x_unscripted_service_token: str | None = Header(default=None, alias="x-unscripted-service-token"),
) -> AgentGeneratedContent:
    _check_service_token(x_unscripted_service_token)
    planner_context = PlannerContext(
        agent_id=payload.agent_id,
        handle=payload.agent_id,
        archetype="unspecified",
        influence_score=payload.influence_score,
        available_budget_tokens=payload.available_budget_tokens,
        pending_mentions=payload.pending_mentions,
        recent_engagement=0,
        trust_delta=payload.trust_delta,
        hostility_delta=payload.hostility_delta,
        target_topic=payload.target_topic,
    )
    plan = plan_turn(planner_context)
    text = generate_text(planner_context, plan)
    return AgentGeneratedContent(action=plan.action, text=text, token_cost=estimate_token_cost(plan, text))
