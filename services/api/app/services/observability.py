from __future__ import annotations

from collections import Counter, defaultdict
from math import sqrt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.api.app.models.agent import Agent, AgentCohort, Faction
from services.api.app.models.eventing import Event, OutboxMessage
from services.api.app.models.game import GuessGameGuess
from services.api.app.models.ml import ConsumerCheckpoint, InferenceLog, ModelVersion, ModerationSignal, TrendSnapshot
from services.api.app.models.social import Post, Profile, User
from services.api.app.models.simulation import CalibrationSnapshot, ExperimentRun, ScenarioInjection


def rebuild_factions(session: Session) -> list[dict]:
    rows = list(
        session.execute(
            select(Agent, User, AgentCohort)
            .join(User, User.id == Agent.account_user_id)
            .outerjoin(AgentCohort, AgentCohort.id == Agent.primary_cohort_id)
            .where(Agent.state == "active")
        ).all()
    )
    if not rows:
        return []

    grouped: dict[str, list[tuple[Agent, User, AgentCohort | None]]] = defaultdict(list)
    for agent, user, cohort in rows:
        grouped[_belief_signature(agent.belief_vector, cohort.scenario if cohort else None)].append((agent, user, cohort))

    existing = {row.name: row for row in session.scalars(select(Faction))}
    results: list[dict] = []
    for signature, members in grouped.items():
        centroid = _centroid([agent.belief_vector for agent, _, _ in members])
        cohesion = _cohesion(centroid, [agent.belief_vector for agent, _, _ in members])
        faction = existing.get(signature)
        if faction is None:
            faction = Faction(
                name=signature,
                origin_type="emergent",
                belief_centroid=centroid,
                cohesion_score=cohesion,
                visibility="internal",
            )
            session.add(faction)
            session.flush()
        else:
            faction.origin_type = "emergent"
            faction.belief_centroid = centroid
            faction.cohesion_score = cohesion

        for agent, _, _ in members:
            agent.faction_id = faction.id

        results.append(_serialize_faction(faction, members))

    session.flush()
    return sorted(results, key=lambda item: (item["member_count"], item["avg_influence"]), reverse=True)


def list_factions(session: Session) -> list[dict]:
    faction_rows = list(session.scalars(select(Faction).order_by(Faction.cohesion_score.desc(), Faction.created_at.asc())))
    if not faction_rows:
        return rebuild_factions(session)

    agents = list(
        session.execute(
            select(Agent, User, AgentCohort)
            .join(User, User.id == Agent.account_user_id)
            .outerjoin(AgentCohort, AgentCohort.id == Agent.primary_cohort_id)
            .where(Agent.faction_id.is_not(None))
        ).all()
    )
    grouped: dict[str, list[tuple[Agent, User, AgentCohort | None]]] = defaultdict(list)
    for agent, user, cohort in agents:
        grouped[agent.faction_id].append((agent, user, cohort))

    return [
        _serialize_faction(faction, grouped.get(faction.id, []))
        for faction in faction_rows
    ]


def build_observability_overview(session: Session) -> dict:
    factions = list_factions(session)
    pending_outbox = session.scalar(
        select(func.count()).select_from(OutboxMessage).where(OutboxMessage.status == "pending")
    ) or 0
    total_events = session.scalar(select(func.count()).select_from(Event)) or 0
    total_logs = session.scalar(select(func.count()).select_from(InferenceLog)) or 0
    open_signals = session.scalar(
        select(func.count()).select_from(ModerationSignal).where(ModerationSignal.status == "open")
    ) or 0
    latest_trend = session.scalar(select(TrendSnapshot).order_by(TrendSnapshot.created_at.desc()))
    checkpoint = session.scalar(select(ConsumerCheckpoint).order_by(ConsumerCheckpoint.updated_at.desc()))
    active_models = session.scalar(
        select(func.count()).select_from(ModelVersion).where(ModelVersion.registry_state == "active")
    ) or 0
    active_experiments = session.scalar(
        select(func.count()).select_from(ExperimentRun).where(ExperimentRun.state == "active")
    ) or 0
    pending_injections = session.scalar(
        select(func.count()).select_from(ScenarioInjection).where(ScenarioInjection.state == "pending")
    ) or 0
    calibration_runs = session.scalar(select(func.count()).select_from(CalibrationSnapshot)) or 0
    metrics = [
        {"key": "pending_outbox", "value": float(pending_outbox), "label": "Pending outbox rows"},
        {"key": "event_volume", "value": float(total_events), "label": "Total canonical events"},
        {"key": "inference_logs", "value": float(total_logs), "label": "Inference log rows"},
        {"key": "open_moderation", "value": float(open_signals), "label": "Open moderation signals"},
        {"key": "active_models", "value": float(active_models), "label": "Active models"},
        {"key": "active_experiments", "value": float(active_experiments), "label": "Active experiments"},
        {"key": "pending_injections", "value": float(pending_injections), "label": "Pending scenario injections"},
        {"key": "calibration_runs", "value": float(calibration_runs), "label": "Calibration snapshots"},
        {
            "key": "latest_synthetic_share",
            "value": float(latest_trend.synthetic_share if latest_trend else 0.0),
            "label": "Latest trend synthetic share",
        },
        {
            "key": "consumer_processed",
            "value": float(checkpoint.processed_count if checkpoint else 0),
            "label": "Processed published events",
        },
    ]
    provenance = [
        {"scope": "events", **_provenance_counts(session, Event, "provenance_type")},
        {"scope": "posts", **_provenance_counts(session, Post, "provenance_type")},
    ]
    rollout_counter = Counter(
        session.scalars(select(ModelVersion.registry_state))
    )
    rollouts = [
        {"registry_state": state, "count": count}
        for state, count in sorted(rollout_counter.items(), key=lambda item: item[0])
    ]
    return {
        "metrics": metrics,
        "provenance": provenance,
        "rollouts": rollouts,
        "factions": factions,
    }


def list_guessable_accounts(session: Session, *, viewer_id: str, limit: int = 6) -> list[dict]:
    latest_post_subquery = (
        select(Post.author_account_id, func.max(Post.created_at).label("latest_created_at"))
        .group_by(Post.author_account_id)
        .subquery()
    )
    guessed_ids = {
        account_id
        for account_id in session.scalars(
            select(GuessGameGuess.target_account_id).where(GuessGameGuess.user_id == viewer_id)
        )
    }
    rows = session.execute(
        select(User, Profile, Post)
        .outerjoin(Profile, Profile.account_id == User.id)
        .outerjoin(latest_post_subquery, latest_post_subquery.c.author_account_id == User.id)
        .outerjoin(
            Post,
            (Post.author_account_id == User.id)
            & (Post.created_at == latest_post_subquery.c.latest_created_at),
        )
        .where(User.id != viewer_id, User.status == "active")
        .order_by(User.created_at.desc())
        .limit(limit)
    ).all()
    items = []
    for user, profile, post in rows:
        activity = session.scalar(
            select(func.count()).select_from(Event).where(Event.actor_id == user.id)
        ) or 0
        items.append(
            {
                "account_id": user.id,
                "handle": user.handle,
                "display_name": user.display_name,
                "bio": profile.bio if profile else "",
                "latest_post_excerpt": post.body[:120] if post else None,
                "recent_activity_count": int(activity),
                "already_guessed": user.id in guessed_ids,
            }
        )
    return items


def build_guess_score(session: Session, *, viewer_id: str) -> dict:
    guesses = list(session.scalars(select(GuessGameGuess).where(GuessGameGuess.user_id == viewer_id)))
    correct = sum(1 for guess in guesses if guess.was_correct)
    last_guess = max((guess.created_at for guess in guesses), default=None)
    return {
        "attempts": len(guesses),
        "correct": correct,
        "accuracy": round(correct / len(guesses), 4) if guesses else 0.0,
        "last_guess_at": last_guess,
    }


def _belief_signature(vector: list[float], scenario: str | None) -> str:
    if not vector:
        return "general-observers"
    dominant_axis = max(range(len(vector)), key=lambda idx: abs(vector[idx]))
    direction = "positive" if vector[dominant_axis] >= 0 else "negative"
    scenario_suffix = scenario or "baseline"
    return f"axis-{dominant_axis + 1}-{direction}-{scenario_suffix}"


def _centroid(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    width = max(len(vector) for vector in vectors)
    totals = [0.0] * width
    for vector in vectors:
        for idx in range(width):
            totals[idx] += vector[idx] if idx < len(vector) else 0.0
    return [round(total / len(vectors), 4) for total in totals]


def _cohesion(centroid: list[float], vectors: list[list[float]]) -> float:
    if not vectors or not centroid:
        return 0.0
    distances = []
    for vector in vectors:
        width = max(len(centroid), len(vector))
        total = 0.0
        for idx in range(width):
            lhs = centroid[idx] if idx < len(centroid) else 0.0
            rhs = vector[idx] if idx < len(vector) else 0.0
            total += (lhs - rhs) ** 2
        distances.append(sqrt(total))
    avg_distance = sum(distances) / len(distances)
    return round(max(0.0, 1.0 - min(1.0, avg_distance)), 4)


def _serialize_faction(faction: Faction, members: list[tuple[Agent, User, AgentCohort | None]]) -> dict:
    archetypes = Counter(agent.archetype for agent, _, _ in members)
    scenarios = Counter((cohort.scenario if cohort else "baseline") for _, _, cohort in members)
    avg_influence = sum(agent.influence_score for agent, _, _ in members) / max(len(members), 1)
    return {
        "id": faction.id,
        "name": faction.name,
        "origin_type": faction.origin_type,
        "cohesion_score": faction.cohesion_score,
        "visibility": faction.visibility,
        "member_count": len(members),
        "avg_influence": round(avg_influence, 4),
        "dominant_archetypes": [name for name, _ in archetypes.most_common(3)],
        "sample_handles": [user.handle for _, user, _ in members[:4]],
        "scenario_mix": [name for name, _ in scenarios.most_common(3)],
        "belief_centroid": faction.belief_centroid,
        "created_at": faction.created_at,
    }


def _provenance_counts(session: Session, model, column_name: str) -> dict[str, int]:
    values = list(session.scalars(select(getattr(model, column_name))))
    counter = Counter(values)
    return {
        "human": counter.get("human", 0),
        "agent": counter.get("agent", 0),
        "mixed": counter.get("mixed", 0),
        "system": counter.get("system", 0),
    }
