from enums import RequestStatus
from memory import MemoryStore
from messages import Reply


def cancel_request(store: MemoryStore, company_id: str, user_id: str) -> dict:
    conversation = store.conversation_for(company_id, user_id)
    request = store.pending_request(conversation)
    if request is None:
        return {"cancelled": False, "say": Reply.NOTHING_PENDING}

    store.save_request(conversation, request.model_copy(update={"status": RequestStatus.CANCELLED}))
    return {"cancelled": True, "say": Reply.CANCELLED}
