import json

from brain.mock import MockAnswers
from brain.schemas import BrainResult
from config import Settings
from enums import LlmProvider, NextMove
from support import with_client

NO_KEYS = {"LLM_PROVIDER": None, "OPENROUTER_API_KEY": None, "OPENROUTER": None}


async def understand(client, heard):
    result = await client.call_tool("understand_speech", {"user_id": "demo-user", "heard": heard})
    return result.structured_content


def test_mock_provider_is_available_for_offline_tests(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    assert Settings().llm.provider == LlmProvider.MOCK


def test_server_starts_without_any_key_and_answers_from_recordings(server):
    url = server(**NO_KEYS)

    result = with_client(url, lambda client: understand(client, "tomorrow doctor ten"))

    assert result["intent"] == "reminder"
    assert result["next_move"] == NextMove.CONFIRM
    assert "doctor" in result["say"]


def test_unknown_speech_gets_the_fallback(server):
    url = server(**NO_KEYS)

    result = with_client(url, lambda client: understand(client, "banana"))

    assert result["next_move"] == NextMove.ASK
    assert result["say"] == "What would you like me to do?"


def test_recordings_are_valid_results_and_cover_the_demo_scenarios():
    recorded = MockAnswers.model_validate_json(Settings().mock.answers_path.read_text())

    assert all(isinstance(answer, BrainResult) for answer in recorded.answers.values())
    assert {"tomorrow doctor ten", "call sara no mom", "message ahmed running late"} <= recorded.answers.keys()


def test_recordings_match_input_case_and_spacing(server, tmp_path):
    answers = {
        "answers": {"call mom": {"next_move": "confirm", "say": "Call Mom?"}},
        "fallback": {"next_move": "ask", "say": "?"},
    }
    path = tmp_path / "answers.json"
    path.write_text(json.dumps(answers))
    url = server(MOCK_ANSWERS_PATH=str(path), **NO_KEYS)

    result = with_client(url, lambda client: understand(client, "  Call MOM "))

    assert result["say"] == "Call Mom?"
