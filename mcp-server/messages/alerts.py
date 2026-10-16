from enum import StrEnum


class AlertText(StrEnum):
    """The emergency alert a helper gets, one line per part."""

    HEADER = "🚨 SOS from {name}."
    SAID = 'They said: "{heard}".'
    MAP = "Where: {url}"
    HOME = "The device gave no location. Home address: {address}"
    NO_PLACE = "Location unknown."
    TIME = "Sent at {time}."


MAP_URL = "https://maps.google.com/?q={latitude},{longitude}"
