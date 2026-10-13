import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, SecretStr

from config.settings import LlmSettings
from enums import ChatRole
from messages import ErrorMessage

# Some providers sit behind Cloudflare, which rejects Python's default user agent (error 1010).
USER_AGENT = "speech-resilient-alexa/0.1"


class ChatCompletionsClient:
    """Shared by every provider that speaks the OpenAI-style chat completions API."""

    def __init__(
        self,
        *,
        provider: str,
        key_variable: str,
        api_key: SecretStr | None,
        model_id: str,
        url: str,
        timeout_seconds: float,
        llm: LlmSettings,
        strict_schema: bool = True,
        headers: dict[str, str] | None = None,
        options: dict[str, Any] | None = None,
    ) -> None:
        if not api_key:
            raise ValueError(ErrorMessage.LLM_KEY_MISSING.format(variable=key_variable, provider=provider))
        self._provider = provider
        self._api_key = api_key
        self._model_id = model_id
        self._url = url
        self._timeout_seconds = timeout_seconds
        self._llm = llm
        self._strict_schema = strict_schema
        self._headers = headers or {}
        self._options = options or {}

    def complete(self, system: str, user: str, schema: type[BaseModel] | None = None) -> str:
        payload = {
            "model": self._model_id,
            "messages": [{"role": ChatRole.SYSTEM, "content": system}, {"role": ChatRole.USER, "content": user}],
            "max_tokens": self._llm.max_tokens,
            "temperature": self._llm.temperature,
            **self._options,
        }
        if schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": self._strict_schema,
                    "schema": schema.model_json_schema(),
                },
            }
        request = Request(
            self._url,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self._api_key.get_secret_value()}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
                **self._headers,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                body = json.loads(response.read().decode())
        except HTTPError as error:
            detail = error.read().decode()
            raise RuntimeError(
                ErrorMessage.LLM_REQUEST_FAILED.format(provider=self._provider, detail=detail)
            ) from error
        except URLError as error:
            raise RuntimeError(ErrorMessage.LLM_UNREACHABLE.format(provider=self._provider)) from error
        return body["choices"][0]["message"]["content"]
