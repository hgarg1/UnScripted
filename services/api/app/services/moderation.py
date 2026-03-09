from __future__ import annotations

from sqlalchemy.orm import Session

from services.api.app.models.ml import ModerationSignal


FLAGGED_TERMS = {"kill", "slur-placeholder", "doxx"}


def moderation_state_for_text(text: str) -> tuple[str, float]:
    normalized = text.lower()
    hits = sum(1 for term in FLAGGED_TERMS if term in normalized)
    if hits:
        return "flagged", min(0.99, 0.55 + (hits * 0.15))
    return "clear", 0.0


def maybe_create_signal(
    session: Session,
    *,
    content_type: str,
    content_id: str,
    text: str,
    source: str = "rule-phase1",
) -> tuple[str, ModerationSignal | None]:
    state, score = moderation_state_for_text(text)
    if state == "flagged":
        signal = ModerationSignal(
            content_type=content_type,
            content_id=content_id,
            signal_type="content-risk",
            score=score,
            source=source,
            status="open",
        )
        session.add(signal)
        return state, signal
    return state, None
