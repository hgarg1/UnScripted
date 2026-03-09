import importlib
from pathlib import Path

from fastapi.testclient import TestClient


def test_phase4_observability_and_guessing(tmp_path: Path, monkeypatch) -> None:
    database_path = tmp_path / "unscripted_phase4.db"
    monkeypatch.setenv("UNSCRIPTED_DATABASE_URL", f"sqlite:///{database_path}")

    import services.api.app.api.routes.agents as agent_routes_module
    import services.api.app.api.routes.auth as auth_routes_module
    import services.api.app.api.routes.ml as ml_routes_module
    import services.api.app.api.routes.observability as observability_routes_module
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
    importlib.reload(observability_routes_module)
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
                "handle": "phase4member",
                "display_name": "Phase 4 Member",
                "bio": "observing synthetic discourse",
            },
        )
        assert member_login.status_code == 201, member_login.text
        member_headers = {"Authorization": f"Bearer {member_login.json()['session']['token']}"}

        agents = client.get("/v1/admin/agents", headers=admin_headers)
        assert agents.status_code == 200, agents.text
        agent_items = agents.json()["items"]
        assert len(agent_items) >= 2

        member_post = client.post(
            "/v1/posts",
            json={"body": "phase four should expose trend amplification and faction drift"},
            headers=member_headers | {"Idempotency-Key": "phase4-post"},
        )
        assert member_post.status_code == 201, member_post.text

        first_agent_user_id = agent_items[0]["user_id"]
        second_agent_id = agent_items[1]["id"]

        follow = client.post(
            "/v1/follows",
            json={"target_account_id": first_agent_user_id},
            headers=member_headers | {"Idempotency-Key": "phase4-follow"},
        )
        assert follow.status_code == 201, follow.text

        feed = client.get("/v1/feed", headers=member_headers)
        assert feed.status_code == 200, feed.text
        post_id = feed.json()["items"][0]["post"]["id"]

        like = client.post(
            f"/v1/posts/{post_id}/likes",
            headers=member_headers | {"Idempotency-Key": "phase4-like"},
        )
        assert like.status_code == 201, like.text

        for agent_id, action in [
            (agent_items[0]["id"], "post"),
            (agent_items[1]["id"], "post"),
            (second_agent_id, "reply"),
        ]:
            executed = client.post(
                f"/v1/admin/agents/{agent_id}/execute-turn",
                json={"force_action": action},
                headers=admin_headers,
            )
            assert executed.status_code == 200, executed.text

        for idx in range(3):
            extra_post = client.post(
                "/v1/posts",
                json={"body": f"extra event stream {idx} for promoted trends"},
                headers=member_headers | {"Idempotency-Key": f"phase4-extra-{idx}"},
            )
            assert extra_post.status_code == 201, extra_post.text

        pipeline = client.post("/v1/admin/pipeline/run-cycle", headers=admin_headers)
        assert pipeline.status_code == 200, pipeline.text

        factions = client.post("/v1/admin/factions/rebuild", headers=admin_headers)
        assert factions.status_code == 200, factions.text
        assert factions.json()
        assert factions.json()[0]["member_count"] >= 1

        overview = client.get("/v1/admin/observability/overview", headers=admin_headers)
        assert overview.status_code == 200, overview.text
        overview_payload = overview.json()
        assert overview_payload["metrics"]
        assert overview_payload["provenance"]
        assert overview_payload["factions"]

        public_trends = client.get("/v1/trends", headers=member_headers)
        assert public_trends.status_code == 200, public_trends.text
        assert public_trends.json()

        guessables = client.get("/v1/game/guessable-accounts", headers=member_headers)
        assert guessables.status_code == 200, guessables.text
        target = next((item for item in guessables.json()["items"] if item["handle"] == "ember_signal"), None)
        assert target is not None

        guess = client.post(
            "/v1/game/guesses",
            json={"target_account_id": target["account_id"], "guessed_is_agent": True},
            headers=member_headers,
        )
        assert guess.status_code == 200, guess.text
        assert guess.json()["was_correct"] is True
        assert guess.json()["actual_account_type"] == "agent"

        score = client.get("/v1/game/score", headers=member_headers)
        assert score.status_code == 200, score.text
        assert score.json()["attempts"] == 1
        assert score.json()["correct"] == 1
