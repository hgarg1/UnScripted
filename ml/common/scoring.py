from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime


def age_hours(created_at: datetime) -> float:
    normalized = created_at.replace(tzinfo=UTC) if created_at.tzinfo is None else created_at.astimezone(UTC)
    delta = datetime.now(UTC) - normalized
    return max(delta.total_seconds() / 3600, 0.0)


def score_feed_candidate(
    *,
    recency_hours: float,
    like_count: int,
    reply_count: int,
    repost_count: int,
    viewer_follows_author: bool = False,
    author_is_agent: bool = False,
    synthetic_share_neighborhood: float = 0.0,
) -> tuple[float, str]:
    score = (
        10.0
        + like_count
        + (reply_count * 1.5)
        + (repost_count * 1.25)
        + (1.35 if viewer_follows_author else 0.0)
        - (recency_hours * 0.15)
        - (synthetic_share_neighborhood * (0.35 if author_is_agent else 0.15))
    )
    return max(0.1, score), "heuristic-bootstrap-v2"


def score_coordination_anomaly(
    *,
    event_volume_1h: int,
    unique_authors_1h: int,
    synthetic_share_1h: float,
    repost_ratio_1h: float = 0.0,
) -> tuple[float, bool]:
    density = event_volume_1h / max(unique_authors_1h, 1)
    score = min(1.0, density * 0.05 + synthetic_share_1h * 0.55 + repost_ratio_1h * 0.25)
    return score, score >= 0.65


def embed_ideology(text: str) -> tuple[list[float], str]:
    normalized = text.lower()
    axes = [
        _keyword_score(normalized, ("order", "control", "stability", "moderation"), ("chaos", "disrupt", "break")),
        _keyword_score(normalized, ("collective", "community", "public"), ("individual", "private", "solo")),
        _keyword_score(normalized, ("optimism", "progress", "future"), ("decline", "decay", "collapse")),
    ]
    dominant_axis = max(range(len(axes)), key=lambda index: abs(axes[index]))
    return axes, f"axis-{dominant_axis + 1}"


def cluster_topic_labels(texts: Iterable[str]) -> list[str]:
    labels: list[str] = []
    for text in texts:
        lowered = text.lower()
        if any(token in lowered for token in ("feed", "ranking", "algorithm", "timeline")):
            labels.append("ranking")
        elif any(token in lowered for token in ("agent", "bot", "synthetic", "ai")):
            labels.append("synthetic-agents")
        elif any(token in lowered for token in ("trust", "community", "faction", "group")):
            labels.append("factions")
        else:
            labels.append("general-discourse")
    return labels


def _keyword_score(text: str, positive: tuple[str, ...], negative: tuple[str, ...]) -> float:
    pos = sum(text.count(token) for token in positive)
    neg = sum(text.count(token) for token in negative)
    raw = pos - neg
    if raw == 0:
        return 0.0
    return max(-1.0, min(1.0, raw / max(pos + neg, 1)))
