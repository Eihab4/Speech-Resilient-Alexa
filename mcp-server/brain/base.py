from typing import Protocol

from brain.schemas import BrainResult


class Brain(Protocol):
    def interpret(self, fragments: list[str]) -> BrainResult: ...
