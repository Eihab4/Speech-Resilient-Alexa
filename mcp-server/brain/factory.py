from brain.base import Brain
from brain.interpreter import LlmBrain
from brain.llm import BedrockClient, GroqClient, LlmClient, OpenRouterClient
from brain.mock import MockBrain
from brain.summarizer import LlmSummarizer, MockSummarizer, Summarizer
from config import Settings, get_settings
from enums import LlmProvider

CLIENTS = {
    LlmProvider.BEDROCK: BedrockClient,
    LlmProvider.OPENROUTER: OpenRouterClient,
    LlmProvider.GROQ: GroqClient,
}


def create_client(settings: Settings) -> LlmClient:
    return CLIENTS[settings.llm.provider](settings)


def create_brain(settings: Settings | None = None) -> Brain:
    config = settings or get_settings()
    if config.llm.provider == LlmProvider.MOCK:
        return MockBrain(config)
    return LlmBrain(create_client(config))


def create_summarizer(settings: Settings | None = None) -> Summarizer:
    config = settings or get_settings()
    if config.llm.provider == LlmProvider.MOCK:
        return MockSummarizer(config.memory.summary_trigger_words)
    return LlmSummarizer(create_client(config))
