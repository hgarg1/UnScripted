import httpx
from temporalio import activity

from services.api.app.core.config import get_settings


settings = get_settings()
API_BASE_URL = "http://localhost:8000"


async def _post(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{API_BASE_URL}{path}",
            json=payload,
            headers={"x-unscripted-service-token": settings.service_token},
        )
        response.raise_for_status()
        return response.json()


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


@activity.defn
async def execute_agent_turn_activity(agent_id: str, force_action: str | None = None, target_topic: str | None = None) -> dict:
    return await _post(
        f"/v1/internal/control-plane/agents/{agent_id}/turn",
        {"force_action": force_action, "target_topic": target_topic},
    )


@activity.defn
async def run_experiment_tick_activity(
    experiment_id: str,
    include_followup_report: bool = False,
) -> dict:
    return await _post(
        f"/v1/internal/control-plane/experiments/{experiment_id}/tick",
        {"include_followup_report": include_followup_report},
    )


@activity.defn
async def run_calibration_activity(model_name: str, include_report: bool = True) -> dict:
    return await _post(
        "/v1/internal/control-plane/calibrations/run",
        {"model_name": model_name, "include_report": include_report},
    )
