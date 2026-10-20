from enums import AlertKind, AlertStatus, NextMove
from memory import Alert, MemoryStore, Profile, Request, Turn
from messages import HELP_WORDS, HelpText, Reply
from notify import Notifier, linked_helpers, names, outcome, reach
from tools.emergency_sos import plain_words
from utils import clock_now

TRIES = (NextMove.ASK, NextMove.HELP)


def asks_for_help(heard: str) -> bool:
    return plain_words(heard) in HELP_WORDS


def ask_for_help(store: MemoryStore, notifier: Notifier, company_id: str, user_id: str) -> dict:
    conversation = store.conversation_for(company_id, user_id)
    request = store.pending_request(conversation)
    pieces = store.turns(conversation, request.id) if request else []
    profile = store.profile(company_id, user_id) or Profile(name=user_id)
    text = help_text(profile, request, pieces)
    helpers = linked_helpers(store, company_id, user_id)
    sent_to = reach(notifier, helpers, text)
    status = outcome(helpers, sent_to)
    heard = " … ".join(turn.heard for turn in pieces)
    store.add_alert(company_id, user_id, Alert(kind=AlertKind.HELP, heard=heard, text=text, status=status))
    say = _say(status, sent_to, pieces)
    store.add_turn(conversation, Turn(request_id=None, heard="", say=say, next_move=NextMove.LISTEN))
    return {"sent": bool(sent_to), "sent_to": sent_to, "say": say}


def help_text(profile: Profile, request: Request | None, pieces: list[Turn]) -> str:
    if pieces and pieces[-1].next_move == NextMove.HELP:
        header = HelpText.STUCK.format(name=profile.name, tries=sum(turn.next_move in TRIES for turn in pieces))
    else:
        header = HelpText.ASKED.format(name=profile.name)
    known = _known(request)
    understood = HelpText.UNDERSTOOD.format(known=", ".join(known)) if known else HelpText.NOTHING
    heard = " … ".join(turn.heard for turn in pieces)
    said = HelpText.SAID.format(heard=heard) if heard else ""
    return "\n".join(filter(None, [header, understood, said, HelpText.TIME.format(time=clock_now())]))


def _known(request: Request | None) -> list[str]:
    if request is None:
        return []
    details = [f"{key}: {value}" for key, value in request.details.items()]
    return [str(request.intent), *details] if request.intent else details


def _say(status: AlertStatus, sent_to: list[str], pieces: list[Turn]) -> str:
    if status == AlertStatus.NO_HELPER:
        sent = Reply.HELP_NO_HELPER
    elif status == AlertStatus.FAILED:
        sent = Reply.HELP_FAILED
    else:
        sent = (Reply.HELP_SENT if pieces else Reply.HELP_SENT_NO_REQUEST).format(who=names(sent_to))
    return f"{sent} {pieces[-1].say if pieces else Reply.HELP_HERE}"
