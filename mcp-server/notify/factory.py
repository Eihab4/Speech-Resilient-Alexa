from config import Settings
from notify.base import Notifier
from notify.simulated import SimulatedNotifier
from notify.telegram import TelegramBot, TelegramNotifier


def create_bot(settings: Settings) -> TelegramBot | None:
    return TelegramBot(settings.telegram) if settings.telegram.enabled else None


def create_notifier(bot: TelegramBot | None) -> Notifier:
    """Telegram when a bot token is set, the server log otherwise."""
    return TelegramNotifier(bot) if bot else SimulatedNotifier()
