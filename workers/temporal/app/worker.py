import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from services.api.app.core.config import get_settings
from workers.temporal.app.activities.agent import request_agent_turn_plan
from workers.temporal.app.workflows.agent import AgentCadenceWorkflow, RetrainModelWorkflow


async def main() -> None:
    settings = get_settings()
    client = await Client.connect(settings.temporal_target)
    worker = Worker(
        client,
        task_queue="unscripted-control-plane",
        workflows=[AgentCadenceWorkflow, RetrainModelWorkflow],
        activities=[request_agent_turn_plan],
    )
    await worker.run()


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
