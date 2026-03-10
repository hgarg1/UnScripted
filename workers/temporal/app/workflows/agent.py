from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from workers.temporal.app.activities.agent import (
        execute_agent_turn_activity,
        run_agent_dispatch_activity,
        run_calibration_activity,
        run_experiment_tick_activity,
    )


@workflow.defn
class AgentCadenceWorkflow:
    @workflow.run
    async def run(self, agent_id: str, influence_score: float, pending_mentions: int) -> dict:
        return await workflow.execute_activity(
            execute_agent_turn_activity,
            args=[agent_id, None, None],
            start_to_close_timeout=timedelta(seconds=30),
        )


@workflow.defn
class RetrainModelWorkflow:
    @workflow.run
    async def run(self, model_name: str, include_report: bool = True) -> dict:
        return await workflow.execute_activity(
            run_calibration_activity,
            args=[model_name, include_report],
            start_to_close_timeout=timedelta(seconds=60),
        )


@workflow.defn
class AgentDispatchWorkflow:
    @workflow.run
    async def run(self, limit: int = 5) -> dict:
        return await workflow.execute_activity(
            run_agent_dispatch_activity,
            args=[limit],
            start_to_close_timeout=timedelta(seconds=60),
        )


@workflow.defn
class ScheduledExperimentWorkflow:
    @workflow.run
    async def run(self, experiment_id: str, ticks: int = 3, interval_seconds: int = 5) -> list[dict]:
        results: list[dict] = []
        for idx in range(max(1, ticks)):
            results.append(
                await workflow.execute_activity(
                    run_experiment_tick_activity,
                    args=[experiment_id, idx == (ticks - 1)],
                    start_to_close_timeout=timedelta(seconds=60),
                )
            )
            if idx < ticks - 1:
                await workflow.sleep(interval_seconds)
        return results
