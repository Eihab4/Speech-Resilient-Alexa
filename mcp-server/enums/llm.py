from enum import StrEnum


class LlmProvider(StrEnum):
    BEDROCK = "bedrock"
    OPENROUTER = "openrouter"


class ChatRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
