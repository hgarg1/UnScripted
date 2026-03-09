from fastapi import FastAPI
from pydantic import BaseModel

from ml.common.scoring import embed_ideology, score_coordination_anomaly, score_feed_candidate


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


class IdeologyEmbeddingRequest(BaseModel):
    text: str


class IdeologyEmbeddingResponse(BaseModel):
    vector: list[float]
    dominant_axis: str


app = FastAPI(title="UnScripted Inference Service")


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/rank/feed", response_model=FeedRankResponse)
def rank_feed_candidate(payload: FeedRankRequest) -> FeedRankResponse:
    score, reason = score_feed_candidate(
        recency_hours=payload.recency_hours,
        like_count=payload.like_count,
        reply_count=payload.reply_count,
        repost_count=payload.repost_count,
    )
    return FeedRankResponse(score=score, reason=reason)


@app.post("/v1/detect/anomaly", response_model=AnomalyScoreResponse)
def score_anomaly(payload: AnomalyScoreRequest) -> AnomalyScoreResponse:
    score, flagged = score_coordination_anomaly(
        event_volume_1h=payload.event_volume_1h,
        unique_authors_1h=payload.unique_authors_1h,
        synthetic_share_1h=payload.synthetic_share_1h,
    )
    return AnomalyScoreResponse(score=score, flagged=flagged)


@app.post("/v1/embed/ideology", response_model=IdeologyEmbeddingResponse)
def ideology_embedding(payload: IdeologyEmbeddingRequest) -> IdeologyEmbeddingResponse:
    vector, dominant_axis = embed_ideology(payload.text)
    return IdeologyEmbeddingResponse(vector=vector, dominant_axis=dominant_axis)
