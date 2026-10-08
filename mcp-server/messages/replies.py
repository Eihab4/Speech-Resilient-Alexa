from enum import StrEnum

from enums import Intent


class Reply(StrEnum):
    STILL_LISTENING = "Take your time. I'm still listening."
    CONFIRMED = "Okay."
    WHAT_TO_CHANGE = "Okay, what should I change?"
    NEEDS_YES = "I need a yes first."
    NOTHING_PENDING = "There's nothing waiting right now."
    CANCELLED = "Okay, cancelled."
    DONE = "Done. {result}"


ACTION_RESULTS = {
    Intent.REMINDER: "Reminder set: {what}, {when}.",
    Intent.MESSAGE: "Message sent to {who}: {text}.",
    Intent.CALL: "Calling {who}.",
}
GENERIC_ACTION_RESULT = "Request completed."
