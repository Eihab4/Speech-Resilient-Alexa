from enum import StrEnum
from functools import cache
from pathlib import Path

from enums import RequestStatus

PROMPTS_DIR = Path(__file__).parent / "prompts"

REQUEST_ENDINGS = {
    RequestStatus.DONE: "(this request was done)",
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
