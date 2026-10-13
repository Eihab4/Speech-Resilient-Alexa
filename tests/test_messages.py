from string import Formatter

import pytest

from brain.factory import create_brain
from brain.interpreter import LlmBrain
from brain.llm import GroqClient, OpenRouterClient
from config import Settings
from enums import Intent, NextMove
from messages import ACTION_RESULTS, ErrorMessage, Prompt, Reply
from support import needs_real_llm, with_client


@pytest.mark.parametrize("prompt", list(Prompt))
def test_every_prompt_has_text(prompt):
    assert prompt.text.strip()


def test_missing_openrouter_key_uses_the_central_message(monkeypatch):
    monkeypatch.delenv("OPENROUTER", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "")

    message = ErrorMessage.LLM_KEY_MISSING.format(variable="OPENROUTER_API_KEY", provider="OpenRouter")

    with pytest.raises(ValueError, match=message):
        OpenRouterClient(Settings())


def test_missing_groq_key_uses_the_central_message(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "")
    message = ErrorMessage.LLM_KEY_MISSING.format(variable="GROQ_API_KEY", provider="Groq")

    with pytest.raises(ValueError, match=message):
        GroqClient(Settings())


def test_rejected_openrouter_key_uses_the_central_message(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "invalid-key")
    prefix = ErrorMessage.LLM_REQUEST_FAILED.format(provider="OpenRouter", detail="")

    with pytest.raises(RuntimeError, match=f"^{prefix}"):
        LlmBrain(OpenRouterClient(Settings())).interpret(["call mom"])


def test_blank_speech_gets_the_central_reply_over_mcp(server):
    url = server(LLM_PROVIDER="bedrock")

    async def call(client):
        result = await client.call_tool("understand_speech", {"user_id": "demo-user", "heard": "   "})
        return result.structured_content

    result = with_client(url, call)

    assert result["next_move"] == NextMove.LISTEN
    assert result["say"] == Reply.STILL_LISTENING


@needs_real_llm
def test_real_llm_answers_with_the_central_prompt():
    result = create_brain().interpret(["tomorrow", "doctor", "ten"])

    assert result.next_move in NextMove
    assert result.say


@pytest.mark.parametrize("intent", list(Intent))
def test_the_prompt_names_every_detail_an_action_needs(intent):
    keys = [field for _, field, _, _ in Formatter().parse(ACTION_RESULTS[intent]) if field]

    assert f"- {intent}:" in Prompt.UNDERSTAND_SPEECH.text
    for key in keys:
        assert f'"{key}"' in Prompt.UNDERSTAND_SPEECH.text
