import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def test_phase2_agent_admin_flow(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "unscripted_agents.db"
    monkeypatch.setenv("UNSCRIPTED_DATABASE_URL", f"sqlite:///{database_path}")

    import services.api.app.api.routes.agents as agent_routes_module
    import services.api.app.api.routes.auth as auth_routes_module
    import services.api.app.api.routes.social as social_routes_module
    import services.api.app.core.config as config_module
    import services.api.app.db.seed as seed_module
    import services.api.app.db.session as session_module
    import services.api.app.main as main_module

    importlib.reload(config_module)
    importlib.reload(session_module)
    importlib.reload(auth_routes_module)
    importlib.reload(social_routes_module)
    importlib.reload(agent_routes_module)
    importlib.reload(seed_module)
    importlib.reload(main_module)
    seed_module.seed()

    with TestClient(main_module.app) as client:
        login = client.post(
            "/v1/auth/invite-login",
            json={
                "invite_code": "ADMIN-ROOT",
                "handle": "admin",
                "display_name": "Admin Operator",
                "bio": "admin",
            },
        )
        assert login.status_code == 201
        token = login.json()["session"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        cohorts = client.get("/v1/admin/agent-cohorts", headers=headers)
        assert cohorts.status_code == 200
        cohort_id = cohorts.json()[0]["id"]

        prompts = client.get("/v1/admin/agent-prompts", headers=headers)
        assert prompts.status_code == 200
        prompt_id = prompts.json()[0]["id"]

        created = client.post(
            "/v1/admin/agents",
            json={
                "handle": "phase2_probe",
                "display_name": "Phase 2 Probe",
                "archetype": "bridge-builder",
                "bio": "Synthetic operator",
                "prompt_version_id": prompt_id,
                "cohort_id": cohort_id,
                "belief_vector": [0.1, 0.3, 0.5],
                "posts_per_day": 3,
                "daily_tokens": 4000,
                "dm_enabled": False,
            },
            headers=headers,
        )
        assert created.status_code == 201, created.text
        agent_id = created.json()["id"]

        executed = client.post(
            f"/v1/admin/agents/{agent_id}/execute-turn",
            json={"force_action": "post"},
            headers=headers,
        )
        assert executed.status_code == 200, executed.text
        assert executed.json()["log"]["action"] == "post"
        assert executed.json()["created_post_id"] is not None

        memories = client.get(f"/v1/admin/agents/{agent_id}/memories", headers=headers)
        assert memories.status_code == 200
        assert len(memories.json()["items"]) >= 2

        turns = client.get(f"/v1/admin/agents/{agent_id}/turns", headers=headers)
        assert turns.status_code == 200
        assert turns.json()["items"][0]["action"] == "post"
