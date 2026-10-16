from secrets import token_urlsafe
from typing import Any

from pydantic import BaseModel, Field

from enums import AlertStatus, NextMove, RequestStatus
from utils import new_id, utc_now


class Turn(BaseModel):
    seq: int = 0
    request_id: str | None = None
    heard: str
    say: str
    next_move: NextMove
    created_at: str = Field(default_factory=utc_now)
    request_status: RequestStatus | None = None  # filled only when read from the history


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


class Profile(BaseModel):
    name: str
    home_address: str | None = None


class Helper(BaseModel):
    id: str = Field(default_factory=lambda: new_id("h"))
    name: str
    # Opens the bot as t.me/<bot>?start=<link_code>; Telegram allows letters, digits, _ and - there.
    link_code: str = Field(default_factory=lambda: token_urlsafe(12))
    telegram_chat_id: str | None = None
    linked_at: str | None = None
    created_at: str = Field(default_factory=utc_now)

    @property
    def linked(self) -> bool:
        return self.telegram_chat_id is not None


class Alert(BaseModel):
    id: str = Field(default_factory=lambda: new_id("a"))
    heard: str = ""
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    text: str
    status: AlertStatus
    created_at: str = Field(default_factory=utc_now)
