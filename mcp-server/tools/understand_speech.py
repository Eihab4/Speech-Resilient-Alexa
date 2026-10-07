from brain.base import Brain
from brain.schemas import BrainResult
from enums import NextMove
from messages import Reply


def understand(brain: Brain, user_id: str, heard: str) -> dict:
    fragment = heard.strip()
    if not fragment:
        return BrainResult(next_move=NextMove.LISTEN, say=Reply.STILL_LISTENING).model_dump()

    return brain.interpret([fragment]).model_dump()
