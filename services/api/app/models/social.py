from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.api.app.db.base import Base
from services.api.app.models.common import new_id, utc_now
from services.api.app.models.enums import AccountRole, AccountStatus, ProvenanceType


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_auth_subject", "auth_subject", unique=True),
        Index("ix_users_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    auth_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    handle: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=AccountStatus.ACTIVE.value, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default=AccountRole.MEMBER.value, nullable=False)
    consent_version: Mapped[str] = mapped_column(String(32), default="v1", nullable=False)
    is_agent_account: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    invite_code_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    profile: Mapped["Profile"] = relationship(back_populates="account", uselist=False)


class Profile(Base):
    __tablename__ = "profiles"

    account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    bio: Mapped[str] = mapped_column(Text, default="", nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    declared_interests: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    location_hint: Mapped[str | None] = mapped_column(String(120), nullable=True)
    visibility_flags: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    account: Mapped[User] = relationship(back_populates="profile")


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        Index("ix_posts_author_created_at", "author_account_id", "created_at"),
        Index("ix_posts_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    author_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(12), default="en", nullable=False)
    topic_embedding: Mapped[list[float]] = mapped_column(JSON, default=list, nullable=False)
    reply_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    repost_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quote_post_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("posts.id"), nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), default="public", nullable=False)
    moderation_state: Mapped[str] = mapped_column(String(16), default="clear", nullable=False)
    provenance_type: Mapped[str] = mapped_column(
        String(16), default=ProvenanceType.HUMAN.value, nullable=False
    )
    actor_origin: Mapped[str] = mapped_column(String(16), default=ProvenanceType.HUMAN.value, nullable=False)
    content_origin: Mapped[str] = mapped_column(String(16), default=ProvenanceType.HUMAN.value, nullable=False)
    lineage_root_origin: Mapped[str] = mapped_column(
        String(16), default=ProvenanceType.HUMAN.value, nullable=False
    )
    generator_model_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    scenario_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contains_synthetic_ancestry: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_post_created_at", "post_id", "created_at"),
        Index("ix_comments_author_created_at", "author_account_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    post_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    parent_comment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )
    author_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    moderation_state: Mapped[str] = mapped_column(String(16), default="clear", nullable=False)
    provenance_type: Mapped[str] = mapped_column(
        String(16), default=ProvenanceType.HUMAN.value, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (
        UniqueConstraint("actor_account_id", "target_type", "target_id", name="uq_likes_actor_target"),
        Index("ix_likes_target", "target_type", "target_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    provenance_type: Mapped[str] = mapped_column(
        String(16), default=ProvenanceType.HUMAN.value, nullable=False
    )


class Repost(Base):
    __tablename__ = "reposts"
    __table_args__ = (
        UniqueConstraint("actor_account_id", "post_id", name="uq_reposts_actor_post"),
        Index("ix_reposts_post_created_at", "post_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    post_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    commentary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    provenance_type: Mapped[str] = mapped_column(
        String(16), default=ProvenanceType.HUMAN.value, nullable=False
    )


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (
        UniqueConstraint(
            "follower_account_id",
            "followed_account_id",
            name="uq_follows_follower_followed",
        ),
        Index("ix_follows_followed_created_at", "followed_account_id", "created_at"),
    )

    follower_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    followed_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    state: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)


class DM(Base):
    __tablename__ = "dms"
    __table_args__ = (
        Index("ix_dms_thread_created_at", "thread_id", "created_at"),
        Index("ix_dms_recipient_created_at", "recipient_account_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    thread_id: Mapped[str] = mapped_column(String(72), nullable=False)
    sender_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recipient_account_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_state: Mapped[str] = mapped_column(String(16), default="sent", nullable=False)
    moderation_state: Mapped[str] = mapped_column(String(16), default="clear", nullable=False)
    provenance_type: Mapped[str] = mapped_column(
        String(16), default=ProvenanceType.HUMAN.value, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
