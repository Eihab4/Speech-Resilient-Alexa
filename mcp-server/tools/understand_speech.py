from brain.base import Brain
from brain.schemas import BrainResult


def understand(brain: Brain, user_id: str, heard: str) -> dict:
    fragment = heard.strip()
    if not fragment:
        return BrainResult(next_move="listen", say="Take your time. I'm still listening.").model_dump()

    return brain.interpret([fragment]).model_dump()
