from enum import StrEnum


class ErrorMessage(StrEnum):
    LLM_KEY_MISSING = "{variable} is required for {provider}"
    LLM_REQUEST_FAILED = "{provider} request failed: {detail}"
    LLM_UNREACHABLE = "Could not reach {provider}"
    SPEECH_TEXT_MISSING = "text is required"
    SPEECH_UNAVAILABLE = "Amazon Polly is unavailable"
    TELEGRAM_FAILED = "Telegram {method} failed: {detail}"
    TELEGRAM_UNREACHABLE = "Could not reach Telegram for {method}"
    NAME_MISSING = "name is required"
    HELPER_NOT_FOUND = "No such helper for this person"
    USERNAME_INVALID = "A username is 3 to 30 letters, digits, dots, dashes or underscores"
    USERNAME_TAKEN = "That username is taken"
    PASSWORD_TOO_SHORT = "A password needs at least 6 characters"
    SIGN_IN_FAILED = "Wrong username or password"
    NOT_SIGNED_IN = "Sign in first"
