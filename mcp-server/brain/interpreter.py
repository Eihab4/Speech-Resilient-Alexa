import json

from brain.llm import LlmClient
from brain.schemas import BrainResult
from messages import Prompt


class LlmBrain:
    def __init__(self, client: LlmClient) -> None:
        self._client = client

    def interpret(self, fragments: list[str], history: str = "", person: str = "", question: str = "") -> BrainResult:
        user = json.dumps({"person": person, "history": history, "question": question, "fragments": fragments})
        return BrainResult.model_validate_json(self._client.complete(Prompt.UNDERSTAND_SPEECH.text, user, BrainResult))
