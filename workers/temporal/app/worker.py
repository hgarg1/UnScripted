import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from services.api.app.core.config import get_settings
from workers.temporal.app.activities.agent import (
    execute_agent_turn_activity,
    request_agent_turn_plan,
    run_calibration_activity,
    run_experiment_tick_activity,
)
from workers.temporal.app.workflows.agent import (
    AgentCadenceWorkflow,
    RetrainModelWorkflow,
    ScheduledExperimentWorkflow,
)


async def main() -> None:
    settings = get_settings()
    client = await Client.connect(settings.temporal_target)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[AgentCadenceWorkflow, RetrainModelWorkflow, ScheduledExperimentWorkflow],
        activities=[
            request_agent_turn_plan,
            execute_agent_turn_activity,
            run_calibration_activity,
            run_experiment_tick_activity,
        ],
    )
    await worker.run()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
