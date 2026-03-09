from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelDescriptor:
    model_name: str
    task_type: str
    feature_set_version: str
    registry_state: str
    artifact_uri: str
