from dataclasses import dataclass

from brain.base import Brain
from brain.schemas import BrainResult
from enums import AskMode, Intent, NextMove, RequestStatus
from memory import History, MemoryStore, Request, Turn
from messages import NO_WORDS, PUNCTUATION_TO_SPACE, REPEATED_YES_WORDS, RESPONSE_FILLERS, YES_WORDS, Reply
from pacing import Pacing
from tools.ask_for_help import TRIES, asks_for_help
from tools.emergency_sos import asks_for_sos, says_stop


@dataclass
class Moment:
    """What one turn starts from, read once from memory."""

    brain: Brain
    store: MemoryStore
    history: History
    conversation: int
    fragment: str
    last: Turn | None  # the conversation's last turn, of any request
    request: Request  # the open request, or a new empty one
    earlier: list[Turn]  # the open request's pieces so far
    person: str  # the name the person signed in with, for the brain to use
    tries: int  # how many times Alexa has already asked about this request
    question: str  # what Alexa last said about this request, so "mom" or "yes" can be read as an answer
    mode: AskMode  # yes_no once asking has failed a few times: the brain guesses and asks "Mom?"

    def ask_brain(self, pieces: list[str]) -> BrainResult:
        return self.brain.interpret(
            pieces, self.history.for_brain(self.conversation), self.person, self.question, self.mode
        )


@dataclass
class Step:
    """What the turn decided: the request as it now stands, Alexa's answer, and which request the turn belongs to."""

    request: Request
    result: BrainResult
    request_id: str | None  # None for turns that belong to no request, like the switch question
    heard: str


def understand(
    brain: Brain,
    store: MemoryStore,
    history: History,
    company_id: str,
    user_id: str,
    heard: str,
    countdown_seconds: int,
    pacing: Pacing,
    pauses_ms: list[int] | None = None,
    yes_no_after_tries: int = 3,
    help_after_tries: int = 5,
) -> dict:
    """pauses_ms: the pauses the host measured inside this piece, between the bits it joined together."""
    fragment = heard.strip()
    if not fragment:
        return BrainResult(next_move=NextMove.LISTEN, say=Reply.STILL_LISTENING).model_dump()

    conversation = store.conversation_for(company_id, user_id)
    request = store.pending_request(conversation) or Request()
    profile = store.profile(company_id, user_id)
    earlier = store.turns(conversation, request.id)
    now = Moment(
        brain=brain,
        store=store,
        history=history,
        conversation=conversation,
        fragment=fragment,
        last=store.last_turn(conversation),
        request=request,
        earlier=earlier,
        person=profile.name if profile else "",
        tries=sum(turn.next_move in TRIES for turn in earlier),
        question=earlier[-1].say if earlier else "",
        mode=AskMode.OPEN,
    )
    now.mode = AskMode.YES_NO if now.tries >= yes_no_after_tries else AskMode.OPEN

    # Checked before the brain, so an emergency is caught even when the LLM is down or slow.
    if (emergency := _emergency(now, countdown_seconds)) is not None:
        return {**emergency, "wait_seconds": pacing.wait(company_id, user_id)}
    if asks_for_help(fragment):
        return {**_ask_for_help(now), "wait_seconds": pacing.wait(company_id, user_id)}

    step = _decide(now)
    gives_up = step.result.next_move == NextMove.ASK and now.tries + 1 == help_after_tries
    move = NextMove.HELP if gives_up else step.result.next_move
    store.save_request(conversation, step.request)
    store.add_turn(
        conversation, Turn(request_id=step.request_id, heard=step.heard, say=step.result.say, next_move=move)
    )
    history.maintain_later(conversation)
    # Alexa said "go on" and the person went on with the same request: she answered before they had finished.
    answered_too_early = (
        now.last is not None and now.last.next_move == NextMove.LISTEN and now.last.request_id == step.request_id
    )
    wait = pacing.learn(company_id, user_id, pauses_ms or [], answered_too_early)
    tries = now.tries + (move in TRIES)
    reply = {**step.result.model_dump(), "next_move": move, "say": Reply.HELP_STUCK if gives_up else step.result.say}
    return {**reply, "pending_id": step.request.id, "wait_seconds": wait, "tries": tries}


def _emergency(now: Moment, countdown_seconds: int) -> dict | None:
    """SOS words start the countdown; while it runs, stop words end it and anything else keeps it going."""
    counting = now.last is not None and now.last.next_move == NextMove.SOS
    if counting and says_stop(now.fragment):
        return _stop_countdown(now)
    if not (counting or asks_for_sos(now.fragment)):
        return None
    say = Reply.SOS_KEEP_CALM if counting else Reply.SOS_COUNTDOWN.format(seconds=countdown_seconds)
    now.store.add_turn(now.conversation, Turn(request_id=None, heard=now.fragment, say=say, next_move=NextMove.SOS))
    result = BrainResult(next_move=NextMove.SOS, say=say)
    return {**result.model_dump(), "pending_id": None, "countdown_seconds": countdown_seconds}


def _ask_for_help(now: Moment) -> dict:
    turn = Turn(request_id=None, heard=now.fragment, say=Reply.HELP_ASKED, next_move=NextMove.HELP)
    now.store.add_turn(now.conversation, turn)
    result = BrainResult(intent=now.request.intent, details=now.request.details, next_move=NextMove.HELP, say=turn.say)
    return {**result.model_dump(), "pending_id": now.request.id if now.earlier else None}


def _stop_countdown(now: Moment) -> dict:
    """No alert. The open request, if any, picks up where it was, like after saying no to a switch."""
    if now.earlier:
        move, say = now.earlier[-1].next_move, Reply.SOS_STOPPED_BACK.format(question=now.earlier[-1].say)
    else:
        move, say = NextMove.LISTEN, Reply.SOS_STOPPED
    now.store.add_turn(now.conversation, Turn(request_id=None, heard=now.fragment, say=say, next_move=move))
    result = BrainResult(intent=now.request.intent, details=now.request.details, next_move=move, say=say)
    return {**result.model_dump(), "pending_id": now.request.id if now.earlier else None}


def _decide(now: Moment) -> Step:
    """A yes or a no to Alexa's last question is handled here; everything else goes to the brain."""
    words = " ".join(now.fragment.lower().translate(PUNCTUATION_TO_SPACE).split())
    response = _without_fillers(words)
    said_yes = response in YES_WORDS or _is_repeated_yes(response)
    said_no = response in NO_WORDS
    set_aside = _set_aside_piece(now.last) if now.earlier else None
    awaiting_yes = bool(now.earlier) and now.earlier[-1].next_move == NextMove.CONFIRM

    if set_aside and said_yes:
        return _switch_to(now, set_aside)
    if set_aside and said_no:
        return _back_to_open_request(now)
    if awaiting_yes and said_yes:
        return _confirm(now)
    if awaiting_yes and said_no:
        return _ask_what_to_change(now)
    return _interpret(now)


def _is_repeated_yes(words: str) -> bool:
    """Accept speech recognition repeating a short affirmative (for example, "yes, yes")."""
    pieces = words.split()
    return len(pieces) > 1 and all(piece in REPEATED_YES_WORDS for piece in pieces)


def _without_fillers(words: str) -> str:
    pieces = words.split()
    while pieces and pieces[0] in RESPONSE_FILLERS:
        pieces.pop(0)
    while pieces and pieces[-1] in RESPONSE_FILLERS:
        pieces.pop()
    return " ".join(pieces)


def _switch_to(now: Moment, piece: str) -> Step:
    """Yes to switching: the open request is replaced, and the set-aside piece starts the new one."""
    now.store.save_request(now.conversation, now.request.model_copy(update={"status": RequestStatus.REPLACED}))
    result = now.ask_brain([piece])
    request = Request(intent=result.intent, details=result.details)
    return Step(request=request, result=result, request_id=request.id, heard=piece)


def _back_to_open_request(now: Moment) -> Step:
    """No to switching: keep the open request and ask its last question again."""
    question = now.earlier[-1]
    result = BrainResult(
        intent=now.request.intent,
        details=now.request.details,
        next_move=question.next_move,
        say=Reply.BACK_TO_IT.format(question=question.say),
    )
    return Step(request=now.request, result=result, request_id=None, heard=now.fragment)


def _confirm(now: Moment) -> Step:
    request = now.request.model_copy(update={"status": RequestStatus.CONFIRMED})
    result = BrainResult(intent=request.intent, details=request.details, next_move=NextMove.DONE, say=Reply.CONFIRMED)
    return Step(request=request, result=result, request_id=request.id, heard=now.fragment)


def _ask_what_to_change(now: Moment) -> Step:
    result = BrainResult(
        intent=now.request.intent, details=now.request.details, next_move=NextMove.ASK, say=Reply.WHAT_TO_CHANGE
    )
    return Step(request=now.request, result=result, request_id=now.request.id, heard=now.fragment)


def _interpret(now: Moment) -> Step:
    """The brain reads every piece so far. If it hears a new request while one is open, Alexa asks before switching."""
    result = now.ask_brain([turn.heard for turn in now.earlier] + [now.fragment])
    # Only _confirm may mark a request done. A model can mistake a hesitant or ambiguous reply for "yes".
    if result.next_move == NextMove.DONE:
        result = result.model_copy(
            update={"next_move": NextMove.CONFIRM, "say": _confirmation_question(result.intent, result.details)}
        )

    changed_intent = now.request.intent is not None and result.intent is not None and result.intent != now.request.intent
    if now.request.intent and (result.new_request or changed_intent):
        say = result.say.strip()
        if changed_intent:
            say = _switch_question(now.request.intent, now.request.details, result.intent, result.details)
        elif not say:
            say = Reply.SWITCH_GENERIC
        # The switch turn belongs to no request, so it never reaches the brain as a piece of the open one.
        switch = BrainResult(
            intent=now.request.intent,
            details=now.request.details,
            new_request=True,
            next_move=NextMove.SWITCH,
            say=say,
        )
        return Step(request=now.request, result=switch, request_id=None, heard=now.fragment)
    if result.next_move == NextMove.CANCEL:
        return Step(request=now.request, result=result, request_id=now.request.id, heard=now.fragment)
    request = now.request.model_copy(update={"intent": result.intent, "details": result.details})
    if not result.say.strip():
        say = _empty_reply(result.next_move, request.intent, request.details)
        result = result.model_copy(update={"say": say})
    return Step(request=request, result=result, request_id=request.id, heard=now.fragment)


def _request_action(intent: Intent | None, details: dict, *, current: bool = False) -> str:
    if intent == Intent.REMINDER:
        what = str(details.get("what", "a reminder"))
        when = str(details.get("when", ""))
        if current:
            return f"the reminder for {what}" + (f" {when}" if when else "")
        return f"set a reminder for {what}" + (f" {when}" if when else "")
    if intent == Intent.CALL:
        who = str(details.get("who", "someone"))
        return f"the call to {who}" if current else f"call {who}"
    if intent == Intent.MESSAGE:
        who = str(details.get("who", "someone"))
        return f"the message to {who}" if current else f"send a message to {who}"
    return "this request" if current else "the new request"


def _switch_question(old_intent: Intent, old_details: dict, new_intent: Intent, new_details: dict) -> str:
    return Reply.SWITCH_REQUEST.format(
        current=_request_action(old_intent, old_details, current=True),
        new=_request_action(new_intent, new_details),
    )


def _confirmation_question(intent: Intent | None, details: dict) -> str:
    if intent is None:
        return Reply.CONFIRM_GENERIC
    return Reply.CONFIRM_REQUEST.format(request=_request_action(intent, details))


def _empty_reply(move: NextMove, intent: Intent | None, details: dict) -> str:
    if move == NextMove.LISTEN:
        return Reply.STILL_LISTENING
    if move == NextMove.ASK:
        return Reply.SAY_MORE
    if move == NextMove.CONFIRM:
        return _confirmation_question(intent, details)
    if move == NextMove.CANCEL:
        return Reply.CANCELLED
    if move == NextMove.HELP:
        return Reply.HELP_ASKED
    return Reply.CONFIRM_GENERIC


def _set_aside_piece(last: Turn | None) -> str | None:
    """The new request Alexa just asked about switching to, if that was her last question."""
    if last and last.request_id is None and last.next_move == NextMove.SWITCH:
        return last.heard
    return None
