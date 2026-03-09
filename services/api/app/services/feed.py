from datetime import datetime
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
from services.api.app.services.ml import latest_model_version, log_feed_rankings, rank_post_for_viewer


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

    followed_lookup = set(followed_ids)
    scored_rows = []
    for post, author in rows:
        score, reason, features = rank_post_for_viewer(
            session,
            post=post,
            viewer_id=viewer_id,
            viewer_follows_author=post.author_account_id in followed_lookup,
        )
        scored_rows.append((post, author, score, reason, features))

    scored_rows.sort(key=lambda row: row[2], reverse=True)
    ranked = scored_rows[:limit]
    active_model = latest_model_version(session, model_name="feed-ranker", registry_states=("active",))
    shadow_model = latest_model_version(session, model_name="feed-ranker", registry_states=("shadow",))
    log_feed_rankings(
        session,
        viewer_id=viewer_id,
        ranked_posts=[(post, score, reason, features) for post, _, score, reason, features in ranked],
        active_model=active_model,
        shadow_model=shadow_model,
    )
    items = [
        FeedItemResponse(
            post=PostResponse.model_validate(post),
            author=FeedAuthorResponse(id=author.id, handle=author.handle, display_name=author.display_name),
            rank=FeedRankResponse(score=score, reason=reason),
        )
        for post, author, score, reason, _ in ranked
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
