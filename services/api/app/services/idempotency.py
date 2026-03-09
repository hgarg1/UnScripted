from __future__ import annotations

import hashlib
import json

from fastapi import Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.models.auth import IdempotencyKeyRecord


def get_idempotency_key(
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> str | None:
    return idempotency_key


def _request_hash(payload: dict | list | str | None) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")) if payload is not None else ""
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def get_saved_response(
    session: Session, *, actor_id: str, key: str | None, payload: dict | list | str | None
) -> IdempotencyKeyRecord | None:
    if not key:
        return None
    record = session.scalar(
        select(IdempotencyKeyRecord).where(
            IdempotencyKeyRecord.actor_id == actor_id, IdempotencyKeyRecord.key == key
        )
    )
    if not record:
        return None
    if record.request_hash != _request_hash(payload):
        raise ValueError("idempotency key reused with different payload")
    return record


def persist_response(
    session: Session,
    *,
    actor_id: str,
    key: str | None,
    payload: dict | list | str | None,
    response_json: dict,
    status_code: int,
) -> None:
    if not key:
        return
    session.add(
        IdempotencyKeyRecord(
            actor_id=actor_id,
            key=key,
            request_hash=_request_hash(payload),
            response_json=response_json,
            status_code=status_code,
        )
    )
