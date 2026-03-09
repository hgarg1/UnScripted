from dataclasses import dataclass
from hashlib import sha256

from fastapi import Header


@dataclass(slots=True)
class RequestActor:
    subject: str
    handle: str
    display_name: str
    role: str

    @property
    def email_hash(self) -> str:
        return sha256(f"{self.subject}@unscripted.local".encode("utf-8")).hexdigest()


def get_request_actor(
    dev_subject: str | None = Header(default=None, alias="x-unscripted-dev-subject"),
    dev_handle: str | None = Header(default=None, alias="x-unscripted-dev-handle"),
    dev_name: str | None = Header(default=None, alias="x-unscripted-dev-name"),
    dev_role: str | None = Header(default=None, alias="x-unscripted-dev-role"),
) -> RequestActor:
    subject = dev_subject or "dev-user"
    handle = dev_handle or "architect"
    display_name = dev_name or handle.title()
    role = dev_role or "member"
    return RequestActor(subject=subject, handle=handle, display_name=display_name, role=role)
