import httpx
from temporalio import activity

from services.api.app.core.config import get_settings


settings = get_settings()


@activity.defn
async def request_agent_turn_plan(agent_id: str, influence_score: float, pending_mentions: int) -> dict:
    payload = {
        "agent_id": agent_id,
        "influence_score": influence_score,
        "available_budget_tokens": 1000,
        "pending_mentions": pending_mentions,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8010/v1/agents/plan-turn",
            json=payload,
            headers={"x-unscripted-service-token": settings.service_token},
        )
        response.raise_for_status()
        return response.json()
