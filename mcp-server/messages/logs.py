from enum import StrEnum


class LogMessage(StrEnum):
    """Written to the server log for whoever runs it; never shown to the person. ErrorMessage is what callers see."""

    MESSAGE_NOT_DELIVERED = "Could not send the message to {helper}"
    MESSAGE_SIMULATED = "Simulated message to {helper}:\n{text}"
    TELEGRAM_UPDATES_FAILED = "Could not read the bot's messages; trying again"
    TELEGRAM_UPDATE_FAILED = "Could not handle a message sent to the bot"
    TELEGRAM_PIN_FAILED = "The alert reached {helper}, but the map pin did not"
    LOCATION_UNAVAILABLE = "Amazon Location could not find an address"
