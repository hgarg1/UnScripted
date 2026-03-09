from datetime import datetime

from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    id: str
    handle: str
    display_name: str
    role: str
    bio: str = ""
    declared_interests: list[str] = []
    is_agent_account: bool = False


class CreatePostRequest(BaseModel):
    body: str = Field(min_length=1, max_length=280)


class CreateCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=280)
    parent_comment_id: str | None = None


class CreateFollowRequest(BaseModel):
    target_account_id: str


class CreateDMRequest(BaseModel):
    recipient_account_id: str
    body: str = Field(min_length=1, max_length=1000)
    thread_id: str | None = None


class CreateRepostRequest(BaseModel):
    commentary: str | None = Field(default=None, max_length=280)


class CreateUserRequest(BaseModel):
    handle: str = Field(min_length=3, max_length=40)
    display_name: str = Field(min_length=1, max_length=120)
    bio: str = Field(default="", max_length=280)


class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    bio: str | None = Field(default=None, max_length=280)
    declared_interests: list[str] | None = None
    location_hint: str | None = Field(default=None, max_length=120)


class PostResponse(BaseModel):
    id: str
    author_account_id: str
    body: str
    provenance_type: str
    moderation_state: str
    created_at: datetime
    like_count: int
    reply_count: int
    repost_count: int

    model_config = {"from_attributes": True}


class FeedAuthorResponse(BaseModel):
    id: str
    handle: str
    display_name: str


class FeedRankResponse(BaseModel):
    score: float
    reason: str


class FeedItemResponse(BaseModel):
    post: PostResponse
    author: FeedAuthorResponse
    rank: FeedRankResponse


class FeedResponse(BaseModel):
    items: list[FeedItemResponse]
    next_cursor: str | None = None


class AccountSummaryResponse(BaseModel):
    id: str
    handle: str
    display_name: str
    bio: str
    is_agent_account: bool
    is_following: bool


class AccountDiscoveryResponse(BaseModel):
    items: list[AccountSummaryResponse]


class CommentResponse(BaseModel):
    id: str
    post_id: str
    author_account_id: str
    body: str
    moderation_state: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CommentsResponse(BaseModel):
    items: list[CommentResponse]


class DirectMessageResponse(BaseModel):
    id: str
    thread_id: str
    sender_account_id: str
    recipient_account_id: str
    body: str
    moderation_state: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ThreadResponse(BaseModel):
    items: list[DirectMessageResponse]


class ModerationSignalResponse(BaseModel):
    id: str
    content_type: str
    content_id: str
    signal_type: str
    score: float
    source: str
    status: str
    created_at: datetime


class ModerationQueueResponse(BaseModel):
    items: list[ModerationSignalResponse]


class AdminOverviewResponse(BaseModel):
    total_users: int
    total_agents: int
    total_posts: int
    total_events: int
    pending_outbox: int
