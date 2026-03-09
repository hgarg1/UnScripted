from datetime import UTC, datetime


def build_dataset_manifest(model_name: str, provenance_policy: str) -> dict:
    return {
        "model_name": model_name,
        "provenance_policy": provenance_policy,
        "built_at": datetime.now(UTC).isoformat(),
        "feature_set_version": "v1",
        "status": "materialized-placeholder",
    }


def train_placeholder_model(model_name: str) -> dict:
    return {
        "model_name": model_name,
        "artifact_uri": f"s3://unscripted/models/{model_name}/placeholder.bin",
        "metrics": {"status": "bootstrap"},
    }


if __name__ == "__main__":  # pragma: no cover
    manifest = build_dataset_manifest("feed-ranker", "human-only")
    result = train_placeholder_model("feed-ranker")
    print({"manifest": manifest, "result": result})
