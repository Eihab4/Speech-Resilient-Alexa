from messages import HELP_WORDS
from tools.emergency_sos import plain_words


def asks_for_help(heard: str) -> bool:
    return plain_words(heard) in HELP_WORDS
