from actions import perform
from enums import Intent, RequestStatus
from memory import MemoryStore
from messages import Reply
from reminders import ReminderEmail, ReminderEmailError


def do_confirmed_request(
    store: MemoryStore,
    company_id: str,
    user_id: str,
    pending_id: str,
    reminder_email: ReminderEmail | None = None,
) -> dict:
    conversation = store.conversation_for(company_id, user_id)
    request = store.request(conversation, pending_id)
    if request is None:
        return {"done": False, "say": Reply.NOTHING_PENDING}
    if request.status != RequestStatus.CONFIRMED:
        return {"done": False, "say": Reply.NEEDS_YES}

    if request.intent == Intent.REMINDER:
        if not reminder_email:
            # The deterministic mock brain is used in tests and scripted demos; its reminder action stays simulated.
            result = perform(request)
        else:
            profile = store.profile(company_id, user_id)
            if not profile or not profile.reminder_email or not profile.reminder_topic_arn:
                return {"done": False, "say": "Add and confirm your reminder email in People who help me first."}
            try:
                result = reminder_email.schedule(
                    company_id,
                    user_id,
                    request.id,
                    profile.reminder_topic_arn,
                    profile.reminder_email,
                    request.details,
                )
            except ReminderEmailError as error:
                return {"done": False, "say": str(error)}
    else:
        result = perform(request)
    store.log_action(request.id, result)
    store.save_request(conversation, request.model_copy(update={"status": RequestStatus.DONE}))
    return {"done": True, "say": Reply.DONE.format(result=result)}
