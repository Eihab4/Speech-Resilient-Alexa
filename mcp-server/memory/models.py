from typing import Any

from pydantic import BaseModel, Field

from enums import NextMove, RequestStatus
from utils import new_id, utc_now


class Turn(BaseModel):
    seq: int = 0
    request_id: str | None = None
    heard: str
    say: str
    next_move: NextMove
    created_at: str = Field(default_factory=utc_now)


class Request(BaseModel):
    id: str = Field(default_factory=lambda: new_id("p"))
    intent: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    status: RequestStatus = RequestStatus.PENDING
    updated_at: str = Field(default_factory=utc_now)


class Summary(BaseModel):
    text: str = ""
    covers_up_to_seq: int = 0


class Action(BaseModel):
    request_id: str
    result: str
    created_at: str
