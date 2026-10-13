from enum import StrEnum


class LlmProvider(StrEnum):
    BEDROCK = "bedrock"
    OPENROUTER = "openrouter"
    MOCK = "mock"


class ChatRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
