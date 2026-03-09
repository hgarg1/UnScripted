from datetime import datetime

from pydantic import BaseModel, Field


class InviteLoginRequest(BaseModel):
    invite_code: str = Field(min_length=4, max_length=64)
    handle: str = Field(min_length=3, max_length=40)
    display_name: str = Field(min_length=1, max_length=120)
    bio: str = Field(default="", max_length=280)
    consent_version: str = Field(default="v1", max_length=32)


class SessionResponse(BaseModel):
    token: str
    expires_at: datetime


class AuthenticatedUserResponse(BaseModel):
    id: str
    handle: str
    display_name: str
    role: str
    bio: str
    is_agent_account: bool
    session: SessionResponse


class LogoutResponse(BaseModel):
    revoked: bool


class CreateInviteCodeRequest(BaseModel):
    role: str = Field(default="member", max_length=32)
    max_uses: int = Field(default=1, ge=1, le=1000)
    expires_in_hours: int | None = Field(default=168, ge=1, le=24 * 365)


class InviteCodeResponse(BaseModel):
    id: str
    code: str
    role: str
    max_uses: int
    use_count: int
    expires_at: datetime | None
    created_at: datetime
