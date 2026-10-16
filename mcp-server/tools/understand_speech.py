from brain.base import Brain
from brain.schemas import BrainResult
from enums import NextMove, RequestStatus
from memory import History, MemoryStore, Request, Turn
from messages import NO_WORDS, YES_WORDS, Reply
from tools.emergency_sos import asks_for_sos, says_stop


def understand(
    brain: Brain,
    store: MemoryStore,
    history: History,
    company_id: str,
    user_id: str,
    heard: str,
    countdown_seconds: int,
) -> dict:
    fragment = heard.strip()
    if not fragment:
        return BrainResult(next_move=NextMove.LISTEN, say=Reply.STILL_LISTENING).model_dump()

    conversation = store.conversation_for(company_id, user_id)
    last = store.last_turn(conversation)
    request = store.pending_request(conversation) or Request()
    earlier = store.turns(conversation, request.id)

    # Checked before the brain, so an emergency is caught even when the LLM is down or slow.
    counting = last is not None and last.next_move == NextMove.SOS
    if counting and says_stop(fragment):
        return _stop_countdown(store, conversation, request, earlier, fragment)
    if counting or asks_for_sos(fragment):
        say = Reply.SOS_KEEP_CALM if counting else Reply.SOS_COUNTDOWN.format(seconds=countdown_seconds)
        store.add_turn(conversation, Turn(request_id=None, heard=fragment, say=say, next_move=NextMove.SOS))
        result = BrainResult(next_move=NextMove.SOS, say=say)
        return {**result.model_dump(), "pending_id": None, "countdown_seconds": countdown_seconds}

    awaiting_yes = bool(earlier) and earlier[-1].next_move == NextMove.CONFIRM
    set_aside = _set_aside_piece(last) if earlier else None
    # The brain may call the person by name; it comes from the name they signed in with.
    profile = store.profile(company_id, user_id)
    person = profile.name if profile else ""
    said_yes = fragment.lower() in YES_WORDS
    said_no = fragment.lower() in NO_WORDS
    # Switch turns belong to no request, so they never reach the brain as pieces of one.
    turn_request_id = request.id

    if set_aside and said_yes:
        store.save_request(conversation, request.model_copy(update={"status": RequestStatus.REPLACED}))
        result = brain.interpret([set_aside], history.for_brain(conversation), person)
        request = Request(intent=result.intent, details=result.details)
        turn_request_id, fragment = request.id, set_aside
    elif set_aside and said_no:
        result = BrainResult(
            intent=request.intent,
            details=request.details,
            next_move=earlier[-1].next_move,
            say=Reply.BACK_TO_IT.format(question=earlier[-1].say),
        )
        turn_request_id = None
    elif awaiting_yes and said_yes:
        request = request.model_copy(update={"status": RequestStatus.CONFIRMED})
        result = BrainResult(
            intent=request.intent, details=request.details, next_move=NextMove.DONE, say=Reply.CONFIRMED
        )
    elif awaiting_yes and said_no:
        result = BrainResult(
            intent=request.intent, details=request.details, next_move=NextMove.ASK, say=Reply.WHAT_TO_CHANGE
        )
    else:
        pieces = [turn.heard for turn in earlier] + [fragment]
        result = brain.interpret(pieces, history.for_brain(conversation), person)
        if result.new_request and request.intent:
            result = BrainResult(
                intent=request.intent,
                details=request.details,
                new_request=True,
                next_move=NextMove.SWITCH,
                say=result.say,
            )
            turn_request_id = None
        else:
            request = request.model_copy(update={"intent": result.intent, "details": result.details})

    store.save_request(conversation, request)
    store.add_turn(
        conversation, Turn(request_id=turn_request_id, heard=fragment, say=result.say, next_move=result.next_move)
    )
    history.maintain_later(conversation)
    return {**result.model_dump(), "pending_id": request.id}


def _stop_countdown(
    store: MemoryStore, conversation: int, request: Request, earlier: list[Turn], fragment: str
) -> dict:
    """No alert. The open request, if any, picks up where it was, like after saying no to a switch."""
    if earlier:
        move, say = earlier[-1].next_move, Reply.SOS_STOPPED_BACK.format(question=earlier[-1].say)
    else:
        move, say = NextMove.LISTEN, Reply.SOS_STOPPED
    store.add_turn(conversation, Turn(request_id=None, heard=fragment, say=say, next_move=move))
    result = BrainResult(intent=request.intent, details=request.details, next_move=move, say=say)
    return {**result.model_dump(), "pending_id": request.id if earlier else None}


def _set_aside_piece(last: Turn | None) -> str | None:
    """The new request Alexa just asked about switching to, if that was her last question."""
    if last and last.request_id is None and last.next_move == NextMove.SWITCH:
        return last.heard
    return None
