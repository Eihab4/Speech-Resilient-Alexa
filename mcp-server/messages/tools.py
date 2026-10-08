from enum import StrEnum


class ToolDescription(StrEnum):
    UNDERSTAND_SPEECH = (
        "Call this on every turn while a person is making a request, with their exact words, even if they are "
        "incomplete, out of order or a correction. It remembers earlier pieces and returns what was understood, "
        "the next move (listen, ask, confirm or done) and the sentence to say."
    )
    DO_CONFIRMED_REQUEST = (
        "Carry out a request after the person clearly said yes. Only works when understand_speech returned "
        "next_move done for this pending_id."
    )
    CANCEL_REQUEST = "Drop the request in progress when the person says to stop or never mind."
