from memory.models import Turn


def render_turns(summary: str, turns: list[Turn]) -> str:
    lines = [f"person: {turn.heard}\nalexa: {turn.say}" for turn in turns]
    return "\n".join(filter(None, [summary, *lines]))
