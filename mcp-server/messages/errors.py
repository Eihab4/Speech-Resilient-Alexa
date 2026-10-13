from enum import StrEnum


class ErrorMessage(StrEnum):
    LLM_KEY_MISSING = "{variable} is required for {provider}"
    LLM_REQUEST_FAILED = "{provider} request failed: {detail}"
    LLM_UNREACHABLE = "Could not reach {provider}"
