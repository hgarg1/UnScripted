import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient


def test_social_flow_smoke(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "unscripted.db"
    monkeypatch.setenv("UNSCRIPTED_DATABASE_URL", f"sqlite:///{database_path}")

    import services.api.app.core.config as config_module
    import services.api.app.api.routes.social as social_routes_module
    import services.api.app.db.session as session_module
    import services.api.app.main as main_module

    importlib.reload(config_module)
    importlib.reload(session_module)
    importlib.reload(social_routes_module)
    importlib.reload(main_module)

    headers = {
        "x-unscripted-dev-subject": "smoke-user",
        "x-unscripted-dev-handle": "smokeuser",
        "x-unscripted-dev-name": "Smoke User",
    }

    with TestClient(main_module.app) as client:
        register = client.post(
            "/v1/accounts/register",
            json={"handle": "smokeuser", "display_name": "Smoke User", "bio": "test"},
            headers=headers,
        )
        assert register.status_code == 201

        post = client.post("/v1/posts", json={"body": "hello unscripted"}, headers=headers)
        assert post.status_code == 201

        feed = client.get("/v1/feed", headers=headers)
        assert feed.status_code == 200
        body = feed.json()
        assert body["items"]
        assert body["items"][0]["post"]["body"] == "hello unscripted"
