from ml.common.bootstrap_pipeline import MODEL_CATALOG, build_dataset_manifest, train_bootstrap_model
from services.api.app.db.session import SessionLocal

def build_dataset_manifest_dict(model_name: str, provenance_policy: str) -> dict:
    with SessionLocal() as session:
        manifest = build_dataset_manifest(
            session,
            model_name=model_name,
            provenance_policy=provenance_policy,
        )
        session.commit()
        return manifest.manifest_json | {"dataset_ref": manifest.dataset_ref, "row_count": manifest.row_count}


def train_bootstrap_model_dict(model_name: str, provenance_policy: str = "mixed") -> dict:
    with SessionLocal() as session:
        model = train_bootstrap_model(
            session,
            model_name=model_name,
            provenance_policy=provenance_policy,
        )
        session.commit()
        return {
            "model_name": model.model_name,
            "registry_state": model.registry_state,
            "artifact_uri": model.artifact_uri,
            "metrics": model.metrics_json,
        }


if __name__ == "__main__":  # pragma: no cover
    results = []
    for model_name in MODEL_CATALOG:
        manifest = build_dataset_manifest_dict(model_name, "mixed")
        result = train_bootstrap_model_dict(model_name, "mixed")
        results.append({"manifest": manifest, "result": result})
    print(results)
