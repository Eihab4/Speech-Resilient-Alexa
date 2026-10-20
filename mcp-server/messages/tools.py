from enum import StrEnum


class ToolDescription(StrEnum):
    UNDERSTAND_SPEECH = (
        "Call this on every turn while a person is making a request, with their exact words, even if they are "
        "incomplete, out of order or a correction. It remembers earlier pieces and returns what was understood, "
        "the next move (listen, ask, confirm, cancel, done or sos) and the sentence to say. "
        "sos means an emergency: wait countdown_seconds, sending anything the person says to this tool as usual, "
        "then call emergency_sos unless a reply other than sos came back first (the person said stop). "
        "Every reply has wait_seconds: how long this person pauses mid-sentence, learned from them. Wait that "
        "long after they stop before calling again, join what they said meanwhile into one heard, and pass the "
        "pauses you measured inside it as pauses_ms, so the wait keeps fitting them."
    )
    DO_CONFIRMED_REQUEST = (
        "Carry out a request after the person clearly said yes. Only works when understand_speech returned "
        "next_move done for this pending_id."
    )
    CANCEL_REQUEST = "Drop the request in progress when the person says to stop or never mind."
    RESUME_UNFINISHED = (
        "Call this once when a session starts. Returns a request the person left unfinished last time, "
        "so you can offer to pick it up instead of making them start over."
    )
    EMERGENCY_SOS = (
        "Send the person's helpers an emergency alert right away, with no yes. Call it when the countdown "
        "that understand_speech asked for (next_move sos) ends without the person saying stop. "
        "Pass the device's latitude and longitude if you have them."
    )
