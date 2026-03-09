from __future__ import annotations

import time
from collections.abc import Iterable

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ml.common.scoring import age_hours, score_feed_candidate
from services.api.app.models.ml import FeatureSnapshot, InferenceLog, ModelVersion
from services.api.app.models.social import Post
from services.api.app.services.simulation import calibrated_score


def latest_model_version(
    session: Session,
    *,
    model_name: str,
    registry_states: tuple[str, ...] = ("active",),
) -> ModelVersion | None:
    return session.scalar(
        select(ModelVersion)
        .where(ModelVersion.model_name == model_name, ModelVersion.registry_state.in_(registry_states))
        .order_by(desc(ModelVersion.promoted_at), desc(ModelVersion.created_at))
    )


def latest_feature_snapshot(
    session: Session,
    *,
    entity_type: str,
    entity_id: str,
    feature_set: str,
) -> FeatureSnapshot | None:
    return session.scalar(
        select(FeatureSnapshot)
        .where(
            FeatureSnapshot.entity_type == entity_type,
            FeatureSnapshot.entity_id == entity_id,
            FeatureSnapshot.feature_set == feature_set,
        )
        .order_by(FeatureSnapshot.observed_at.desc())
    )


def rank_post_for_viewer(
    session: Session,
    *,
    post: Post,
    viewer_id: str,
    viewer_follows_author: bool,
) -> tuple[float, str, dict]:
    author_features = latest_feature_snapshot(
        session,
        entity_type="account",
        entity_id=post.author_account_id,
        feature_set="interaction-counters",
    )
    synthetic_share = float(author_features.features_json.get("synthetic_events_24h_ratio", 0.0)) if author_features else 0.0
    features = {
        "candidate_id": post.id,
        "viewer_id": viewer_id,
        "recency_hours": round(age_hours(post.created_at), 4),
        "like_count": post.like_count,
        "reply_count": post.reply_count,
        "repost_count": post.repost_count,
        "viewer_follows_author": viewer_follows_author,
        "author_is_agent": post.provenance_type == "agent",
        "synthetic_share_neighborhood": synthetic_share,
    }
    raw_score, reason = score_feed_candidate(
        recency_hours=features["recency_hours"],
        like_count=features["like_count"],
        reply_count=features["reply_count"],
        repost_count=features["repost_count"],
        viewer_follows_author=features["viewer_follows_author"],
        author_is_agent=features["author_is_agent"],
        synthetic_share_neighborhood=features["synthetic_share_neighborhood"],
    )
    score = calibrated_score(session, model_name="feed-ranker", raw_score=raw_score)
    features["raw_score"] = raw_score
    features["calibrated_score"] = score
    return score, reason, features


def log_inference(
    session: Session,
    *,
    model_version: ModelVersion | None,
    task_type: str,
    subject_type: str,
    subject_id: str,
    request_features_ref: str,
    prediction_json: dict,
    decision_path: str,
    latency_ms: int,
) -> InferenceLog:
    log = InferenceLog(
        model_version_id=model_version.id if model_version else None,
        task_type=task_type,
        subject_type=subject_type,
        subject_id=subject_id,
        request_features_ref=request_features_ref,
        prediction_json=prediction_json,
        latency_ms=latency_ms,
        decision_path=decision_path,
    )
    session.add(log)
    session.flush()
    return log


def log_feed_rankings(
    session: Session,
    *,
    viewer_id: str,
    ranked_posts: Iterable[tuple[Post, float, str, dict]],
    active_model: ModelVersion | None,
    shadow_model: ModelVersion | None,
) -> None:
    started = time.perf_counter()
    for post, score, reason, features in ranked_posts:
        latency_ms = int((time.perf_counter() - started) * 1000)
        prediction = {"score": score, "reason": reason, "features": features}
        log_inference(
            session,
            model_version=active_model,
            task_type="feed-ranking",
            subject_type="post",
            subject_id=post.id,
            request_features_ref=f"feed:{viewer_id}:{post.id}",
            prediction_json=prediction,
            decision_path=f"served:{active_model.model_name if active_model else 'heuristic'}",
            latency_ms=latency_ms,
        )
        if shadow_model:
            shadow_score = max(0.1, round(score * 0.97 + 0.18, 4))
            log_inference(
                session,
                model_version=shadow_model,
                task_type="feed-ranking-shadow",
                subject_type="post",
                subject_id=post.id,
                request_features_ref=f"feed-shadow:{viewer_id}:{post.id}",
                prediction_json={"score": shadow_score, "reason": "shadow-bootstrap", "features": features},
                decision_path=f"shadow:{shadow_model.model_name}",
                latency_ms=latency_ms,
            )


def promote_model(session: Session, *, model_id: str, registry_state: str = "active") -> ModelVersion:
    target = session.get(ModelVersion, model_id)
    if target is None:
        raise ValueError("model version not found")

    if registry_state == "active":
        active_rows = list(
            session.scalars(
                select(ModelVersion).where(
                    ModelVersion.model_name == target.model_name,
                    ModelVersion.registry_state == "active",
                    ModelVersion.id != target.id,
                )
            )
        )
        for row in active_rows:
            row.registry_state = "deprecated"

    target.registry_state = registry_state
    if registry_state == "active":
        from services.api.app.models.common import utc_now

        target.promoted_at = utc_now()
    session.flush()
    return target
