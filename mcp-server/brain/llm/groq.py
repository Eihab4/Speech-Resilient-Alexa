from brain.llm.chat_completions import ChatCompletionsClient
from config import Settings


class GroqClient(ChatCompletionsClient):
    def __init__(self, settings: Settings) -> None:
        groq = settings.groq
        super().__init__(
            provider="Groq",
            key_variable="GROQ_API_KEY",
            api_key=groq.api_key,
            model_id=groq.model_id,
            url=groq.base_url,
            timeout_seconds=groq.timeout_seconds,
            llm=settings.llm,
            # Groq's strict mode needs every object closed, but BrainResult.details is open by design.
            # Best effort still follows the schema, and the brain validates every answer anyway.
            strict_schema=False,
            # gpt-oss thinks before answering, and the thinking counts against LLM_MAX_TOKENS.
            options={"reasoning_effort": groq.reasoning_effort},
        )
