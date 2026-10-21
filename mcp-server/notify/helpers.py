import logging

from enums import AlertStatus
from memory import Helper, MemoryStore
from messages import LogMessage, Reply
from notify.base import Notifier, Position

logger = logging.getLogger(__name__)


def linked_helpers(store: MemoryStore, company_id: str, user_id: str) -> list[Helper]:
    return [helper for helper in store.helpers(company_id, user_id) if helper.linked]


def reach(notifier: Notifier, helpers: list[Helper], text: str, position: Position | None = None) -> list[str]:
    return [helper.name for helper in helpers if _deliver(notifier, helper, text, position)]


def outcome(helpers: list[Helper], sent_to: list[str]) -> AlertStatus:
    if not helpers:
        return AlertStatus.NO_HELPER
    return AlertStatus.SENT if sent_to else AlertStatus.FAILED


def names(sent_to: list[str]) -> str:
    return sent_to[0] if len(sent_to) == 1 else f"{', '.join(sent_to[:-1])} {Reply.AND} {sent_to[-1]}"


def _deliver(notifier: Notifier, helper: Helper, text: str, position: Position | None) -> bool:
    try:
        notifier.notify(helper, text, position)
    except Exception:
        logger.exception(LogMessage.MESSAGE_NOT_DELIVERED.format(helper=helper.name))
        return False
    return True
