from pydantic import BaseModel

from brain.schemas import BrainResult
from config import Settings, get_settings


class MockAnswers(BaseModel):
    answers: dict[str, BrainResult]
    fallback: BrainResult


class MockBrain:
    def __init__(self, settings: Settings | None = None) -> None:
        config = settings or get_settings()
        self._recorded = MockAnswers.model_validate_json(config.mock.answers_path.read_text())

    def interpret(self, fragments: list[str], history: str = "", person: str = "", question: str = "") -> BrainResult:
        key = " ".join(fragment.lower().strip() for fragment in fragments)
        return self._recorded.answers.get(key, self._recorded.fallback)
