from enum import StrEnum


class NextMove(StrEnum):
    LISTEN = "listen"
    ASK = "ask"
    CONFIRM = "confirm"


class RequestStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DONE = "done"
    CANCELLED = "cancelled"
