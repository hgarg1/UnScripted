from enum import StrEnum


class AccountStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class AccountRole(StrEnum):
    MEMBER = "member"
    MODERATOR = "moderator"
    RESEARCHER = "researcher"
    ADMIN = "admin"
    SERVICE_AGENT = "service-agent"


class ProvenanceType(StrEnum):
    HUMAN = "human"
    AGENT = "agent"
    MIXED = "mixed"
    SYSTEM = "system"


class EventType(StrEnum):
    POST_CREATED = "post_created"
    COMMENT_CREATED = "comment_created"
    LIKE_CREATED = "like_created"
    REPOST_CREATED = "repost_created"
    FOLLOW_CREATED = "follow_created"
    DM_SENT = "dm_sent"
    FEED_SERVED = "feed_served"
    PROFILE_VIEWED = "profile_viewed"
    AGENT_GENERATED_POST = "agent_generated_post"
    AGENT_GENERATED_COMMENT = "agent_generated_comment"
    MODERATION_FLAGGED = "moderation_flagged"
    TREND_PROMOTED = "trend_promoted"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PUBLISHED = "published"
    FAILED = "failed"
