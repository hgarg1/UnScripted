from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.api.app.models.eventing import Event
from services.api.app.models.ml import DatasetManifest, ModelEvaluation, ModelVersion
from services.api.app.models.social import Post


MODEL_CATALOG: dict[str, dict[str, str]] = {
    "feed-ranker": {
        "task_type": "feed-ranking",
        "feature_set_version": "feed_v1",
        "default_state": "active",
    },
    "ideology-embedding": {
        "task_type": "ideology-embedding",
        "feature_set_version": "ideology_v1",
        "default_state": "validated",
    },
    "coordination-anomaly": {
        "task_type": "coordination-anomaly",
        "feature_set_version": "coordination_v1",
        "default_state": "shadow",
    },
}

ARTIFACT_ROOT = Path("artifacts")


def build_dataset_manifest(session: Session, *, model_name: str, provenance_policy: str) -> DatasetManifest:
    catalog = MODEL_CATALOG[model_name]
    now = datetime.now(UTC)
    row_count = session.scalar(select(func.count()).select_from(Event)) or 0
    posts_last_day = session.scalar(
        select(func.count()).select_from(Post).where(Post.created_at >= now - timedelta(days=1))
    ) or 0
    artifact_dir = ARTIFACT_ROOT / "datasets"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = artifact_dir / f"{model_name}-{now.strftime('%Y%m%d%H%M%S')}.json"
    manifest_json = {
        "model_name": model_name,
        "provenance_policy": provenance_policy,
        "feature_set_version": catalog["feature_set_version"],
        "event_count": row_count,
        "posts_last_day": posts_last_day,
        "built_at": now.isoformat(),
    }
    dataset_path.write_text(json.dumps(manifest_json, indent=2), encoding="utf-8")

    manifest = DatasetManifest(
        model_name=model_name,
        dataset_ref=str(dataset_path),
        provenance_policy=provenance_policy,
        feature_set_version=catalog["feature_set_version"],
        row_count=row_count,
        status="materialized",
        manifest_json=manifest_json,
    )
    session.add(manifest)
    session.flush()
    return manifest


def train_bootstrap_model(
    session: Session,
    *,
    model_name: str,
    provenance_policy: str = "mixed",
    registry_state: str | None = None,
) -> ModelVersion:
    catalog = MODEL_CATALOG[model_name]
    manifest = build_dataset_manifest(session, model_name=model_name, provenance_policy=provenance_policy)

    model_dir = ARTIFACT_ROOT / "models" / model_name
    model_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = model_dir / f"{manifest.id}.json"
    metrics = _bootstrap_metrics(model_name, manifest.row_count)
    artifact_payload = {
        "model_name": model_name,
        "task_type": catalog["task_type"],
        "feature_set_version": catalog["feature_set_version"],
        "trained_at": datetime.now(UTC).isoformat(),
        "metrics": metrics,
    }
    artifact_path.write_text(json.dumps(artifact_payload, indent=2), encoding="utf-8")

    model_version = ModelVersion(
        model_name=model_name,
        task_type=catalog["task_type"],
        registry_state=registry_state or catalog["default_state"],
        artifact_uri=str(artifact_path),
        feature_set_version=catalog["feature_set_version"],
        training_dataset_ref=manifest.dataset_ref,
        metrics_json=metrics,
        promoted_at=datetime.now(UTC) if (registry_state or catalog["default_state"]) == "active" else None,
    )
    session.add(model_version)
    session.flush()

    evaluation = ModelEvaluation(
        model_version_id=model_version.id,
        dataset_ref=manifest.dataset_ref,
        eval_type="bootstrap-offline",
        metrics_json=metrics,
        decision="pass" if metrics.get("quality", 0.0) >= 0.6 else "review",
    )
    session.add(evaluation)
    session.flush()
    return model_version


def ensure_bootstrap_models(session: Session) -> list[ModelVersion]:
    created: list[ModelVersion] = []
    for model_name in MODEL_CATALOG:
        existing = session.scalar(select(ModelVersion).where(ModelVersion.model_name == model_name))
        if existing:
            continue
        created.append(train_bootstrap_model(session, model_name=model_name))
    return created


def _bootstrap_metrics(model_name: str, row_count: int) -> dict[str, float | int | str]:
    baseline = {
        "feed-ranker": 0.71,
        "ideology-embedding": 0.68,
        "coordination-anomaly": 0.74,
    }[model_name]
    return {
        "quality": baseline,
        "coverage": min(1.0, max(0.1, row_count / 100.0)),
        "rows": row_count,
        "status": "bootstrap",
    }
