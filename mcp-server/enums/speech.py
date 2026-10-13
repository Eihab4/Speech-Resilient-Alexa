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


class TranscriptType(StrEnum):
    """What the /transcribe WebSocket sends back to the page."""

    PARTIAL = "partial"  # still being said; may change
    FINAL = "final"  # the person paused; this piece is one turn
    UNAVAILABLE = "unavailable"  # Transcribe could not start; the page falls back to the browser
    ERROR = "error"  # Transcribe failed after it started
