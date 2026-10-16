import pytest
from pydantic import ValidationError

from brain.factory import CLIENTS, create_brain
from brain.interpreter import LlmBrain
from brain.llm import BedrockClient
from brain.schemas import BrainResult
from config import Settings
from enums import LlmProvider, NextMove


def test_every_real_provider_has_a_client():
    assert set(CLIENTS) | {LlmProvider.MOCK} == set(LlmProvider)


def test_factory_builds_the_configured_brain(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", LlmProvider.BEDROCK)

    brain = create_brain(Settings())

    assert isinstance(brain, LlmBrain)
    assert isinstance(brain._client, BedrockClient)


def test_brain_result_rejects_an_unknown_move():
    with pytest.raises(ValidationError):
        BrainResult(next_move="dance", say="hi")


def test_llm_schema_offers_exactly_the_known_moves():
    schema = BrainResult.model_json_schema()

    assert schema["$defs"]["NextMove"]["enum"] == [move.value for move in NextMove]


def test_a_brain_result_continues_the_open_request_unless_told_otherwise():
    assert BrainResult(next_move=NextMove.LISTEN, say="Mm-hm").new_request is False


def test_llm_schema_lets_the_brain_flag_a_new_request():
    schema = BrainResult.model_json_schema()

    assert schema["properties"]["new_request"]["type"] == "boolean"
