from brain.base import Brain
from brain.schemas import BrainResult
from enums import NextMove
from memory import MemoryStore, Request, Turn
from messages import Reply


def understand(brain: Brain, store: MemoryStore, company_id: str, user_id: str, heard: str) -> dict:
    fragment = heard.strip()
    if not fragment:
        return BrainResult(next_move=NextMove.LISTEN, say=Reply.STILL_LISTENING).model_dump()

    conversation = store.conversation_for(company_id, user_id)
    request = store.pending_request(conversation) or Request()
    pieces = [turn.heard for turn in store.turns(conversation, request.id)] + [fragment]
    result = brain.interpret(pieces)

    store.save_request(conversation, request.model_copy(update={"intent": result.intent, "details": result.details}))
    store.add_turn(
        conversation, Turn(request_id=request.id, heard=fragment, say=result.say, next_move=result.next_move)
    )
    return result.model_dump()
