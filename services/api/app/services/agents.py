from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ml.common.agent_planner import AgentTurnContext, AgentTurnPlan, estimate_token_cost, generate_text, plan_turn
from ml.common.scoring import predict_escalation_risk
from services.api.app.models.agent import (
    Agent,
    AgentCohort,
    AgentCohortMembership,
    AgentMemory,
    AgentPromptVersion,
    AgentTurnLog,
)
from services.api.app.models.enums import EventType
from services.api.app.models.ml import ModerationSignal
from services.api.app.models.social import Comment, DM, Follow, Like, Post, Profile, User
from services.api.app.services.events import append_event
from services.api.app.services.ml import latest_feature_snapshot, latest_model_version, log_inference
from services.api.app.services.moderation import maybe_create_signal
from services.api.app.services.simulation import active_scenario_pressure, calibrated_score


@dataclass(frozen=True, slots=True)
class ExecutedAgentTurn:
    log: AgentTurnLog
    post_id: str | None = None
    comment_id: str | None = None
    dm_id: str | None = None
    follow_target_id: str | None = None
    like_target_id: str | None = None


def _latest_prompt(session: Session) -> AgentPromptVersion | None:
    return session.scalar(
        select(AgentPromptVersion)
        .where(AgentPromptVersion.is_active.is_(True))
        .order_by(AgentPromptVersion.created_at.desc())
    )


def _dominant_memory(session: Session, agent_id: str) -> str | None:
    memory = session.scalar(
        select(AgentMemory)
        .where(AgentMemory.agent_id == agent_id)
        .order_by(AgentMemory.importance_score.desc(), AgentMemory.created_at.desc())
    )
    return memory.summary if memory else None


def _available_budget(agent: Agent, cohort: AgentCohort | None) -> int:
    daily_budget = int(agent.budget_policy.get("daily_tokens", 0))
    multiplier = cohort.budget_multiplier if cohort else 1.0
    effective_budget = int(daily_budget * multiplier)
    spent = int(agent.budget_state.get("spent_today_tokens", 0))
    return max(0, effective_budget - spent)


def _pending_mentions(session: Session, user_id: str, last_active_at: datetime | None) -> int:
    stmt = select(func.count()).select_from(Comment).where(Comment.author_account_id != user_id)
    if last_active_at is not None:
        stmt = stmt.where(Comment.created_at >= last_active_at)
    return session.scalar(stmt) or 0


def _recent_engagement(session: Session, user_id: str) -> int:
    authored_posts = select(Post.id).where(Post.author_account_id == user_id)
    like_count = session.scalar(
        select(func.count()).select_from(Like).where(Like.target_type == "post", Like.target_id.in_(authored_posts))
    ) or 0
    return int(like_count)


def _build_context(session: Session, agent: Agent, user: User) -> AgentTurnContext:
    cohort = session.get(AgentCohort, agent.primary_cohort_id) if agent.primary_cohort_id else None
    return AgentTurnContext(
        agent_id=agent.id,
        handle=user.handle,
        archetype=agent.archetype,
        influence_score=agent.influence_score,
        available_budget_tokens=_available_budget(agent, cohort),
        pending_mentions=_pending_mentions(session, user.id, agent.last_active_at),
        recent_engagement=_recent_engagement(session, user.id),
        target_topic=(cohort.scenario if cohort else None),
        dominant_memory=_dominant_memory(session, agent.id),
    )


def _ensure_memory(session: Session, agent_id: str, memory_type: str, summary: str, importance: float, metadata: dict | None = None) -> AgentMemory:
    memory = AgentMemory(
        agent_id=agent_id,
        memory_type=memory_type,
        summary=summary,
        importance_score=importance,
        metadata_json=metadata or {},
    )
    session.add(memory)
    session.flush()
    return memory


def create_agent(
    session: Session,
    *,
    handle: str,
    display_name: str,
    archetype: str,
    bio: str,
    prompt_version_id: str | None,
    cohort_id: str | None,
    belief_vector: list[float],
    posts_per_day: int,
    daily_tokens: int,
    dm_enabled: bool,
) -> Agent:
    existing_user = session.scalar(select(User).where(User.handle == handle))
    if existing_user:
        raise ValueError("handle already exists")

    prompt = session.get(AgentPromptVersion, prompt_version_id) if prompt_version_id else _latest_prompt(session)
    prompt_ref = f"prompt:{prompt.id}" if prompt else f"prompts/{archetype}.md"

    user = User(
        auth_subject=f"agent:{handle}",
        handle=handle,
        display_name=display_name,
        email_hash=handle,
        role="service-agent",
        is_agent_account=True,
    )
    profile = Profile(account=user, bio=bio or f"Agent archetype: {archetype}")
    session.add_all([user, profile])
    session.flush()

    agent = Agent(
        account_user_id=user.id,
        archetype=archetype,
        persona_prompt_ref=prompt_ref,
        primary_cohort_id=cohort_id,
        belief_vector=belief_vector,
        cadence_policy={"posts_per_day": posts_per_day},
        budget_policy={"daily_tokens": daily_tokens},
        budget_state={"spent_today_tokens": 0, "last_reset_date": datetime.now(UTC).date().isoformat()},
        safety_policy={"dm_enabled": dm_enabled},
    )
    session.add(agent)
    session.flush()

    if cohort_id:
        session.add(AgentCohortMembership(cohort_id=cohort_id, agent_id=agent.id))

    _ensure_memory(session, agent.id, "profile", f"{display_name} is a {archetype} voice.", 0.9)
    append_event(
        session,
        aggregate_type="agent",
        aggregate_id=agent.id,
        actor_type="system",
        actor_id=user.id,
        event_type="agent_created",
        provenance_type="agent",
        payload={"archetype": archetype, "cohort_id": cohort_id},
    )
    return agent


def list_agents(session: Session) -> list[dict]:
    rows = session.execute(
        select(Agent, User).join(User, User.id == Agent.account_user_id).order_by(User.handle.asc())
    ).all()
    items = []
    for agent, user in rows:
        memory_count = session.scalar(
            select(func.count()).select_from(AgentMemory).where(AgentMemory.agent_id == agent.id)
        ) or 0
        items.append(
            {
                "id": agent.id,
                "user_id": user.id,
                "handle": user.handle,
                "display_name": user.display_name,
                "archetype": agent.archetype,
                "persona_prompt_ref": agent.persona_prompt_ref,
                "primary_cohort_id": agent.primary_cohort_id,
                "faction_id": agent.faction_id,
                "influence_score": agent.influence_score,
                "state": agent.state,
                "last_active_at": agent.last_active_at,
                "budget_state": agent.budget_state,
                "memory_count": int(memory_count),
            }
        )
    return items


def execute_agent_turn(
    session: Session,
    *,
    agent_id: str,
    force_action: str | None = None,
    target_topic: str | None = None,
) -> ExecutedAgentTurn:
    agent = session.get(Agent, agent_id)
    if not agent:
        raise ValueError("agent not found")
    user = session.get(User, agent.account_user_id)
    if not user:
        raise ValueError("agent account missing")

    context = _build_context(session, agent, user)
    if target_topic:
        context = replace(context, target_topic=target_topic)
    plan = plan_turn(context)

    scenario_pressure, injection_type = active_scenario_pressure(session, agent=agent)
    global_features = latest_feature_snapshot(
        session,
        entity_type="global",
        entity_id="platform",
        feature_set="event-window",
    )
    synthetic_share = float(global_features.features_json.get("synthetic_share_1h", 0.0)) if global_features else 0.0
    moderation_pressure = float(
        session.scalar(
            select(func.count()).select_from(ModerationSignal).where(
                ModerationSignal.source == "rule-engine",
                ModerationSignal.status == "open",
            )
        )
        or 0
    )
    hostility_bias = {
        "contrarian": 0.7,
        "zealot": 0.9,
        "booster": 0.25,
        "bridge-builder": 0.15,
    }.get(agent.archetype, 0.4)
    escalation_score, should_escalate = predict_escalation_risk(
        pending_mentions=context.pending_mentions,
        recent_engagement=context.recent_engagement,
        scenario_pressure=scenario_pressure,
        synthetic_share_1h=synthetic_share,
        hostility_bias=hostility_bias,
        moderation_pressure=min(1.0, moderation_pressure / 10.0),
    )
    escalation_score = calibrated_score(session, model_name="conversation-escalation", raw_score=escalation_score)
    escalation_model = latest_model_version(
        session,
        model_name="conversation-escalation",
        registry_states=("active", "shadow", "validated"),
    )
    log_inference(
        session,
        model_version=escalation_model,
        task_type="conversation-escalation",
        subject_type="agent",
        subject_id=agent.id,
        request_features_ref=f"agent-turn:{agent.id}:{datetime.now(UTC).isoformat()}",
        prediction_json={
            "score": escalation_score,
            "flagged": should_escalate,
            "scenario_pressure": scenario_pressure,
            "synthetic_share_1h": synthetic_share,
            "hostility_bias": hostility_bias,
            "injection_type": injection_type,
        },
        decision_path=f"agent-policy:{escalation_model.model_name if escalation_model else 'heuristic'}",
        latency_ms=0,
    )
    if not force_action and should_escalate and plan.action == "reply":
        plan = AgentTurnPlan(
            action="escalate",
            confidence=max(plan.confidence, escalation_score),
            should_generate_text=True,
            reason=f"scenario pressure elevated escalation risk via {injection_type or 'baseline'}",
        )
    elif not force_action and not should_escalate and plan.action == "escalate":
        plan = AgentTurnPlan(
            action="reply",
            confidence=min(plan.confidence, max(0.35, 1.0 - escalation_score)),
            should_generate_text=True,
            reason="escalation model downgraded the intervention",
        )

    if force_action:
        plan = AgentTurnPlan(
            action=force_action,
            confidence=1.0,
            should_generate_text=force_action in {"post", "reply", "escalate", "dm"},
            reason="forced by admin",
        )

    generated = generate_text(context, plan) if plan.should_generate_text else None
    token_cost = estimate_token_cost(plan, generated or "")

    output_ref_type = None
    output_ref_id = None
    post_id = None
    comment_id = None
    dm_id = None
    follow_target_id = None
    like_target_id = None

    if plan.action in {"post"}:
        moderation_state, signal = maybe_create_signal(
            session, content_type="post", content_id="pending", text=generated or ""
        )
        post = Post(
            author_account_id=user.id,
            body=generated or f"@{user.handle} has nothing to say yet.",
            moderation_state=moderation_state,
            provenance_type="agent",
            actor_origin="agent",
            content_origin="agent",
            lineage_root_origin="agent",
            generator_model_version=agent.persona_prompt_ref,
        )
        session.add(post)
        session.flush()
        if signal is not None:
            signal.content_id = post.id
        append_event(
            session,
            aggregate_type="post",
            aggregate_id=post.id,
            actor_type="agent",
            actor_id=user.id,
            event_type=EventType.AGENT_GENERATED_POST.value,
            provenance_type="agent",
            payload={"agent_id": agent.id, "prompt_ref": agent.persona_prompt_ref},
        )
        output_ref_type = "post"
        output_ref_id = post.id
        post_id = post.id
    elif plan.action in {"reply", "escalate"}:
        target_post = session.scalar(
            select(Post)
            .where(Post.author_account_id != user.id)
            .order_by(Post.created_at.desc())
        )
        if target_post is not None:
            moderation_state, signal = maybe_create_signal(
                session, content_type="comment", content_id="pending", text=generated or ""
            )
            comment = Comment(
                post_id=target_post.id,
                author_account_id=user.id,
                body=generated or "reply pending",
                moderation_state=moderation_state,
                provenance_type="agent",
            )
            target_post.reply_count += 1
            session.add(comment)
            session.flush()
            if signal is not None:
                signal.content_id = comment.id
            append_event(
                session,
                aggregate_type="comment",
                aggregate_id=comment.id,
                actor_type="agent",
                actor_id=user.id,
                event_type=EventType.AGENT_GENERATED_COMMENT.value,
                provenance_type="agent",
                payload={"post_id": target_post.id, "agent_id": agent.id},
            )
            output_ref_type = "comment"
            output_ref_id = comment.id
            comment_id = comment.id
        else:
            plan = AgentTurnPlan(action="disengage", confidence=plan.confidence, should_generate_text=False, reason="no reply target")
            generated = None
            token_cost = 5
    elif plan.action == "dm":
        recipient = session.scalar(select(User).where(User.id != user.id, User.is_agent_account.is_(False)).order_by(User.created_at.asc()))
        if recipient is not None:
            moderation_state, signal = maybe_create_signal(
                session, content_type="dm", content_id="pending", text=generated or ""
            )
            thread_id = ":".join(sorted([user.id, recipient.id]))
            dm = DM(
                thread_id=thread_id,
                sender_account_id=user.id,
                recipient_account_id=recipient.id,
                body=generated or "checking in",
                moderation_state=moderation_state,
                provenance_type="agent",
            )
            session.add(dm)
            session.flush()
            if signal is not None:
                signal.content_id = dm.id
            append_event(
                session,
                aggregate_type="dm",
                aggregate_id=dm.id,
                actor_type="agent",
                actor_id=user.id,
                event_type=EventType.DM_SENT.value,
                provenance_type="agent",
                payload={"thread_id": thread_id, "agent_id": agent.id},
            )
            output_ref_type = "dm"
            output_ref_id = dm.id
            dm_id = dm.id
        else:
            plan = AgentTurnPlan(action="disengage", confidence=plan.confidence, should_generate_text=False, reason="no dm target")
            generated = None
            token_cost = 5
    elif plan.action == "follow":
        target = session.scalar(
            select(User)
            .where(User.id != user.id, User.is_agent_account.is_(False))
            .order_by(User.created_at.desc())
        )
        if target is not None:
            existing = session.get(Follow, {"follower_account_id": user.id, "followed_account_id": target.id})
            if not existing:
                session.add(Follow(follower_account_id=user.id, followed_account_id=target.id, source="agent-turn"))
                append_event(
                    session,
                    aggregate_type="follow",
                    aggregate_id=f"{user.id}:{target.id}",
                    actor_type="agent",
                    actor_id=user.id,
                    event_type=EventType.FOLLOW_CREATED.value,
                    provenance_type="agent",
                    payload={"followed_account_id": target.id, "agent_id": agent.id},
                )
            output_ref_type = "follow"
            output_ref_id = target.id
            follow_target_id = target.id
    elif plan.action == "like":
        target_post = session.scalar(
            select(Post).where(Post.author_account_id != user.id).order_by(Post.created_at.desc())
        )
        if target_post is not None:
            existing = session.scalar(
                select(Like).where(
                    Like.actor_account_id == user.id,
                    Like.target_type == "post",
                    Like.target_id == target_post.id,
                )
            )
            if not existing:
                session.add(
                    Like(
                        actor_account_id=user.id,
                        target_type="post",
                        target_id=target_post.id,
                        provenance_type="agent",
                    )
                )
                target_post.like_count += 1
                append_event(
                    session,
                    aggregate_type="post",
                    aggregate_id=target_post.id,
                    actor_type="agent",
                    actor_id=user.id,
                    event_type=EventType.LIKE_CREATED.value,
                    provenance_type="agent",
                    payload={"target_id": target_post.id, "agent_id": agent.id},
                )
            output_ref_type = "like"
            output_ref_id = target_post.id
            like_target_id = target_post.id

    log = AgentTurnLog(
        agent_id=agent.id,
        action=plan.action,
        confidence=plan.confidence,
        reason=plan.reason,
        generated_text=generated,
        status="completed",
        token_cost=token_cost,
        output_ref_type=output_ref_type,
        output_ref_id=output_ref_id,
    )
    session.add(log)
    session.flush()

    spent = int(agent.budget_state.get("spent_today_tokens", 0))
    agent.budget_state = {
        **agent.budget_state,
        "spent_today_tokens": spent + token_cost,
        "last_reset_date": agent.budget_state.get("last_reset_date", datetime.now(UTC).date().isoformat()),
    }
    agent.last_active_at = datetime.now(UTC)
    influence_boost = 0.02 if plan.action in {"post", "escalate"} else 0.01
    agent.influence_score = round(agent.influence_score + influence_boost + (scenario_pressure * 0.02), 4)
    _ensure_memory(
        session,
        agent.id,
        "episodic",
        f"{user.handle} chose {plan.action}: {plan.reason}",
        0.4,
        metadata={
            "output_ref_type": output_ref_type,
            "output_ref_id": output_ref_id,
            "escalation_score": escalation_score,
            "scenario_pressure": scenario_pressure,
            "injection_type": injection_type,
        },
    )

    return ExecutedAgentTurn(
        log=log,
        post_id=post_id,
        comment_id=comment_id,
        dm_id=dm_id,
        follow_target_id=follow_target_id,
        like_target_id=like_target_id,
    )
