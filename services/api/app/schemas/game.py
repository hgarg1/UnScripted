from datetime import datetime

from pydantic import BaseModel, Field


class GuessableAccountResponse(BaseModel):
    account_id: str
    handle: str
    display_name: str
    bio: str
    latest_post_excerpt: str | None = None
    recent_activity_count: int = 0
    already_guessed: bool = False


class GuessableAccountsResponse(BaseModel):
    items: list[GuessableAccountResponse]


class SubmitGuessRequest(BaseModel):
    target_account_id: str
    guessed_is_agent: bool = Field(description="True when the user thinks the account is an agent")


class GuessResultResponse(BaseModel):
    id: str
    target_account_id: str
    guessed_is_agent: bool
    was_correct: bool
    actual_account_type: str
    created_at: datetime


class GuessGameScoreResponse(BaseModel):
    attempts: int
    correct: int
    accuracy: float
    last_guess_at: datetime | None = None

