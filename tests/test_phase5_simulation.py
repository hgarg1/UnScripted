import importlib
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select


def test_phase5_simulation_controls_and_calibration(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "unscripted_phase5.db"
    monkeypatch.setenv("UNSCRIPTED_DATABASE_URL", f"sqlite:///{database_path}")

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
    from services.api.app.models.agent import Agent
    from services.api.app.models.ml import InferenceLog, ModelEvaluation
    from services.api.app.models.simulation import CalibrationSnapshot
    from services.api.app.models.simulation import ExperimentRun, ScenarioInjection

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

        cohorts = client.get("/v1/admin/agent-cohorts", headers=admin_headers)
        assert cohorts.status_code == 200, cohorts.text
        cohort_id = cohorts.json()[0]["id"]

        experiment = client.post(
            "/v1/admin/experiments",
            json={
                "name": "Escalation Stress",
                "scenario_key": "escalation-pressure",
                "target_cohort_id": cohort_id,
                "configuration_json": {"target_model": "conversation-escalation"},
                "start_immediately": True,
            },
            headers=admin_headers,
        )
        assert experiment.status_code == 201, experiment.text
        experiment_id = experiment.json()["id"]

        injection = client.post(
            "/v1/admin/scenario-injections",
            json={
                "experiment_id": experiment_id,
                "target_cohort_id": cohort_id,
                "injection_type": "belief-shift",
                "payload_json": {"delta": [0.4, -0.2, 0.1]},
                "apply_now": True,
            },
            headers=admin_headers,
        )
        assert injection.status_code == 201, injection.text
        injection_id = injection.json()["id"]
        assert injection.json()["state"] == "applied"

        agents = client.get("/v1/admin/agents", headers=admin_headers)
        assert agents.status_code == 200, agents.text
        agent_id = agents.json()["items"][0]["id"]

        with session_module.SessionLocal() as session:
            agent = session.get(Agent, agent_id)
            assert agent is not None
            assert agent.belief_vector[0] != 0.2

        executed = client.post(
            f"/v1/admin/agents/{agent_id}/execute-turn",
            json={"force_action": "reply"},
            headers=admin_headers,
        )
        assert executed.status_code == 200, executed.text

        calibration = client.post(
            "/v1/admin/calibrations/run",
            json={"model_name": "conversation-escalation"},
            headers=admin_headers,
        )
        assert calibration.status_code == 201, calibration.text
        assert calibration.json()["model_name"] == "conversation-escalation"

        report = client.post(
            "/v1/admin/evaluations/conversation-escalation/advanced-report",
            headers=admin_headers,
        )
        assert report.status_code == 200, report.text
        assert report.json()["eval_type"] == "advanced-evaluation-report"

        with session_module.SessionLocal() as session:
            assert session.scalar(select(ExperimentRun).where(ExperimentRun.id == experiment_id)) is not None
            assert session.scalar(select(ScenarioInjection).where(ScenarioInjection.id == injection_id)) is not None
            escalation_log = session.scalar(
                select(InferenceLog).where(InferenceLog.task_type == "conversation-escalation")
            )
            assert escalation_log is not None
            calibration_snapshot = session.scalar(
                select(CalibrationSnapshot).where(CalibrationSnapshot.model_name == "conversation-escalation")
            )
            assert calibration_snapshot is not None
            advanced_eval = session.scalar(
                select(ModelEvaluation).where(ModelEvaluation.eval_type == "advanced-evaluation-report")
            )
            assert advanced_eval is not None
