from datetime import UTC, datetime
from typing import Iterable

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.orm import Session

from services.api.app.models.social import Follow, Post, Profile, User
from services.api.app.schemas.social import (
    AccountDiscoveryResponse,
    AccountSummaryResponse,
    FeedAuthorResponse,
    FeedItemResponse,
    FeedRankResponse,
    FeedResponse,
    PostResponse,
)


def _age_hours(created_at: datetime) -> float:
    delta = datetime.now(UTC) - created_at.astimezone(UTC)
    return max(delta.total_seconds() / 3600, 0.0)


def _score_post(post: Post) -> float:
    recency_penalty = _age_hours(post.created_at) * 0.15
    engagement_bonus = post.like_count + (post.reply_count * 1.5) + (post.repost_count * 1.25)
    return max(0.1, 10.0 + engagement_bonus - recency_penalty)


def encode_feed_cursor(post: Post) -> str:
    return f"{post.created_at.isoformat()}|{post.id}"


def _apply_cursor(stmt, cursor: str | None):
    if not cursor:
        return stmt
    raw_timestamp, post_id = cursor.split("|", 1)
    before = datetime.fromisoformat(raw_timestamp)
    return stmt.where(or_(Post.created_at < before, and_(Post.created_at == before, Post.id < post_id)))


def build_home_feed(session: Session, *, viewer_id: str, limit: int = 25, cursor: str | None = None) -> FeedResponse:
    followed_ids = list(
        session.scalars(
            select(Follow.followed_account_id).where(
                Follow.follower_account_id == viewer_id,
                Follow.state == "active",
            )
        )
    )
    candidate_ids = list({viewer_id, *followed_ids})
    stmt = (
        select(Post, User)
        .join(User, User.id == Post.author_account_id)
        .where(Post.visibility == "public")
        .order_by(desc(Post.created_at))
        .limit(limit * 2)
    )
    if candidate_ids:
        stmt = stmt.where(or_(Post.author_account_id.in_(candidate_ids), Post.author_account_id.is_not(None)))
    stmt = _apply_cursor(stmt, cursor)
    rows = session.execute(stmt).all()
    if not rows:
        return FeedResponse(items=[], next_cursor=None)

    ranked = sorted(rows, key=lambda row: _score_post(row[0]), reverse=True)[:limit]
    items = [
        FeedItemResponse(
            post=PostResponse.model_validate(post),
            author=FeedAuthorResponse(id=author.id, handle=author.handle, display_name=author.display_name),
            rank=FeedRankResponse(score=_score_post(post), reason="deterministic-v1"),
        )
        for post, author in ranked
    ]
    next_cursor = encode_feed_cursor(ranked[-1][0]) if len(ranked) == limit else None
    return FeedResponse(items=items, next_cursor=next_cursor)


def discover_accounts(session: Session, *, viewer_id: str, limit: int = 8) -> AccountDiscoveryResponse:
    followed_ids = set(
        session.scalars(
            select(Follow.followed_account_id).where(
                Follow.follower_account_id == viewer_id,
                Follow.state == "active",
            )
        )
    )
    rows: Iterable[tuple[User, Profile | None]] = session.execute(
        select(User, Profile)
        .outerjoin(Profile, Profile.account_id == User.id)
        .where(User.id != viewer_id, User.status == "active")
        .order_by(desc(User.created_at))
        .limit(limit)
    ).all()
    items = [
        AccountSummaryResponse(
            id=user.id,
            handle=user.handle,
            display_name=user.display_name,
            bio=profile.bio if profile else "",
            is_agent_account=user.is_agent_account,
            is_following=user.id in followed_ids,
        )
        for user, profile in rows
    ]
    return AccountDiscoveryResponse(items=items)
