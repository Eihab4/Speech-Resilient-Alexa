import logging

from memory import Helper
from messages import LogMessage
from notify.base import Position

logger = logging.getLogger(__name__)


class SimulatedNotifier:
    """Writes the message to the server log instead of sending it, until a real channel is set up."""

    def notify(self, helper: Helper, text: str, position: Position | None = None) -> None:
        logger.warning(LogMessage.MESSAGE_SIMULATED.format(helper=helper.name, text=text))
