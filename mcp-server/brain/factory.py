from brain.base import Brain
from brain.bedrock import BedrockBrain
from brain.openrouter import OpenRouterBrain
from config import Settings, get_settings


def create_brain(settings: Settings | None = None) -> Brain:
    config = settings or get_settings()
    if config.llm_provider == "openrouter":
        return OpenRouterBrain(config)
    return BedrockBrain(config)
