from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from workers.temporal.app.activities.agent import request_agent_turn_plan


@workflow.defn
class AgentCadenceWorkflow:
    @workflow.run
    async def run(self, agent_id: str, influence_score: float, pending_mentions: int) -> dict:
        return await workflow.execute_activity(
            request_agent_turn_plan,
            args=[agent_id, influence_score, pending_mentions],
            start_to_close_timeout=timedelta(seconds=30),
        )


@workflow.defn
class RetrainModelWorkflow:
    @workflow.run
    async def run(self, model_name: str) -> dict:
        return {
            "model_name": model_name,
            "status": "scheduled",
            "note": "trainer-batch picks up the actual retraining flow",
        }
