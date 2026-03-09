from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    actor_origin: str
    content_origin: str
    lineage_root_origin: str
    contains_synthetic_ancestry: bool
    generator_model_version: str | None = None
    scenario_id: str | None = None
