from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FeedFeatureVector:
    likes_1h: int
    replies_1h: int
    reposts_24h: int
    synthetic_share_neighborhood: float
    ideology_distance: float
