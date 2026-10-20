from dataclasses import dataclass

from brain.base import Brain
from brain.schemas import BrainResult
from enums import AskMode, NextMove, RequestStatus
from memory import History, MemoryStore, Request, Turn
from messages import NO_WORDS, YES_WORDS, Reply
from pacing import Pacing
from tools.ask_for_help import asks_for_help
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
        tries=sum(turn.next_move == NextMove.ASK for turn in earlier),
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
    store.save_request(conversation, step.request)
    turn = Turn(request_id=step.request_id, heard=step.heard, say=step.result.say, next_move=step.result.next_move)
    store.add_turn(conversation, turn)
    history.maintain_later(conversation)
    # Alexa said "go on" and the person went on with the same request: she answered before they had finished.
    answered_too_early = (
        now.last is not None and now.last.next_move == NextMove.LISTEN and now.last.request_id == step.request_id
    )
    wait = pacing.learn(company_id, user_id, pauses_ms or [], answered_too_early)
    tries = now.tries + (step.result.next_move == NextMove.ASK)
    return {**step.result.model_dump(), "pending_id": step.request.id, "wait_seconds": wait, "tries": tries}


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
    said_yes = now.fragment.lower() in YES_WORDS
    said_no = now.fragment.lower() in NO_WORDS
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
    if result.new_request and now.request.intent:
        # The switch turn belongs to no request, so it never reaches the brain as a piece of the open one.
        switch = BrainResult(
            intent=now.request.intent,
            details=now.request.details,
            new_request=True,
            next_move=NextMove.SWITCH,
            say=result.say,
        )
        return Step(request=now.request, result=switch, request_id=None, heard=now.fragment)
    if result.next_move == NextMove.CANCEL:
        return Step(request=now.request, result=result, request_id=now.request.id, heard=now.fragment)
    request = now.request.model_copy(update={"intent": result.intent, "details": result.details})
    return Step(request=request, result=result, request_id=request.id, heard=now.fragment)


def _set_aside_piece(last: Turn | None) -> str | None:
    """The new request Alexa just asked about switching to, if that was her last question."""
    if last and last.request_id is None and last.next_move == NextMove.SWITCH:
        return last.heard
    return None
