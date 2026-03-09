from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

import orjson
from redis import Redis
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ml.common.scoring import cluster_topic_labels, score_coordination_anomaly
from services.api.app.core.config import get_settings
from services.api.app.models.eventing import Event, OutboxMessage
from services.api.app.models.ml import ConsumerCheckpoint, FeatureSnapshot, TrendSnapshot
from services.api.app.models.enums import OutboxStatus
from services.api.app.models.social import Post
from services.api.app.services.ml import latest_model_version, log_inference
from services.api.app.services.observability import rebuild_factions


settings = get_settings()


def relay_outbox_batch(session: Session, *, batch_size: int = 100) -> int:
    processed = 0
    rows = list(
        session.scalars(
            select(OutboxMessage)
            .where(
                OutboxMessage.status == OutboxStatus.PENDING.value,
                OutboxMessage.available_at <= datetime.now(UTC),
            )
            .limit(batch_size)
        )
    )

    redis_client = _build_redis_client()
    for row in rows:
        try:
            if redis_client is not None:
                redis_client.xadd(row.stream_name, {"payload": orjson.dumps(row.payload_json)})
            row.status = OutboxStatus.PUBLISHED.value
            row.published_at = datetime.now(UTC)
            row.last_error = None if redis_client is not None else "relay-fallback:no-redis"
            processed += 1
        except Exception as exc:  # pragma: no cover
            row.status = OutboxStatus.FAILED.value
            row.attempts += 1
            row.last_error = str(exc)
    session.flush()
    return processed


def consume_published_events(
    session: Session,
    *,
    consumer_name: str = "projection-consumer",
    batch_size: int = 200,
) -> int:
    checkpoint = _checkpoint(session, consumer_name)
    stmt = (
        select(OutboxMessage)
        .where(
            OutboxMessage.status == OutboxStatus.PUBLISHED.value,
            OutboxMessage.published_at.is_not(None),
        )
        .order_by(OutboxMessage.published_at.asc(), OutboxMessage.id.asc())
        .limit(batch_size)
    )
    if checkpoint.last_event_at and checkpoint.last_outbox_id:
        stmt = stmt.where(
            or_(
                OutboxMessage.published_at > checkpoint.last_event_at,
                and_(
                    OutboxMessage.published_at == checkpoint.last_event_at,
                    OutboxMessage.id > checkpoint.last_outbox_id,
                ),
            )
        )

    rows = list(session.scalars(stmt))
    if not rows:
        return 0

    actor_ids: set[str] = set()
    event_types: Counter[str] = Counter()
    for row in rows:
        payload = row.payload_json
        actor_id = payload.get("actor_id")
        if actor_id:
            actor_ids.add(actor_id)
        event_types[payload.get("event_type", "unknown")] += 1
        checkpoint.last_event_id = row.event_id
        checkpoint.last_outbox_id = row.id
        checkpoint.last_event_at = row.published_at
        checkpoint.processed_count += 1

    for actor_id in actor_ids:
        _record_actor_feature_snapshot(session, actor_id)
    _record_global_feature_snapshot(session)
    trend_count = rebuild_trend_snapshots(session, event_types=event_types)
    factions = rebuild_factions(session)
    checkpoint.metadata_json = {
        "trend_count": trend_count,
        "actors_touched": len(actor_ids),
        "faction_count": len(factions),
    }
    session.flush()
    return len(rows)


def rebuild_trend_snapshots(session: Session, *, event_types: Counter[str] | None = None) -> int:
    now = datetime.now(UTC)
    window_start = now - timedelta(hours=1)
    recent_events = list(session.scalars(select(Event).where(Event.occurred_at >= window_start)))
    event_counter = event_types or Counter(event.event_type for event in recent_events)
    synthetic_count = sum(1 for event in recent_events if event.provenance_type == "agent")
    created = [
        TrendSnapshot(
            window_start=window_start,
            window_end=now,
            topic_key="global",
            volume=len(recent_events),
            velocity=float(len(recent_events)),
            synthetic_share=(synthetic_count / len(recent_events)) if recent_events else 0.0,
            coordination_score=_coordination_score(len(recent_events), recent_events),
            promoted=len(recent_events) >= 10,
        )
    ]
    top_event_types = event_counter.most_common(3)
    for event_type, count in top_event_types:
        created.append(
            TrendSnapshot(
                window_start=window_start,
                window_end=now,
                topic_key=f"event:{event_type}",
                volume=count,
                velocity=float(count),
                synthetic_share=(synthetic_count / len(recent_events)) if recent_events else 0.0,
                coordination_score=min(1.0, count / 20.0),
                promoted=count >= 5,
            )
        )

    post_bodies = list(session.scalars(select(Post.body).where(Post.created_at >= window_start).limit(20)))
    for label, count in Counter(cluster_topic_labels(post_bodies)).most_common(2):
        created.append(
            TrendSnapshot(
                window_start=window_start,
                window_end=now,
                topic_key=f"topic:{label}",
                volume=count,
                velocity=float(count),
                synthetic_share=(synthetic_count / len(recent_events)) if recent_events else 0.0,
                coordination_score=min(1.0, count / 10.0),
                promoted=count >= 2,
            )
        )

    for snapshot in created:
        session.add(snapshot)
    session.flush()
    _log_coordination_inference(session, trend_snapshot=created[0], recent_events=recent_events)
    return len(created)


def run_pipeline_cycle(session: Session) -> tuple[int, int, int]:
    relayed = relay_outbox_batch(session)
    consumed = consume_published_events(session)
    latest_trends = list(session.scalars(select(TrendSnapshot).order_by(TrendSnapshot.created_at.desc()).limit(5)))
    session.commit()
    return relayed, consumed, len(latest_trends)


def _record_actor_feature_snapshot(session: Session, actor_id: str) -> FeatureSnapshot:
    now = datetime.now(UTC)
    last_day = now - timedelta(hours=24)
    last_hour = now - timedelta(hours=1)
    recent_events = list(session.scalars(select(Event).where(Event.actor_id == actor_id, Event.occurred_at >= last_day)))
    one_hour_events = [event for event in recent_events if _as_utc(event.occurred_at) >= last_hour]
    event_counter = Counter(event.event_type for event in recent_events)
    synthetic_events = sum(1 for event in recent_events if event.provenance_type == "agent")
    snapshot = FeatureSnapshot(
        entity_type="account",
        entity_id=actor_id,
        feature_set="interaction-counters",
        feature_version="v1",
        source_window="24h",
        features_json={
            "events_1h": len(one_hour_events),
            "events_24h": len(recent_events),
            "posts_24h": event_counter.get("post_created", 0),
            "comments_24h": event_counter.get("comment_created", 0),
            "likes_24h": event_counter.get("like_created", 0),
            "reposts_24h": event_counter.get("repost_created", 0),
            "follows_24h": event_counter.get("follow_created", 0),
            "dms_24h": event_counter.get("dm_sent", 0),
            "synthetic_events_24h_ratio": round(synthetic_events / len(recent_events), 4) if recent_events else 0.0,
        },
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def _record_global_feature_snapshot(session: Session) -> FeatureSnapshot:
    now = datetime.now(UTC)
    last_day = now - timedelta(hours=24)
    last_hour = now - timedelta(hours=1)
    recent_events = list(session.scalars(select(Event).where(Event.occurred_at >= last_day)))
    one_hour_events = [event for event in recent_events if _as_utc(event.occurred_at) >= last_hour]
    unique_authors = len({event.actor_id for event in one_hour_events})
    synthetic_events = sum(1 for event in one_hour_events if event.provenance_type == "agent")
    repost_events = sum(1 for event in one_hour_events if event.event_type == "repost_created")
    snapshot = FeatureSnapshot(
        entity_type="global",
        entity_id="platform",
        feature_set="event-window",
        feature_version="v1",
        source_window="1h",
        features_json={
            "event_volume_1h": len(one_hour_events),
            "event_volume_24h": len(recent_events),
            "unique_authors_1h": unique_authors,
            "synthetic_share_1h": round(synthetic_events / len(one_hour_events), 4) if one_hour_events else 0.0,
            "repost_ratio_1h": round(repost_events / len(one_hour_events), 4) if one_hour_events else 0.0,
        },
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def _coordination_score(event_volume: int, recent_events: list[Event]) -> float:
    unique_authors = len({event.actor_id for event in recent_events})
    synthetic_share = (
        sum(1 for event in recent_events if event.provenance_type == "agent") / len(recent_events)
        if recent_events
        else 0.0
    )
    repost_ratio = sum(1 for event in recent_events if event.event_type == "repost_created") / len(recent_events) if recent_events else 0.0
    score, _ = score_coordination_anomaly(
        event_volume_1h=event_volume,
        unique_authors_1h=unique_authors,
        synthetic_share_1h=synthetic_share,
        repost_ratio_1h=repost_ratio,
    )
    return score


def _log_coordination_inference(session: Session, *, trend_snapshot: TrendSnapshot, recent_events: list[Event]) -> None:
    unique_authors = len({event.actor_id for event in recent_events})
    synthetic_share = (
        sum(1 for event in recent_events if event.provenance_type == "agent") / len(recent_events)
        if recent_events
        else 0.0
    )
    repost_ratio = sum(1 for event in recent_events if event.event_type == "repost_created") / len(recent_events) if recent_events else 0.0
    score, flagged = score_coordination_anomaly(
        event_volume_1h=len(recent_events),
        unique_authors_1h=unique_authors,
        synthetic_share_1h=synthetic_share,
        repost_ratio_1h=repost_ratio,
    )
    model = latest_model_version(
        session,
        model_name="coordination-anomaly",
        registry_states=("active", "shadow", "validated"),
    )
    log_inference(
        session,
        model_version=model,
        task_type="coordination-anomaly",
        subject_type="trend-window",
        subject_id=trend_snapshot.id,
        request_features_ref=f"trend:{trend_snapshot.window_end.isoformat()}",
        prediction_json={
            "score": score,
            "flagged": flagged,
            "event_volume_1h": len(recent_events),
            "unique_authors_1h": unique_authors,
            "synthetic_share_1h": synthetic_share,
            "repost_ratio_1h": repost_ratio,
        },
        decision_path=f"pipeline:{model.model_name if model else 'heuristic'}",
        latency_ms=0,
    )


def _checkpoint(session: Session, consumer_name: str) -> ConsumerCheckpoint:
    checkpoint = session.get(ConsumerCheckpoint, consumer_name)
    if checkpoint is None:
        checkpoint = ConsumerCheckpoint(consumer_name=consumer_name)
        session.add(checkpoint)
        session.flush()
    return checkpoint


def _build_redis_client() -> Redis | None:
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=False)
        client.ping()
        return client
    except Exception:
        return None


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
