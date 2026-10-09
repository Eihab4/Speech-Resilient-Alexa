from memory import MemoryStore
from messages import Reply


def resume_unfinished(store: MemoryStore, company_id: str, user_id: str) -> dict:
    conversation = store.conversation_for(company_id, user_id)
    request = store.pending_request(conversation)
    if request is None:
        return {"found": False, "say": Reply.NOTHING_PENDING}

    say = Reply.RESUME.format(intent=request.intent or Reply.GENERIC_INTENT)
    return {"found": True, "pending_id": request.id, "intent": request.intent, "details": request.details, "say": say}
