from enum import StrEnum


class ErrorMessage(StrEnum):
    LLM_KEY_MISSING = "{variable} is required for {provider}"
    LLM_REQUEST_FAILED = "{provider} request failed: {detail}"
    LLM_UNREACHABLE = "Could not reach {provider}"
    SPEECH_TEXT_MISSING = "text is required"
    SPEECH_UNAVAILABLE = "Amazon Polly is unavailable"
    ALERT_NOT_DELIVERED = "Could not send the emergency alert to {helper}"
    ALERT_SIMULATED = "Simulated emergency alert to {helper}:\n{text}"
    TELEGRAM_FAILED = "Telegram {method} failed: {detail}"
    TELEGRAM_UNREACHABLE = "Could not reach Telegram for {method}"
    TELEGRAM_UPDATES_FAILED = "Could not read the bot's messages; trying again"
    TELEGRAM_UPDATE_FAILED = "Could not handle a message sent to the bot"
    TELEGRAM_PIN_FAILED = "The alert reached {helper}, but the map pin did not"
    LOCATION_UNAVAILABLE = "Amazon Location could not find an address"
    NAME_MISSING = "name is required"
    HELPER_NOT_FOUND = "No such helper for this person"
    USERNAME_INVALID = "A username is 3 to 30 letters, digits, dots, dashes or underscores"
    USERNAME_TAKEN = "That username is taken"
    PASSWORD_TOO_SHORT = "A password needs at least 6 characters"
    SIGN_IN_FAILED = "Wrong username or password"
    NOT_SIGNED_IN = "Sign in first"
