from memory.models import Turn
from messages import REQUEST_ENDINGS


def render_turns(summary: str, turns: list[Turn]) -> str:
    lines = []
    for index, turn in enumerate(turns):
        lines.append(f"person: {turn.heard}\nalexa: {turn.say}")
        last_of_request = index == len(turns) - 1 or turns[index + 1].request_id != turn.request_id
        if last_of_request and turn.request_status in REQUEST_ENDINGS:
            lines.append(REQUEST_ENDINGS[turn.request_status])
    return "\n".join(filter(None, [summary, *lines]))
