import time
from datetime import UTC, datetime, timedelta

import orjson
from redis import Redis
from sqlalchemy import select

from services.api.app.core.config import get_settings
from services.api.app.db.session import SessionLocal
from services.api.app.models.eventing import OutboxMessage
from services.api.app.models.enums import OutboxStatus
from services.api.app.models.ml import TrendSnapshot


settings = get_settings()


def relay_outbox_batch(batch_size: int = 100) -> int:
    redis_client = Redis.from_url(settings.redis_url, decode_responses=False)
    processed = 0

    with SessionLocal() as session:
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

        for row in rows:
            try:
                redis_client.xadd(row.stream_name, {"payload": orjson.dumps(row.payload_json)})
                row.status = OutboxStatus.PUBLISHED.value
                row.published_at = datetime.now(UTC)
                row.last_error = None
                processed += 1
            except Exception as exc:  # pragma: no cover
                row.status = OutboxStatus.FAILED.value
                row.attempts += 1
                row.last_error = str(exc)

        session.commit()
    return processed


def rebuild_simple_trend_snapshot(topic_key: str = "global") -> TrendSnapshot:
    with SessionLocal() as session:
        window_end = datetime.now(UTC)
        window_start = window_end - timedelta(hours=1)
        published_events = list(
            session.scalars(
                select(OutboxMessage).where(
                    OutboxMessage.status == OutboxStatus.PUBLISHED.value,
                    OutboxMessage.published_at >= window_start,
                )
            )
        )

        synthetic_count = sum(
            1
            for event in published_events
            if event.payload_json.get("provenance_type") == "agent"
        )

        snapshot = TrendSnapshot(
            window_start=window_start,
            window_end=window_end,
            topic_key=topic_key,
            volume=len(published_events),
            velocity=float(len(published_events)),
            synthetic_share=(synthetic_count / len(published_events)) if published_events else 0.0,
            coordination_score=min(1.0, len(published_events) / 100.0),
            promoted=len(published_events) >= 25,
        )
        session.add(snapshot)
        session.commit()
        session.refresh(snapshot)
        return snapshot


def run_forever() -> None:  # pragma: no cover
    while True:
        relay_outbox_batch()
        rebuild_simple_trend_snapshot()
        time.sleep(5)


if __name__ == "__main__":  # pragma: no cover
    run_forever()
