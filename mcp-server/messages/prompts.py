from enum import StrEnum
from functools import cache
from pathlib import Path

from enums import RequestStatus

PROMPTS_DIR = Path(__file__).parent / "prompts"

# Shown to the brain after a request in the history that ended without being done.
REQUEST_ENDINGS = {
    RequestStatus.CANCELLED: "(this request was cancelled)",
    RequestStatus.REPLACED: "(this request was left unfinished: the person moved to another request)",
}


class Prompt(StrEnum):
    UNDERSTAND_SPEECH = "understand_speech"
    SUMMARIZE = "summarize"

    @property
    def text(self) -> str:
        return read_prompt(self)


@cache
def read_prompt(prompt: Prompt) -> str:
    return (PROMPTS_DIR / f"{prompt}.txt").read_text()
