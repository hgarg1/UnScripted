import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def test_social_flow_smoke(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "unscripted.db"
    monkeypatch.setenv("UNSCRIPTED_DATABASE_URL", f"sqlite:///{database_path}")

    import services.api.app.api.routes.auth as auth_routes_module
    import services.api.app.core.config as config_module
    import services.api.app.api.routes.social as social_routes_module
    import services.api.app.db.seed as seed_module
    import services.api.app.db.session as session_module
    import services.api.app.main as main_module

    importlib.reload(config_module)
    importlib.reload(session_module)
    importlib.reload(auth_routes_module)
    importlib.reload(social_routes_module)
    importlib.reload(seed_module)
    importlib.reload(main_module)
    seed_module.seed()

    with TestClient(main_module.app) as client:
        login = client.post(
            "/v1/auth/invite-login",
            json={
                "invite_code": "UNSCRIPTED-ALPHA",
                "handle": "smokeuser",
                "display_name": "Smoke User",
                "bio": "test"
            },
        )
        assert login.status_code == 201
        token = login.json()["session"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        me = client.get("/v1/me", headers=headers)
        assert me.status_code == 200

        post = client.post(
            "/v1/posts",
            json={"body": "hello unscripted"},
            headers=headers | {"Idempotency-Key": "smoke-post"},
        )
        assert post.status_code == 201

        feed = client.get("/v1/feed", headers=headers)
        assert feed.status_code == 200
        body = feed.json()
        assert body["items"]
        assert any(item["post"]["body"] == "hello unscripted" for item in body["items"])

        second_post = client.post(
            "/v1/posts",
            json={"body": "hello unscripted"},
            headers=headers | {"Idempotency-Key": "smoke-post"},
        )
        assert second_post.status_code == 201
        assert second_post.json()["id"] == post.json()["id"]
