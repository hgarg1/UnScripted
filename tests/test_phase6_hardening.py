import importlib
import asyncio
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select


def test_phase6_control_plane_jobs_and_budget_hard_caps(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "unscripted_phase6.db"
    monkeypatch.setenv("UNSCRIPTED_DATABASE_URL", f"sqlite:///{database_path}")
    monkeypatch.setenv("UNSCRIPTED_AGENT_DAILY_TOKEN_HARD_CAP", "40")
    monkeypatch.setenv("UNSCRIPTED_COHORT_DAILY_TOKEN_HARD_CAP", "200")

    import services.api.app.api.routes.agents as agent_routes_module
    import services.api.app.api.routes.auth as auth_routes_module
    import services.api.app.api.routes.ml as ml_routes_module
    import services.api.app.api.routes.observability as observability_routes_module
    import services.api.app.api.routes.simulation as simulation_routes_module
    import services.api.app.api.routes.social as social_routes_module
    import services.api.app.core.config as config_module
    import services.api.app.db.seed as seed_module
    import services.api.app.db.session as session_module
    import services.api.app.main as main_module
    from services.api.app.models.agent import AgentTurnLog
    from services.api.app.models.simulation import ControlPlaneJob, ExperimentRun

    importlib.reload(config_module)
    importlib.reload(session_module)
    importlib.reload(auth_routes_module)
    importlib.reload(social_routes_module)
    importlib.reload(agent_routes_module)
    importlib.reload(ml_routes_module)
    importlib.reload(observability_routes_module)
    importlib.reload(simulation_routes_module)
    importlib.reload(seed_module)
    importlib.reload(main_module)
    seed_module.seed()

    with TestClient(main_module.app) as client:
        admin_login = client.post(
            "/v1/auth/invite-login",
            json={
                "invite_code": "ADMIN-ROOT",
                "handle": "admin",
                "display_name": "Admin Operator",
                "bio": "admin",
            },
        )
        assert admin_login.status_code == 201, admin_login.text
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['session']['token']}"}

        agents = client.get("/v1/admin/agents", headers=admin_headers)
        assert agents.status_code == 200, agents.text
        agent_id = agents.json()["items"][0]["id"]

        blocked = client.post(
            f"/v1/admin/agents/{agent_id}/execute-turn",
            json={"force_action": "post"},
            headers=admin_headers,
        )
        assert blocked.status_code == 200, blocked.text
        assert blocked.json()["log"]["status"] == "blocked"
        assert "hard cap" in blocked.json()["log"]["reason"]

        experiment = client.post(
            "/v1/admin/experiments",
            json={
                "name": "Managed Tick Test",
                "scenario_key": "escalation-pressure",
                "configuration_json": {"multiplier": 1.4, "target_model": "conversation-escalation"},
                "start_immediately": True,
            },
            headers=admin_headers,
        )
        assert experiment.status_code == 201, experiment.text
        experiment_id = experiment.json()["id"]

        tick = client.post(
            f"/v1/admin/experiments/{experiment_id}/tick",
            json={"include_followup_report": False},
            headers=admin_headers,
        )
        assert tick.status_code == 201, tick.text
        assert tick.json()["workflow_name"] == "scheduled-experiment"
        assert tick.json()["status"] == "completed"

        calibration = client.post(
            "/v1/admin/calibrations/managed-run",
            json={"model_name": "conversation-escalation", "include_report": True},
            headers=admin_headers,
        )
        assert calibration.status_code == 201, calibration.text
        assert calibration.json()["workflow_name"] == "calibration-sweep"

        jobs = client.get("/v1/admin/control-plane/jobs", headers=admin_headers)
        assert jobs.status_code == 200, jobs.text
        assert len(jobs.json()) >= 3

        metrics = client.get("/metrics")
        assert metrics.status_code == 200, metrics.text
        assert "unscripted_outbox_pending" in metrics.text
        assert "unscripted_control_plane_jobs_total" in metrics.text
        assert "unscripted_agent_turn_blocks_total" in metrics.text
        assert "unscripted_last_calibration_timestamp_seconds" in metrics.text

        with session_module.SessionLocal() as session:
            blocked_log = session.scalar(
                select(AgentTurnLog).where(AgentTurnLog.agent_id == agent_id).order_by(AgentTurnLog.created_at.desc())
            )
            assert blocked_log is not None
            assert blocked_log.status == "blocked"
            experiment_row = session.get(ExperimentRun, experiment_id)
            assert experiment_row is not None
            assert int(experiment_row.metrics_json.get("ticks_run", 0)) == 1
            job_rows = list(session.scalars(select(ControlPlaneJob).order_by(ControlPlaneJob.created_at.desc())))
            assert any(row.workflow_name == "agent-cadence" for row in job_rows)
            assert any(row.workflow_name == "scheduled-experiment" for row in job_rows)
            assert any(row.workflow_name == "calibration-sweep" for row in job_rows)


def test_temporal_schedule_bootstrap_registers_dispatch_and_calibration(monkeypatch) -> None:
    monkeypatch.setenv("UNSCRIPTED_BOOTSTRAP_TEMPORAL_SCHEDULES", "true")
    monkeypatch.setenv("UNSCRIPTED_AGENT_DISPATCH_INTERVAL_SECONDS", "30")
    monkeypatch.setenv("UNSCRIPTED_CALIBRATION_INTERVAL_SECONDS", "600")

    import services.api.app.core.config as config_module
    import workers.temporal.app.worker as worker_module

    importlib.reload(config_module)
    importlib.reload(worker_module)

    class FakeClient:
        def __init__(self) -> None:
            self.created_ids: list[str] = []

        async def create_schedule(self, schedule_id: str, schedule) -> None:
            self.created_ids.append(schedule_id)

    fake_client = FakeClient()
    asyncio.run(worker_module.bootstrap_schedules(fake_client))
    assert "unscripted-agent-dispatch" in fake_client.created_ids
    assert "unscripted-calibration-sweep" in fake_client.created_ids
