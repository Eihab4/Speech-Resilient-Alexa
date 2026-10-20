import re
from datetime import datetime

from config.settings import SosSettings
from enums import AlertKind, AlertStatus, NextMove
from location import Geocoder
from memory import Alert, MemoryStore, Profile, Turn
from messages import MAP_URL, SOS_PHRASES, STOP_WORDS, AlertText, Reply
from notify import Notifier, Position, linked_helpers, names, outcome, reach
from utils import hours_ago

SOS_PATTERN = re.compile(r"\b(" + "|".join(map(re.escape, SOS_PHRASES)) + r")\b")


def plain_words(heard: str) -> str:
    """The piece as plain lowercase words, so punctuation and pauses ("i… fell") don't matter."""
    return " ".join(re.findall(r"[a-z']+", heard.lower().replace("’", "'")))


def asks_for_sos(heard: str) -> bool:
    words = plain_words(heard)
    return bool(SOS_PATTERN.search(words)) or words.split().count("help") >= 2


def says_stop(heard: str) -> bool:
    return plain_words(heard) in STOP_WORDS


def emergency_sos(
    store: MemoryStore,
    notifier: Notifier,
    geocoder: Geocoder,
    settings: SosSettings,
    company_id: str,
    user_id: str,
    latitude: float | None = None,
    longitude: float | None = None,
) -> dict:
    conversation = store.conversation_for(company_id, user_id)
    recent = store.last_sent_alert(company_id, user_id, AlertKind.SOS)
    if recent and recent.created_at >= hours_ago(settings.cooldown_minutes / 60):
        return _finish(store, conversation, Reply.SOS_ALREADY_SENT, sent_to=[])

    position = None if latitude is None or longitude is None else Position(latitude=latitude, longitude=longitude)
    heard = " … ".join(_countdown_pieces(store, conversation))
    address = geocoder.address(position) if position else None
    text = alert_text(store.profile(company_id, user_id) or Profile(name=user_id), heard, position, address)
    helpers = linked_helpers(store, company_id, user_id)
    sent_to = reach(notifier, helpers, text, position)
    status = outcome(helpers, sent_to)
    if status == AlertStatus.NO_HELPER:
        say = Reply.SOS_NO_HELPER
    elif status == AlertStatus.FAILED:
        say = Reply.SOS_FAILED
    else:
        say = (Reply.SOS_SENT if position else Reply.SOS_SENT_NO_PLACE).format(who=names(sent_to))

    alert = Alert(
        kind=AlertKind.SOS,
        heard=heard,
        latitude=latitude,
        longitude=longitude,
        address=address,
        text=text,
        status=status,
    )
    store.add_alert(company_id, user_id, alert)
    return _finish(store, conversation, say, sent_to)


def alert_text(profile: Profile, heard: str, position: Position | None, address: str | None = None) -> str:
    if position:
        url = MAP_URL.format(latitude=position.latitude, longitude=position.longitude)
        where = [AlertText.ADDRESS.format(address=address) if address else "", AlertText.MAP.format(url=url)]
    elif profile.home_address:
        where = [AlertText.HOME.format(address=profile.home_address)]
    else:
        where = [AlertText.NO_PLACE]
    said = AlertText.SAID.format(heard=heard) if heard else ""
    time = AlertText.TIME.format(time=datetime.now().astimezone().strftime("%H:%M"))
    return "\n".join(filter(None, [AlertText.HEADER.format(name=profile.name), said, *where, time]))


def _countdown_pieces(store: MemoryStore, conversation: int) -> list[str]:
    """What the person said since the countdown started, the words that started it first."""
    pieces = []
    for turn in reversed(store.turns(conversation)):
        if turn.next_move != NextMove.SOS:
            break
        pieces.append(turn.heard)
    return pieces[::-1]


def _finish(store: MemoryStore, conversation: int, say: str, sent_to: list[str]) -> dict:
    # Ends the countdown, so the next piece is heard as usual.
    store.add_turn(conversation, Turn(heard="", say=say, next_move=NextMove.LISTEN))
    return {"sent": bool(sent_to), "sent_to": sent_to, "say": say}
