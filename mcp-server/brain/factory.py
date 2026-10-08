from brain.base import Brain
from brain.bedrock import BedrockBrain
from brain.mock import MockBrain
from brain.openrouter import OpenRouterBrain
from config import Settings, get_settings
from enums import LlmProvider

BRAINS = {
    LlmProvider.BEDROCK: BedrockBrain,
    LlmProvider.OPENROUTER: OpenRouterBrain,
    LlmProvider.MOCK: MockBrain,
}


def create_brain(settings: Settings | None = None) -> Brain:
    config = settings or get_settings()
    return BRAINS[config.llm.provider](config)
