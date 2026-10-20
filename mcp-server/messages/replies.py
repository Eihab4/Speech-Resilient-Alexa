from enum import StrEnum

from enums import Intent


class Reply(StrEnum):
    STILL_LISTENING = "Take your time. I'm still listening."
    CONFIRMED = "Okay."
    WHAT_TO_CHANGE = "Okay, what should I change?"
    NEEDS_YES = "I need a yes first."
    NOTHING_PENDING = "There's nothing waiting right now."
    CANCELLED = "Okay, cancelled."
    BACK_TO_IT = "Okay, let's finish this one first. {question}"
    DONE = "Done. {result}"
    RESUME = "You didn't finish your {intent} last time. Want to pick it up?"
    GENERIC_INTENT = "request"
    SOS_COUNTDOWN = "I'll send an emergency alert in {seconds} seconds. Say stop if you're okay."
    SOS_KEEP_CALM = "Help is coming in a moment. Say stop if you're okay."
    SOS_STOPPED = "Okay, I won't send it. I'm here if you need me."
    SOS_STOPPED_BACK = "Okay, I won't send it. {question}"
    TREND_EMPTY = "We haven't finished a request together yet."
    TREND_ONE_DAY = "I needed {tries} questions per request today."
    TREND = "On {first_day} I needed {first_tries} questions per request. Now it's {last_tries}."
    SOS_SENT = "I sent {who} an alert with where you are. I'm staying with you."
    SOS_SENT_NO_PLACE = "I sent {who} an alert. I'm staying with you."
    SOS_ALREADY_SENT = "I already sent the alert a moment ago. I'm staying with you."
    SOS_NO_HELPER = "I can't reach anyone, because no helper is set up yet. Please call the emergency number."
    SOS_FAILED = "I couldn't send the alert. Please call the emergency number."
    AND = "and"


ACTION_RESULTS = {
    Intent.REMINDER: "Reminder set: {what}, {when}.",
    Intent.MESSAGE: "Message sent to {who}: {text}.",
    Intent.CALL: "Calling {who}.",
}
GENERIC_ACTION_RESULT = "Request completed."
