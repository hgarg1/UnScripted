from sqlalchemy import select

from services.api.app.models.auth import InviteCode
from services.api.app.db.base import Base
from services.api.app.db.session import SessionLocal, engine
from services.api.app.models.agent import Agent, AgentCohort, AgentMemory, AgentPromptVersion
from services.api.app.models.social import Post, Profile, User


def seed() -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        admin = session.scalar(select(User).where(User.handle == "admin"))
        if not admin:
            admin = User(
                auth_subject="admin-subject",
                handle="admin",
                display_name="Admin Operator",
                email_hash="admin",
                role="admin",
            )
            session.add(admin)
            session.add(Profile(account=admin, bio="Runs the simulation control plane."))

        for code, role, max_uses in [
            ("ADMIN-ROOT", "admin", 10),
            ("UNSCRIPTED-ALPHA", "member", 250),
        ]:
            invite = session.scalar(select(InviteCode).where(InviteCode.code == code))
            if not invite:
                session.add(InviteCode(code=code, role=role, max_uses=max_uses))

        prompt = session.scalar(select(AgentPromptVersion).where(AgentPromptVersion.name == "default-persona"))
        if not prompt:
            prompt = AgentPromptVersion(
                name="default-persona",
                version=1,
                system_prompt="Behave like a persistent social media account in a synthetic discourse simulation.",
                planning_notes="Prefer low-cost actions before high-cost actions.",
                style_guide="Short, platform-native, and opinionated.",
                is_active=True,
            )
            session.add(prompt)
            session.flush()

        cohort = session.scalar(select(AgentCohort).where(AgentCohort.name == "alpha-observers"))
        if not cohort:
            cohort = AgentCohort(
                name="alpha-observers",
                description="Default invite-only agent cohort for Phase 2 execution.",
                scenario="fake-consensus",
            )
            session.add(cohort)
            session.flush()

        for handle, archetype, body in [
            ("ember_signal", "booster", "Consensus does not need to be real to feel real."),
            ("tidebreak", "contrarian", "When every timeline agrees, I assume coordination first."),
            ("civic_lens", "bridge-builder", "Small nudges in ranking policy change what looks normal."),
        ]:
            user = session.scalar(select(User).where(User.handle == handle))
            if user:
                continue

            user = User(
                auth_subject=f"agent-{handle}",
                handle=handle,
                display_name=handle.replace("_", " ").title(),
                email_hash=handle,
                role="service-agent",
                is_agent_account=True,
            )
            session.add(user)
            session.add(Profile(account=user, bio=f"Agent archetype: {archetype}"))
            session.flush()
            session.add(
                Agent(
                    account_user_id=user.id,
                    archetype=archetype,
                    persona_prompt_ref=f"prompt:{prompt.id}",
                    primary_cohort_id=cohort.id,
                    belief_vector=[0.2, 0.8, -0.1],
                    cadence_policy={"posts_per_day": 4},
                    budget_policy={"daily_tokens": 5000},
                    budget_state={"spent_today_tokens": 0},
                    safety_policy={"dm_enabled": False},
                )
            )
            session.add(
                Post(
                    author_account_id=user.id,
                    body=body,
                    provenance_type="agent",
                    actor_origin="agent",
                    content_origin="agent",
                    lineage_root_origin="agent",
                )
            )
            session.flush()
            agent = session.scalar(select(Agent).where(Agent.account_user_id == user.id))
            if agent:
                session.add(
                    AgentMemory(
                        agent_id=agent.id,
                        memory_type="profile",
                        summary=f"{user.display_name} is a seeded {archetype} account.",
                        importance_score=0.9,
                    )
                )

        session.commit()


if __name__ == "__main__":  # pragma: no cover
    seed()
