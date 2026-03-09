from typing import Any

from sqlalchemy.orm import Session

from services.api.app.models.eventing import Event, OutboxMessage


def append_event(
    session: Session,
    *,
    aggregate_type: str,
    aggregate_id: str,
    actor_type: str,
    actor_id: str,
    event_type: str,
    provenance_type: str,
    payload: dict[str, Any],
    stream_name: str = "unscripted.events",
    trace_id: str | None = None,
    causation_id: str | None = None,
    correlation_id: str | None = None,
) -> Event:
    event = Event(
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        actor_type=actor_type,
        actor_id=actor_id,
        event_type=event_type,
        provenance_type=provenance_type,
        payload_json=payload,
        trace_id=trace_id,
        causation_id=causation_id,
        correlation_id=correlation_id,
    )
    session.add(event)
    session.flush()

    outbox = OutboxMessage(
        event_id=event.event_id,
        stream_name=stream_name,
        payload_json={
            "event_id": event.event_id,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "event_type": event_type,
            "provenance_type": provenance_type,
            "payload": payload,
            "trace_id": trace_id,
            "causation_id": causation_id,
            "correlation_id": correlation_id,
        },
    )
    session.add(outbox)
    return event
