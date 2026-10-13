import pytest

from brain.interpreter import LlmBrain
from brain.llm import OpenRouterClient
from config import Settings
from enums import NextMove
from messages import ErrorMessage, Prompt, Reply
from support import with_client


@pytest.mark.parametrize("prompt", list(Prompt))
def test_every_prompt_has_text(prompt):
    assert prompt.text.strip()


def test_missing_openrouter_key_uses_the_central_message(monkeypatch):
    monkeypatch.delenv("OPENROUTER", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "")

    with pytest.raises(ValueError, match=ErrorMessage.OPENROUTER_KEY_MISSING):
        OpenRouterClient(Settings())


def test_rejected_openrouter_key_uses_the_central_message(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "invalid-key")
    prefix = ErrorMessage.OPENROUTER_REQUEST_FAILED.split("{")[0]

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


@pytest.mark.skipif(not Settings().openrouter.api_key, reason="needs OPENROUTER_API_KEY")
def test_real_llm_answers_with_the_central_prompt():
    result = LlmBrain(OpenRouterClient(Settings())).interpret(["tomorrow", "doctor", "ten"])

    assert result.next_move in NextMove
    assert result.say
