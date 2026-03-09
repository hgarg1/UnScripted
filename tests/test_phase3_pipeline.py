import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def test_phase3_pipeline_and_models(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "unscripted_phase3.db"
    monkeypatch.setenv("UNSCRIPTED_DATABASE_URL", f"sqlite:///{database_path}")

    import services.api.app.api.routes.agents as agent_routes_module
    import services.api.app.api.routes.auth as auth_routes_module
    import services.api.app.api.routes.ml as ml_routes_module
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
    importlib.reload(ml_routes_module)
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

        member_login = client.post(
            "/v1/auth/invite-login",
            json={
                "invite_code": "UNSCRIPTED-ALPHA",
                "handle": "phase3member",
                "display_name": "Phase 3 Member",
                "bio": "testing pipeline",
            },
        )
        assert member_login.status_code == 201, member_login.text
        member_headers = {"Authorization": f"Bearer {member_login.json()['session']['token']}"}

        created_post = client.post(
            "/v1/posts",
            json={"body": "ranking pressure and synthetic agent drift should be observable"},
            headers=member_headers | {"Idempotency-Key": "phase3-post"},
        )
        assert created_post.status_code == 201, created_post.text

        models = client.get("/v1/admin/models", headers=admin_headers)
        assert models.status_code == 200, models.text
        model_payload = models.json()
        assert len(model_payload["models"]) >= 3
        assert len(model_payload["datasets"]) >= 3

        pipeline = client.post("/v1/admin/pipeline/run-cycle", headers=admin_headers)
        assert pipeline.status_code == 200, pipeline.text
        assert pipeline.json()["relayed_count"] >= 1
        assert pipeline.json()["consumed_count"] >= 1

        checkpoints = client.get("/v1/admin/pipeline/checkpoints", headers=admin_headers)
        assert checkpoints.status_code == 200
        assert checkpoints.json()[0]["processed_count"] >= 1

        feed = client.get("/v1/feed", headers=member_headers)
        assert feed.status_code == 200, feed.text
        assert feed.json()["items"]

        inference_logs = client.get("/v1/admin/inference-logs", headers=admin_headers)
        assert inference_logs.status_code == 200, inference_logs.text
        task_types = {row["task_type"] for row in inference_logs.json()}
        assert "coordination-anomaly" in task_types
        assert any(task.startswith("feed-ranking") for task in task_types)

        trends = client.get("/v1/admin/trends", headers=admin_headers)
        assert trends.status_code == 200, trends.text
        assert any(row["topic_key"] == "global" for row in trends.json())

        features = client.get("/v1/admin/features/global/platform", headers=admin_headers)
        assert features.status_code == 200, features.text
        assert features.json()[0]["feature_set"] == "event-window"
