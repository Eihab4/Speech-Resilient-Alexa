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

    if awaiting_yes and fragment.lower() in YES_WORDS:
        request = request.model_copy(update={"status": RequestStatus.CONFIRMED})
        result = BrainResult(
            intent=request.intent, details=request.details, next_move=NextMove.DONE, say=Reply.CONFIRMED
        )
    elif awaiting_yes and fragment.lower() in NO_WORDS:
        result = BrainResult(
            intent=request.intent, details=request.details, next_move=NextMove.ASK, say=Reply.WHAT_TO_CHANGE
        )
    else:
        result = brain.interpret([turn.heard for turn in earlier] + [fragment], history.for_brain(conversation))
        request = request.model_copy(update={"intent": result.intent, "details": result.details})

    store.save_request(conversation, request)
    store.add_turn(
        conversation, Turn(request_id=request.id, heard=fragment, say=result.say, next_move=result.next_move)
    )
    Thread(target=history.maintain, args=(conversation,), daemon=True).start()
    return {**result.model_dump(), "pending_id": request.id}
