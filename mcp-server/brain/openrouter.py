import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from brain.schemas import BrainResult
from config import Settings, get_settings


SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "understand_speech.txt").read_text()


class OpenRouterBrain:
    def __init__(self, settings: Settings | None = None) -> None:
        config = settings or get_settings()
        if config.openrouter_api_key is None:
            raise ValueError("OPENROUTER_API_KEY is required for OpenRouter")
        self._api_key = config.openrouter_api_key.get_secret_value()
        self._model_id = config.openrouter_model_id
        self._max_tokens = config.llm_max_tokens

    def interpret(self, fragments: list[str]) -> BrainResult:
        payload = {
            "model": self._model_id,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({"fragments": fragments})},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "brain_result",
                    "strict": True,
                    "schema": BrainResult.model_json_schema(),
                },
            },
            "max_tokens": self._max_tokens,
            "temperature": 0,
        }
        request = Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "X-OpenRouter-Title": "Speech-Resilient Alexa",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode())
        except HTTPError as error:
            detail = error.read().decode()
            raise RuntimeError(f"OpenRouter request failed: {detail}") from error
        except URLError as error:
            raise RuntimeError("Could not reach OpenRouter") from error

        content = body["choices"][0]["message"]["content"]
        return BrainResult.model_validate_json(content)
