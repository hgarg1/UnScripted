from fastapi import FastAPI
from pydantic import BaseModel


class FeedRankRequest(BaseModel):
    candidate_id: str
    recency_hours: float
    like_count: int
    reply_count: int
    repost_count: int


class FeedRankResponse(BaseModel):
    score: float
    reason: str


class AnomalyScoreRequest(BaseModel):
    event_volume_1h: int
    unique_authors_1h: int
    synthetic_share_1h: float


class AnomalyScoreResponse(BaseModel):
    score: float
    flagged: bool


app = FastAPI(title="UnScripted Inference Service")


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/rank/feed", response_model=FeedRankResponse)
def rank_feed_candidate(payload: FeedRankRequest) -> FeedRankResponse:
    score = max(
        0.1,
        10.0
        + payload.like_count
        + payload.reply_count * 1.5
        + payload.repost_count * 1.25
        - payload.recency_hours * 0.15,
    )
    return FeedRankResponse(score=score, reason="heuristic-bootstrap")


@app.post("/v1/detect/anomaly", response_model=AnomalyScoreResponse)
def score_anomaly(payload: AnomalyScoreRequest) -> AnomalyScoreResponse:
    score = min(
        1.0,
        (payload.event_volume_1h / max(payload.unique_authors_1h, 1)) * 0.05
        + payload.synthetic_share_1h * 0.6,
    )
    return AnomalyScoreResponse(score=score, flagged=score >= 0.65)
