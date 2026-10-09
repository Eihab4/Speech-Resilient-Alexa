from actions import perform
from enums import RequestStatus
from memory import MemoryStore
from messages import Reply


def do_confirmed_request(store: MemoryStore, company_id: str, user_id: str, pending_id: str) -> dict:
    conversation = store.conversation_for(company_id, user_id)
    request = store.request(conversation, pending_id)
    if request is None:
        return {"done": False, "say": Reply.NOTHING_PENDING}
    if request.status != RequestStatus.CONFIRMED:
        return {"done": False, "say": Reply.NEEDS_YES}

    result = perform(request)
    store.log_action(request.id, result)
    store.save_request(conversation, request.model_copy(update={"status": RequestStatus.DONE}))
    return {"done": True, "say": Reply.DONE.format(result=result)}
