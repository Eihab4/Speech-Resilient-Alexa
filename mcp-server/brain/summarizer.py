from typing import Protocol

from brain.llm import LlmClient
from memory.context import render_turns
from memory.models import Turn
from messages import Prompt


class Summarizer(Protocol):
    def summarize(self, previous: str, turns: list[Turn]) -> str: ...


class LlmSummarizer:
    def __init__(self, client: LlmClient) -> None:
        self._client = client

    def summarize(self, previous: str, turns: list[Turn]) -> str:
        return self._client.complete(Prompt.SUMMARIZE.text, render_turns(previous, turns)).strip()


class MockSummarizer:
    def __init__(self, max_words: int) -> None:
        self._max_words = max_words

    def summarize(self, previous: str, turns: list[Turn]) -> str:
        words = render_turns(previous, turns).split()
        return " ".join(words[-self._max_words :])
