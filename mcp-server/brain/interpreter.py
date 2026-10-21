import json
from datetime import datetime
from zoneinfo import ZoneInfo

from brain.llm import LlmClient
from brain.schemas import BrainResult
from enums import AskMode
from messages import Prompt


class LlmBrain:
    def __init__(self, client: LlmClient, timezone: str = "Africa/Cairo") -> None:
        self._client = client
        self._timezone = timezone

    def interpret(
        self,
        fragments: list[str],
        history: str = "",
        person: str = "",
        question: str = "",
        mode: AskMode = AskMode.OPEN,
    ) -> BrainResult:
        user = json.dumps(
            {
                "person": person,
                "history": history,
                "question": question,
                "mode": mode,
                "fragments": fragments,
                "current_time": datetime.now(ZoneInfo(self._timezone)).isoformat(timespec="seconds"),
                "timezone": self._timezone,
            }
        )
        return BrainResult.model_validate_json(self._client.complete(Prompt.UNDERSTAND_SPEECH.text, user, BrainResult))
