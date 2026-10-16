from config import Settings
from notify.base import Notifier
from notify.simulated import SimulatedNotifier


def create_notifier(settings: Settings) -> Notifier:
    return SimulatedNotifier()
