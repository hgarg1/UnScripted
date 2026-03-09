from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from services.api.app.models.social import Follow, Post, User
from services.api.app.schemas.social import FeedAuthorResponse, FeedItemResponse, FeedRankResponse, FeedResponse, PostResponse


def _age_hours(created_at: datetime) -> float:
    delta = datetime.now(UTC) - created_at.astimezone(UTC)
    return max(delta.total_seconds() / 3600, 0.0)


def _score_post(post: Post) -> float:
    recency_penalty = _age_hours(post.created_at) * 0.15
    engagement_bonus = post.like_count + (post.reply_count * 1.5) + (post.repost_count * 1.25)
    return max(0.1, 10.0 + engagement_bonus - recency_penalty)


def build_home_feed(session: Session, *, viewer_id: str, limit: int = 25) -> FeedResponse:
    followed_ids = list(
        session.scalars(
            select(Follow.followed_account_id).where(
                Follow.follower_account_id == viewer_id,
                Follow.state == "active",
            )
        )
    )
    candidate_ids = list({viewer_id, *followed_ids})
    if not candidate_ids:
        return FeedResponse(items=[])

    rows = session.execute(
        select(Post, User)
        .join(User, User.id == Post.author_account_id)
        .where(Post.author_account_id.in_(candidate_ids))
        .order_by(desc(Post.created_at))
        .limit(limit * 2)
    ).all()

    ranked = sorted(rows, key=lambda row: _score_post(row[0]), reverse=True)[:limit]
    items = [
        FeedItemResponse(
            post=PostResponse.model_validate(post),
            author=FeedAuthorResponse(id=author.id, handle=author.handle, display_name=author.display_name),
            rank=FeedRankResponse(score=_score_post(post), reason="deterministic-v1"),
        )
        for post, author in ranked
    ]
    return FeedResponse(items=items)
