from enum import StrEnum


class NextMove(StrEnum):
    LISTEN = "listen"
    ASK = "ask"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    DONE = "done"


class Intent(StrEnum):
    REMINDER = "reminder"
    MESSAGE = "message"
    CALL = "call"


class RequestStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DONE = "done"
    CANCELLED = "cancelled"
