from enums import NextMove
from memory.models import Turn
from messages import CANCELLED_NOTE

# How a request's last turn looks when it ended on its own. Any other last move means it was dropped midway.
ENDING_MOVES = {NextMove.DONE, NextMove.CANCEL}


def render_turns(summary: str, turns: list[Turn]) -> str:
    """The turns of finished requests, with a note after each request that was cancelled before it was done."""
    lines = []
    for index, turn in enumerate(turns):
        lines.append(f"person: {turn.heard}\nalexa: {turn.say}")
        ends_request = index == len(turns) - 1 or turns[index + 1].request_id != turn.request_id
        if ends_request and turn.next_move not in ENDING_MOVES:
            lines.append(CANCELLED_NOTE)
    return "\n".join(filter(None, [summary, *lines]))
