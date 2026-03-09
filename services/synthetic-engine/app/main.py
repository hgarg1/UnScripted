from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

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

    if payload.available_budget_tokens <= 0:
        return AgentTurnPlan(
            action="disengage",
            confidence=1.0,
            should_generate_text=False,
            reason="budget exhausted",
        )
    if payload.pending_mentions > 0 and payload.trust_delta >= 0:
        return AgentTurnPlan(
            action="reply",
            confidence=0.82,
            should_generate_text=True,
            reason="mentions pending and trust is non-negative",
        )
    if payload.hostility_delta > 0.6:
        return AgentTurnPlan(
            action="escalate",
            confidence=0.7,
            should_generate_text=True,
            reason="hostility threshold exceeded",
        )
    if payload.influence_score < 0.15:
        return AgentTurnPlan(
            action="like",
            confidence=0.65,
            should_generate_text=False,
            reason="low influence agents amplify before posting",
        )
    return AgentTurnPlan(
        action="post",
        confidence=0.74,
        should_generate_text=True,
        reason="default cadence favors original posting",
    )
