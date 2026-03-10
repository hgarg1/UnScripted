import asyncio
from datetime import timedelta

from temporalio.client import Client, Schedule, ScheduleActionStartWorkflow, ScheduleIntervalSpec, ScheduleSpec
from temporalio.worker import Worker

from services.api.app.core.config import get_settings
from workers.temporal.app.activities.agent import (
    execute_agent_turn_activity,
    request_agent_turn_plan,
    run_agent_dispatch_activity,
    run_calibration_activity,
    run_experiment_tick_activity,
)
from workers.temporal.app.workflows.agent import (
    AgentDispatchWorkflow,
    AgentCadenceWorkflow,
    RetrainModelWorkflow,
    ScheduledExperimentWorkflow,
)


async def bootstrap_schedules(client: Client) -> None:
    settings = get_settings()
    if not settings.bootstrap_temporal_schedules:
        return

    await _ensure_schedule(
        client,
        schedule_id="unscripted-agent-dispatch",
        schedule=Schedule(
            action=ScheduleActionStartWorkflow(
                AgentDispatchWorkflow.run,
                args=[settings.agent_dispatch_batch_size],
                id="unscripted-agent-dispatch-workflow",
                task_queue=settings.temporal_task_queue,
                static_summary="Dispatch active agents on a fixed cadence.",
            ),
            spec=ScheduleSpec(
                intervals=[ScheduleIntervalSpec(every=timedelta(seconds=settings.agent_dispatch_interval_seconds))]
            ),
        ),
    )
    await _ensure_schedule(
        client,
        schedule_id="unscripted-calibration-sweep",
        schedule=Schedule(
            action=ScheduleActionStartWorkflow(
                RetrainModelWorkflow.run,
                args=[settings.default_calibration_model, False],
                id="unscripted-calibration-sweep-workflow",
                task_queue=settings.temporal_task_queue,
                static_summary="Run periodic calibration over live inference logs.",
            ),
            spec=ScheduleSpec(
                intervals=[ScheduleIntervalSpec(every=timedelta(seconds=settings.calibration_interval_seconds))]
            ),
        ),
    )


async def _ensure_schedule(client: Client, *, schedule_id: str, schedule: Schedule) -> None:
    try:
        await client.create_schedule(schedule_id, schedule)
    except Exception as exc:  # pragma: no cover
        if "already exists" not in str(exc).lower():
            raise


async def main() -> None:
    settings = get_settings()
    client = await Client.connect(settings.temporal_target)
    await bootstrap_schedules(client)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[AgentCadenceWorkflow, AgentDispatchWorkflow, RetrainModelWorkflow, ScheduledExperimentWorkflow],
        activities=[
            request_agent_turn_plan,
            execute_agent_turn_activity,
            run_agent_dispatch_activity,
            run_calibration_activity,
            run_experiment_tick_activity,
        ],
    )
    await worker.run()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
