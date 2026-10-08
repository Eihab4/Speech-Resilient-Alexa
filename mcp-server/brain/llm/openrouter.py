import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel

from config import Settings
from enums import ChatRole
from messages import ErrorMessage


class OpenRouterClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.openrouter.api_key:
            raise ValueError(ErrorMessage.OPENROUTER_KEY_MISSING)
        self._settings = settings.openrouter
        self._llm = settings.llm

    def complete(self, system: str, user: str, schema: type[BaseModel] | None = None) -> str:
        payload = {
            "model": self._settings.model_id,
            "messages": [{"role": ChatRole.SYSTEM, "content": system}, {"role": ChatRole.USER, "content": user}],
            "max_tokens": self._llm.max_tokens,
            "temperature": self._llm.temperature,
        }
        if schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "strict": True, "schema": schema.model_json_schema()},
            }
        request = Request(
            self._settings.base_url,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self._settings.api_key.get_secret_value()}",
                "Content-Type": "application/json",
                "X-OpenRouter-Title": self._settings.app_title,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._settings.timeout_seconds) as response:
                body = json.loads(response.read().decode())
        except HTTPError as error:
            raise RuntimeError(ErrorMessage.OPENROUTER_REQUEST_FAILED.format(detail=error.read().decode())) from error
        except URLError as error:
            raise RuntimeError(ErrorMessage.OPENROUTER_UNREACHABLE) from error
        return body["choices"][0]["message"]["content"]
