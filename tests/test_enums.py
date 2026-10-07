import pytest
from pydantic import ValidationError

from brain.bedrock import BedrockBrain
from brain.factory import BRAINS, create_brain
from brain.schemas import BrainResult
from config import Settings
from enums import LlmProvider, NextMove


def test_every_provider_has_a_brain():
    assert set(BRAINS) == set(LlmProvider)


def test_factory_builds_the_configured_brain(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", LlmProvider.BEDROCK)

    assert isinstance(create_brain(Settings()), BedrockBrain)


def test_brain_result_rejects_an_unknown_move():
    with pytest.raises(ValidationError):
        BrainResult(next_move="dance", say="hi")


def test_llm_schema_offers_exactly_the_known_moves():
    schema = BrainResult.model_json_schema()

    assert schema["$defs"]["NextMove"]["enum"] == [move.value for move in NextMove]
