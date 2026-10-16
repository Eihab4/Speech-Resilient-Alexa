from typing import Protocol

from pydantic import BaseModel

from memory import Helper


class Position(BaseModel):
    latitude: float
    longitude: float


class Notifier(Protocol):
    """The one way a message leaves the server. Raises when the helper could not be reached."""

    def notify(self, helper: Helper, text: str, position: Position | None = None) -> None: ...
