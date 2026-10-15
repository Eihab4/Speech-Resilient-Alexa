from threading import Thread

from brain.base import Brain
from brain.schemas import BrainResult
from enums import NextMove, RequestStatus
from memory import History, MemoryStore, Request, Turn
from messages import NO_WORDS, YES_WORDS, Reply


def understand(brain: Brain, store: MemoryStore, history: History, company_id: str, user_id: str, heard: str) -> dict:
    fragment = heard.strip()
    if not fragment:
        return BrainResult(next_move=NextMove.LISTEN, say=Reply.STILL_LISTENING).model_dump()

    conversation = store.conversation_for(company_id, user_id)
    request = store.pending_request(conversation) or Request()
    earlier = store.turns(conversation, request.id)
    awaiting_yes = bool(earlier) and earlier[-1].next_move == NextMove.CONFIRM
    set_aside = _set_aside_piece(store.last_turn(conversation)) if earlier else None
    said_yes = fragment.lower() in YES_WORDS
    said_no = fragment.lower() in NO_WORDS
    # Switch turns belong to no request, so they never reach the brain as pieces of one.
    turn_request_id = request.id

    if set_aside and said_yes:
        store.save_request(conversation, request.model_copy(update={"status": RequestStatus.CANCELLED}))
        # No history: it would show the dropped request unanswered, and the brain would ask to switch again.
        result = brain.interpret([set_aside])
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
        result = brain.interpret([turn.heard for turn in earlier] + [fragment], history.for_brain(conversation))
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
    Thread(target=history.maintain, args=(conversation,), daemon=True).start()
    return {**result.model_dump(), "pending_id": request.id}


def _set_aside_piece(last: Turn | None) -> str | None:
    """The new request Alexa just asked about switching to, if that was her last question."""
    if last and last.request_id is None and last.next_move == NextMove.SWITCH:
        return last.heard
    return None
