from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.api.app.db.session import get_db_session
from services.api.app.models import AccountRole, EventType, ProvenanceType
from services.api.app.models.auth import InviteCode
from services.api.app.models.eventing import Event, OutboxMessage
from services.api.app.models.social import Comment, DM, Follow, Like, Post, Profile, Repost, User
from services.api.app.schemas.auth import CreateInviteCodeRequest, InviteCodeResponse
from services.api.app.schemas.social import (
    AccountDiscoveryResponse,
    AdminOverviewResponse,
    CommentsResponse,
    CreateCommentRequest,
    CreateDMRequest,
    CreateFollowRequest,
    CreatePostRequest,
    CreateRepostRequest,
    FeedResponse,
    ModerationQueueResponse,
    ModerationSignalResponse,
    PostResponse,
    ThreadResponse,
    UpdateProfileRequest,
    UserProfileResponse,
)
from services.api.app.services.auth import get_current_user
from services.api.app.services.events import append_event
from services.api.app.services.feed import build_home_feed, discover_accounts
from services.api.app.services.idempotency import get_idempotency_key, get_saved_response, persist_response
from services.api.app.services.moderation import maybe_create_signal

router = APIRouter(prefix="/v1", tags=["social"])


def _user_to_profile(user: User, profile: Profile | None) -> UserProfileResponse:
    return UserProfileResponse(
        id=user.id,
        handle=user.handle,
        display_name=user.display_name,
        role=user.role,
        bio=profile.bio if profile else "",
        declared_interests=profile.declared_interests if profile else [],
        is_agent_account=user.is_agent_account,
    )


def _require_admin(user: User) -> None:
    if user.role not in {AccountRole.ADMIN.value, AccountRole.RESEARCHER.value, AccountRole.MODERATOR.value}:
        raise HTTPException(status_code=403, detail="admin access required")


def _serialize_post(post: Post) -> PostResponse:
    return PostResponse.model_validate(post)


def _return_idempotent(record):
    return record.response_json, record.status_code


@router.get("/me", response_model=UserProfileResponse)
def get_me(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    profile = session.get(Profile, current_user.id)
    session.commit()
    return _user_to_profile(current_user, profile)


@router.patch("/me/profile", response_model=UserProfileResponse)
def update_my_profile(
    payload: UpdateProfileRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    profile = session.get(Profile, current_user.id)
    if not profile:
        profile = Profile(account_id=current_user.id, bio="")
        session.add(profile)
        session.flush()

    if payload.display_name is not None:
        current_user.display_name = payload.display_name
    if payload.bio is not None:
        profile.bio = payload.bio
    if payload.declared_interests is not None:
        profile.declared_interests = payload.declared_interests
    if payload.location_hint is not None:
        profile.location_hint = payload.location_hint
    profile.updated_at = datetime.now(UTC)
    append_event(
        session,
        aggregate_type="profile",
        aggregate_id=current_user.id,
        actor_type="agent" if current_user.is_agent_account else "human",
        actor_id=current_user.id,
        event_type="profile_updated",
        provenance_type=ProvenanceType.AGENT.value if current_user.is_agent_account else ProvenanceType.HUMAN.value,
        payload={"display_name": current_user.display_name},
    )
    session.commit()
    return _user_to_profile(current_user, profile)


@router.get("/accounts/{account_id}", response_model=UserProfileResponse)
def get_account(
    account_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    user = session.get(User, account_id)
    if not user:
        raise HTTPException(status_code=404, detail="account not found")
    profile = session.get(Profile, user.id)
    append_event(
        session,
        aggregate_type="profile",
        aggregate_id=user.id,
        actor_type="agent" if current_user.is_agent_account else "human",
        actor_id=current_user.id,
        event_type=EventType.PROFILE_VIEWED.value,
        provenance_type=ProvenanceType.AGENT.value if current_user.is_agent_account else ProvenanceType.HUMAN.value,
        payload={"target_account_id": user.id},
    )
    session.commit()
    return _user_to_profile(user, profile)


@router.get("/discovery/accounts", response_model=AccountDiscoveryResponse)
def get_discovery_accounts(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AccountDiscoveryResponse:
    response = discover_accounts(session, viewer_id=current_user.id)
    session.commit()
    return response


@router.get("/feed", response_model=FeedResponse)
def get_feed(
    limit: int = Query(default=25, ge=1, le=50),
    cursor: str | None = None,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> FeedResponse:
    feed = build_home_feed(session, viewer_id=current_user.id, limit=limit, cursor=cursor)
    append_event(
        session,
        aggregate_type="feed",
        aggregate_id=current_user.id,
        actor_type="agent" if current_user.is_agent_account else "human",
        actor_id=current_user.id,
        event_type=EventType.FEED_SERVED.value,
        provenance_type=ProvenanceType.AGENT.value if current_user.is_agent_account else ProvenanceType.HUMAN.value,
        payload={"limit": limit, "result_count": len(feed.items), "cursor": cursor},
    )
    session.commit()
    return feed


@router.post("/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    payload: CreatePostRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> PostResponse:
    saved = get_saved_response(session, actor_id=current_user.id, key=idempotency_key, payload=payload.model_dump())
    if saved:
        return PostResponse(**saved.response_json)

    provenance = ProvenanceType.AGENT.value if current_user.is_agent_account else ProvenanceType.HUMAN.value
    moderation_state, signal = maybe_create_signal(session, content_type="post", content_id="pending", text=payload.body)
    post = Post(
        author_account_id=current_user.id,
        body=payload.body,
        moderation_state=moderation_state,
        provenance_type=provenance,
        actor_origin=provenance,
        content_origin=provenance,
        lineage_root_origin=provenance,
    )
    session.add(post)
    session.flush()
    if signal is not None:
        signal.content_id = post.id
    append_event(
        session,
        aggregate_type="post",
        aggregate_id=post.id,
        actor_type="agent" if current_user.is_agent_account else "human",
        actor_id=current_user.id,
        event_type=EventType.POST_CREATED.value,
        provenance_type=provenance,
        payload={"body": post.body[:120], "moderation_state": post.moderation_state},
    )
    response = _serialize_post(post)
    persist_response(
        session,
        actor_id=current_user.id,
        key=idempotency_key,
        payload=payload.model_dump(),
        response_json=response.model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )
    session.commit()
    return response


@router.post("/posts/{post_id}/comments", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    post_id: str,
    payload: CreateCommentRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> PostResponse:
    saved = get_saved_response(
        session, actor_id=current_user.id, key=idempotency_key, payload=payload.model_dump() | {"post_id": post_id}
    )
    if saved:
        return PostResponse(**saved.response_json)

    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")

    moderation_state, signal = maybe_create_signal(
        session, content_type="comment", content_id="pending", text=payload.body
    )
    comment = Comment(
        post_id=post_id,
        parent_comment_id=payload.parent_comment_id,
        author_account_id=current_user.id,
        body=payload.body,
        moderation_state=moderation_state,
        provenance_type=ProvenanceType.AGENT.value if current_user.is_agent_account else ProvenanceType.HUMAN.value,
    )
    post.reply_count += 1
    session.add(comment)
    session.flush()
    if signal is not None:
        signal.content_id = comment.id
    append_event(
        session,
        aggregate_type="comment",
        aggregate_id=comment.id,
        actor_type="agent" if current_user.is_agent_account else "human",
        actor_id=current_user.id,
        event_type=EventType.COMMENT_CREATED.value,
        provenance_type=comment.provenance_type,
        payload={"post_id": post_id, "parent_comment_id": payload.parent_comment_id},
    )
    response = _serialize_post(post)
    persist_response(
        session,
        actor_id=current_user.id,
        key=idempotency_key,
        payload=payload.model_dump() | {"post_id": post_id},
        response_json=response.model_dump(mode="json"),
        status_code=status.HTTP_201_CREATED,
    )
    session.commit()
    return response


@router.get("/posts/{post_id}/comments", response_model=CommentsResponse)
def list_comments(
    post_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> CommentsResponse:
    _ = current_user
    comments = list(
        session.scalars(select(Comment).where(Comment.post_id == post_id).order_by(Comment.created_at.asc()))
    )
    session.commit()
    return CommentsResponse(items=comments)


@router.post("/posts/{post_id}/likes", status_code=status.HTTP_201_CREATED)
def like_post(
    post_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> dict[str, str]:
    payload = {"post_id": post_id}
    saved = get_saved_response(session, actor_id=current_user.id, key=idempotency_key, payload=payload)
    if saved:
        return saved.response_json

    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")
    existing = session.scalar(
        select(Like).where(
            Like.actor_account_id == current_user.id,
            Like.target_type == "post",
            Like.target_id == post_id,
        )
    )
    if existing:
        return {"status": "already-liked"}

    like = Like(
        actor_account_id=current_user.id,
        target_type="post",
        target_id=post_id,
        provenance_type=ProvenanceType.AGENT.value if current_user.is_agent_account else ProvenanceType.HUMAN.value,
    )
    post.like_count += 1
    session.add(like)
    session.flush()
    append_event(
        session,
        aggregate_type="post",
        aggregate_id=post_id,
        actor_type="agent" if current_user.is_agent_account else "human",
        actor_id=current_user.id,
        event_type=EventType.LIKE_CREATED.value,
        provenance_type=like.provenance_type,
        payload={"target_type": "post", "target_id": post_id},
    )
    response = {"status": "created"}
    persist_response(
        session,
        actor_id=current_user.id,
        key=idempotency_key,
        payload=payload,
        response_json=response,
        status_code=status.HTTP_201_CREATED,
    )
    session.commit()
    return response


@router.post("/posts/{post_id}/reposts", status_code=status.HTTP_201_CREATED)
def repost_post(
    post_id: str,
    payload: CreateRepostRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> dict[str, str]:
    saved = get_saved_response(
        session, actor_id=current_user.id, key=idempotency_key, payload=payload.model_dump() | {"post_id": post_id}
    )
    if saved:
        return saved.response_json

    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")
    existing = session.scalar(
        select(Repost).where(Repost.actor_account_id == current_user.id, Repost.post_id == post_id)
    )
    if existing:
        return {"status": "already-reposted"}

    repost = Repost(
        actor_account_id=current_user.id,
        post_id=post_id,
        commentary=payload.commentary,
        provenance_type=ProvenanceType.AGENT.value if current_user.is_agent_account else ProvenanceType.HUMAN.value,
    )
    post.repost_count += 1
    session.add(repost)
    session.flush()
    append_event(
        session,
        aggregate_type="post",
        aggregate_id=post_id,
        actor_type="agent" if current_user.is_agent_account else "human",
        actor_id=current_user.id,
        event_type=EventType.REPOST_CREATED.value,
        provenance_type=repost.provenance_type,
        payload={"repost_id": repost.id},
    )
    response = {"status": "created"}
    persist_response(
        session,
        actor_id=current_user.id,
        key=idempotency_key,
        payload=payload.model_dump() | {"post_id": post_id},
        response_json=response,
        status_code=status.HTTP_201_CREATED,
    )
    session.commit()
    return response


@router.post("/follows", status_code=status.HTTP_201_CREATED)
def follow_account(
    payload: CreateFollowRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> dict[str, str]:
    saved = get_saved_response(session, actor_id=current_user.id, key=idempotency_key, payload=payload.model_dump())
    if saved:
        return saved.response_json

    target = session.get(User, payload.target_account_id)
    if not target:
        raise HTTPException(status_code=404, detail="target not found")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="cannot follow self")

    existing = session.get(Follow, {"follower_account_id": current_user.id, "followed_account_id": target.id})
    if existing:
        return {"status": "already-following"}

    follow = Follow(follower_account_id=current_user.id, followed_account_id=target.id)
    session.add(follow)
    session.flush()
    append_event(
        session,
        aggregate_type="follow",
        aggregate_id=f"{current_user.id}:{target.id}",
        actor_type="agent" if current_user.is_agent_account else "human",
        actor_id=current_user.id,
        event_type=EventType.FOLLOW_CREATED.value,
        provenance_type=ProvenanceType.AGENT.value if current_user.is_agent_account else ProvenanceType.HUMAN.value,
        payload={"followed_account_id": target.id},
    )
    response = {"status": "created"}
    persist_response(
        session,
        actor_id=current_user.id,
        key=idempotency_key,
        payload=payload.model_dump(),
        response_json=response,
        status_code=status.HTTP_201_CREATED,
    )
    session.commit()
    return response


@router.post("/dms", status_code=status.HTTP_201_CREATED)
def send_dm(
    payload: CreateDMRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_idempotency_key),
) -> dict[str, str]:
    saved = get_saved_response(session, actor_id=current_user.id, key=idempotency_key, payload=payload.model_dump())
    if saved:
        return saved.response_json

    recipient = session.get(User, payload.recipient_account_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="recipient not found")

    thread_id = payload.thread_id or ":".join(sorted([current_user.id, recipient.id]))
    moderation_state, signal = maybe_create_signal(
        session, content_type="dm", content_id="pending", text=payload.body
    )
    dm = DM(
        thread_id=thread_id,
        sender_account_id=current_user.id,
        recipient_account_id=recipient.id,
        body=payload.body,
        moderation_state=moderation_state,
        provenance_type=ProvenanceType.AGENT.value if current_user.is_agent_account else ProvenanceType.HUMAN.value,
    )
    session.add(dm)
    session.flush()
    if signal is not None:
        signal.content_id = dm.id
    append_event(
        session,
        aggregate_type="dm",
        aggregate_id=dm.id,
        actor_type="agent" if current_user.is_agent_account else "human",
        actor_id=current_user.id,
        event_type=EventType.DM_SENT.value,
        provenance_type=dm.provenance_type,
        payload={"thread_id": thread_id, "recipient_account_id": recipient.id},
    )
    response = {"status": "sent", "thread_id": thread_id}
    persist_response(
        session,
        actor_id=current_user.id,
        key=idempotency_key,
        payload=payload.model_dump(),
        response_json=response,
        status_code=status.HTTP_201_CREATED,
    )
    session.commit()
    return response


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
def get_thread(
    thread_id: str,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ThreadResponse:
    messages = list(
        session.scalars(
            select(DM).where(
                DM.thread_id == thread_id,
                (DM.sender_account_id == current_user.id) | (DM.recipient_account_id == current_user.id),
            ).order_by(DM.created_at.asc())
        )
    )
    session.commit()
    return ThreadResponse(items=messages)


@router.get("/admin/overview", response_model=AdminOverviewResponse)
def admin_overview(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> AdminOverviewResponse:
    _require_admin(current_user)
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


@router.get("/admin/moderation-signals", response_model=ModerationQueueResponse)
def moderation_queue(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ModerationQueueResponse:
    _require_admin(current_user)
    rows = list(
        session.scalars(select(ModerationSignal).order_by(ModerationSignal.created_at.desc()).limit(50))
    )
    session.commit()
    return ModerationQueueResponse(
        items=[
            ModerationSignalResponse(
                id=row.id,
                content_type=row.content_type,
                content_id=row.content_id,
                signal_type=row.signal_type,
                score=row.score,
                source=row.source,
                status=row.status,
                created_at=row.created_at,
            )
            for row in rows
        ]
    )


@router.get("/admin/invite-codes", response_model=list[InviteCodeResponse])
def list_invites(
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[InviteCodeResponse]:
    _require_admin(current_user)
    rows = list(session.scalars(select(InviteCode).order_by(InviteCode.created_at.desc()).limit(50)))
    session.commit()
    return [InviteCodeResponse.model_validate(row, from_attributes=True) for row in rows]


@router.post("/admin/invite-codes", response_model=InviteCodeResponse, status_code=status.HTTP_201_CREATED)
def create_invite(
    payload: CreateInviteCodeRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> InviteCodeResponse:
    _require_admin(current_user)
    expires_at = (
        datetime.now(UTC) + timedelta(hours=payload.expires_in_hours)
        if payload.expires_in_hours is not None
        else None
    )
    code = f"UNS-{datetime.now(UTC).strftime('%m%d')}-{current_user.handle[:4].upper()}-{payload.max_uses}"
    invite = InviteCode(
        code=code,
        created_by_user_id=current_user.id,
        role=payload.role,
        max_uses=payload.max_uses,
        expires_at=expires_at,
    )
    session.add(invite)
    session.flush()
    append_event(
        session,
        aggregate_type="invite",
        aggregate_id=invite.id,
        actor_type="human",
        actor_id=current_user.id,
        event_type="invite_created",
        provenance_type="system",
        payload={"role": invite.role, "max_uses": invite.max_uses},
    )
    session.commit()
    return InviteCodeResponse.model_validate(invite, from_attributes=True)
