from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.core.auth import RequestActor
from services.api.app.models.social import Profile, User


def ensure_user_for_actor(session: Session, actor: RequestActor) -> User:
    user = session.scalar(select(User).where(User.auth_subject == actor.subject))
    if user:
        return user

    user = User(
        auth_subject=actor.subject,
        handle=actor.handle,
        display_name=actor.display_name,
        email_hash=actor.email_hash,
        role=actor.role,
    )
    profile = Profile(account=user, bio="")
    session.add_all([user, profile])
    session.flush()
    return user
