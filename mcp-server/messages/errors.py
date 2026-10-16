from enum import StrEnum


class ErrorMessage(StrEnum):
    LLM_KEY_MISSING = "{variable} is required for {provider}"
    LLM_REQUEST_FAILED = "{provider} request failed: {detail}"
    LLM_UNREACHABLE = "Could not reach {provider}"
    SPEECH_TEXT_MISSING = "text is required"
    SPEECH_UNAVAILABLE = "Amazon Polly is unavailable"
    ALERT_NOT_DELIVERED = "Could not send the emergency alert to {helper}"
    ALERT_SIMULATED = "Simulated emergency alert to {helper}:\n{text}"
