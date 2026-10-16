from enum import StrEnum


class AlertText(StrEnum):
    """The emergency alert a helper gets, one line per part."""

    HEADER = "🚨 SOS from {name}."
    SAID = 'They said: "{heard}".'
    ADDRESS = "Where: {address}"
    MAP = "Map: {url}"
    HOME = "The device gave no location. Home address: {address}"
    NO_PLACE = "Location unknown."
    TIME = "Sent at {time}."


MAP_URL = "https://maps.google.com/?q={latitude},{longitude}"


class TelegramText(StrEnum):
    """What the bot says to a helper who opens their link."""

    LINKED = "You're linked as {name}. Emergency alerts from Speech-Resilient Alexa will come here."
    BAD_LINK = "This link doesn't work. Ask for a new one on the Alexa page."


TELEGRAM_LINK = "https://t.me/{username}?start={code}"
