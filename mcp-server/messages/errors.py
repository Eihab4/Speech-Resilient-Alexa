from enum import StrEnum


class ErrorMessage(StrEnum):
    OPENROUTER_KEY_MISSING = "OPENROUTER_API_KEY is required for OpenRouter"
    OPENROUTER_REQUEST_FAILED = "OpenRouter request failed: {detail}"
    OPENROUTER_UNREACHABLE = "Could not reach OpenRouter"
