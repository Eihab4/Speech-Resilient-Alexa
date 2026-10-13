from brain.llm.chat_completions import ChatCompletionsClient
from config import Settings


class OpenRouterClient(ChatCompletionsClient):
    def __init__(self, settings: Settings) -> None:
        openrouter = settings.openrouter
        super().__init__(
            provider="OpenRouter",
            key_variable="OPENROUTER_API_KEY",
            api_key=openrouter.api_key,
            model_id=openrouter.model_id,
            url=openrouter.base_url,
            timeout_seconds=openrouter.timeout_seconds,
            llm=settings.llm,
            headers={"X-OpenRouter-Title": openrouter.app_title},
        )
