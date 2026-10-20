from typing import Protocol

from brain.schemas import BrainResult
from enums import AskMode


class Brain(Protocol):
    def interpret(
        self,
        fragments: list[str],
        history: str = "",
        person: str = "",
        question: str = "",
        mode: AskMode = AskMode.OPEN,
    ) -> BrainResult: ...
