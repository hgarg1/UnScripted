from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.api.app.core.auth import RequestActor, get_request_actor
from services.api.app.db.session import get_db_session
from services.api.app.models import AccountRole, EventType, ProvenanceType
from services.api.app.models.eventing import Event, OutboxMessage
from services.api.app.models.social import Comment, DM, Follow, Like, Post, Profile, Repost, User
from services.api.app.schemas.social import (
    AdminOverviewResponse,
    CreateCommentRequest,
    CreateDMRequest,
    CreateFollowRequest,
    CreatePostRequest,
    CreateRepostRequest,
    CreateUserRequest,
    FeedResponse,
    PostResponse,
    UserProfileResponse,
)
from services.api.app.services.accounts import ensure_user_for_actor
from services.api.app.services.events import append_event
from services.api.app.services.feed import build_home_feed

router = APIRouter(prefix="/v1", tags=["social"])


def _user_to_profile(user: User, profile: Profile | None) -> UserProfileResponse:
    return UserProfileResponse(
        id=user.id,
        handle=user.handle,
        display_name=user.display_name,
        role=user.role,
        bio=profile.bio if profile else "",
        is_agent_account=user.is_agent_account,
    )


@router.post("/accounts/register", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
def register_account(
    payload: CreateUserRequest,
    session: Session = Depends(get_db_session),
    actor: RequestActor = Depends(get_request_actor),
) -> UserProfileResponse:
    existing = session.scalar(select(User).where(User.auth_subject == actor.subject))
    if existing:
        profile = session.get(Profile, existing.id)
        return _user_to_profile(existing, profile)

    user = User(
        auth_subject=actor.subject,
        handle=payload.handle,
        display_name=payload.display_name,
        email_hash=actor.email_hash,
        role=actor.role,
    )
    profile = Profile(account=user, bio=payload.bio)
    session.add_all([user, profile])
    session.flush()
    append_event(
        session,
        aggregate_type="user",
        aggregate_id=user.id,
        actor_type="human",
        actor_id=user.id,
        event_type="account_registered",
        provenance_type=ProvenanceType.HUMAN.value,
        payload={"handle": user.handle},
    )
    session.commit()
    return _user_to_profile(user, profile)


@router.get("/me", response_model=UserProfileResponse)
def get_me(
    session: Session = Depends(get_db_session),
    actor: RequestActor = Depends(get_request_actor),
) -> UserProfileResponse:
    user = ensure_user_for_actor(session, actor)
    profile = session.get(Profile, user.id)
    session.commit()
    return _user_to_profile(user, profile)


@router.get("/feed", response_model=FeedResponse)
def get_feed(
    limit: int = 25,
    session: Session = Depends(get_db_session),
    actor: RequestActor = Depends(get_request_actor),
) -> FeedResponse:
    user = ensure_user_for_actor(session, actor)
    feed = build_home_feed(session, viewer_id=user.id, limit=min(limit, 50))
    append_event(
        session,
        aggregate_type="feed",
        aggregate_id=user.id,
        actor_type="human",
        actor_id=user.id,
        event_type=EventType.FEED_SERVED.value,
        provenance_type=ProvenanceType.HUMAN.value,
        payload={"limit": limit, "result_count": len(feed.items)},
    )
    session.commit()
    return feed


@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    payload: CreatePostRequest,
    session: Session = Depends(get_db_session),
    actor: RequestActor = Depends(get_request_actor),
) -> PostResponse:
    user = ensure_user_for_actor(session, actor)
    provenance = ProvenanceType.AGENT.value if user.is_agent_account else ProvenanceType.HUMAN.value
    post = Post(
        author_account_id=user.id,
        body=payload.body,
        provenance_type=provenance,
        actor_origin=provenance,
        content_origin=provenance,
        lineage_root_origin=provenance,
    )
    session.add(post)
    session.flush()
    append_event(
        session,
        aggregate_type="post",
        aggregate_id=post.id,
        actor_type="agent" if user.is_agent_account else "human",
        actor_id=user.id,
        event_type=EventType.POST_CREATED.value,
        provenance_type=provenance,
        payload={"body": post.body[:120]},
    )
    session.commit()
    return PostResponse.model_validate(post)


@router.post("/posts/{post_id}/comments", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    post_id: str,
    payload: CreateCommentRequest,
    session: Session = Depends(get_db_session),
    actor: RequestActor = Depends(get_request_actor),
) -> PostResponse:
    user = ensure_user_for_actor(session, actor)
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")

    comment = Comment(
        post_id=post_id,
        parent_comment_id=payload.parent_comment_id,
        author_account_id=user.id,
        body=payload.body,
        provenance_type=ProvenanceType.AGENT.value if user.is_agent_account else ProvenanceType.HUMAN.value,
    )
    post.reply_count += 1
    session.add(comment)
    session.flush()
    append_event(
        session,
        aggregate_type="comment",
        aggregate_id=comment.id,
        actor_type="agent" if user.is_agent_account else "human",
        actor_id=user.id,
        event_type=EventType.COMMENT_CREATED.value,
        provenance_type=comment.provenance_type,
        payload={"post_id": post_id, "parent_comment_id": payload.parent_comment_id},
    )
    session.commit()
    return PostResponse.model_validate(post)


@router.post("/posts/{post_id}/likes", status_code=status.HTTP_201_CREATED)
def like_post(
    post_id: str,
    session: Session = Depends(get_db_session),
    actor: RequestActor = Depends(get_request_actor),
) -> dict[str, str]:
    user = ensure_user_for_actor(session, actor)
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")

    existing = session.scalar(
        select(Like).where(
            Like.actor_account_id == user.id,
            Like.target_type == "post",
            Like.target_id == post_id,
        )
    )
    if existing:
        return {"status": "already-liked"}

    like = Like(
        actor_account_id=user.id,
        target_type="post",
        target_id=post_id,
        provenance_type=ProvenanceType.AGENT.value if user.is_agent_account else ProvenanceType.HUMAN.value,
    )
    post.like_count += 1
    session.add(like)
    session.flush()
    append_event(
        session,
        aggregate_type="post",
        aggregate_id=post_id,
        actor_type="agent" if user.is_agent_account else "human",
        actor_id=user.id,
        event_type=EventType.LIKE_CREATED.value,
        provenance_type=like.provenance_type,
        payload={"target_type": "post", "target_id": post_id},
    )
    session.commit()
    return {"status": "created"}


@router.post("/posts/{post_id}/reposts", status_code=status.HTTP_201_CREATED)
def repost_post(
    post_id: str,
    payload: CreateRepostRequest,
    session: Session = Depends(get_db_session),
    actor: RequestActor = Depends(get_request_actor),
) -> dict[str, str]:
    user = ensure_user_for_actor(session, actor)
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")

    existing = session.scalar(
        select(Repost).where(Repost.actor_account_id == user.id, Repost.post_id == post_id)
    )
    if existing:
        return {"status": "already-reposted"}

    repost = Repost(
        actor_account_id=user.id,
        post_id=post_id,
        commentary=payload.commentary,
        provenance_type=ProvenanceType.AGENT.value if user.is_agent_account else ProvenanceType.HUMAN.value,
    )
    post.repost_count += 1
    session.add(repost)
    session.flush()
    append_event(
        session,
        aggregate_type="post",
        aggregate_id=post_id,
        actor_type="agent" if user.is_agent_account else "human",
        actor_id=user.id,
        event_type=EventType.REPOST_CREATED.value,
        provenance_type=repost.provenance_type,
        payload={"repost_id": repost.id},
    )
    session.commit()
    return {"status": "created"}


@router.post("/follows", status_code=status.HTTP_201_CREATED)
def follow_account(
    payload: CreateFollowRequest,
    session: Session = Depends(get_db_session),
    actor: RequestActor = Depends(get_request_actor),
) -> dict[str, str]:
    user = ensure_user_for_actor(session, actor)
    target = session.get(User, payload.target_account_id)
    if not target:
        raise HTTPException(status_code=404, detail="target not found")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="cannot follow self")

    existing = session.get(Follow, {"follower_account_id": user.id, "followed_account_id": target.id})
    if existing:
        return {"status": "already-following"}

    follow = Follow(follower_account_id=user.id, followed_account_id=target.id)
    session.add(follow)
    session.flush()
    append_event(
        session,
        aggregate_type="follow",
        aggregate_id=f"{user.id}:{target.id}",
        actor_type="agent" if user.is_agent_account else "human",
        actor_id=user.id,
        event_type=EventType.FOLLOW_CREATED.value,
        provenance_type=ProvenanceType.AGENT.value if user.is_agent_account else ProvenanceType.HUMAN.value,
        payload={"followed_account_id": target.id},
    )
    session.commit()
    return {"status": "created"}


@router.post("/dms", status_code=status.HTTP_201_CREATED)
def send_dm(
    payload: CreateDMRequest,
    session: Session = Depends(get_db_session),
    actor: RequestActor = Depends(get_request_actor),
) -> dict[str, str]:
    user = ensure_user_for_actor(session, actor)
    recipient = session.get(User, payload.recipient_account_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="recipient not found")

    thread_id = payload.thread_id or ":".join(sorted([user.id, recipient.id]))
    dm = DM(
        thread_id=thread_id,
        sender_account_id=user.id,
        recipient_account_id=recipient.id,
        body=payload.body,
        provenance_type=ProvenanceType.AGENT.value if user.is_agent_account else ProvenanceType.HUMAN.value,
    )
    session.add(dm)
    session.flush()
    append_event(
        session,
        aggregate_type="dm",
        aggregate_id=dm.id,
        actor_type="agent" if user.is_agent_account else "human",
        actor_id=user.id,
        event_type=EventType.DM_SENT.value,
        provenance_type=dm.provenance_type,
        payload={"thread_id": thread_id, "recipient_account_id": recipient.id},
    )
    session.commit()
    return {"status": "sent", "thread_id": thread_id}


@router.get("/admin/overview", response_model=AdminOverviewResponse)
def admin_overview(
    session: Session = Depends(get_db_session),
    actor: RequestActor = Depends(get_request_actor),
) -> AdminOverviewResponse:
    user = ensure_user_for_actor(session, actor)
    if user.role not in {AccountRole.ADMIN.value, AccountRole.RESEARCHER.value, AccountRole.MODERATOR.value}:
        raise HTTPException(status_code=403, detail="admin access required")

    total_users = session.scalar(select(func.count()).select_from(User)) or 0
    total_agents = session.scalar(select(func.count()).select_from(User).where(User.is_agent_account.is_(True))) or 0
    total_posts = session.scalar(select(func.count()).select_from(Post)) or 0
    total_events = session.scalar(select(func.count()).select_from(Event)) or 0
    pending_outbox = (
        session.scalar(select(func.count()).select_from(OutboxMessage).where(OutboxMessage.status == "pending"))
        or 0
    )
    session.commit()
    return AdminOverviewResponse(
        total_users=total_users,
        total_agents=total_agents,
        total_posts=total_posts,
        total_events=total_events,
        pending_outbox=pending_outbox,
    )
