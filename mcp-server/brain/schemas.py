from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from enums import Intent, NextMove


class BrainResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    changed: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    # The latest piece starts a different request instead of continuing or correcting the open one.
    new_request: bool = False
    next_move: NextMove
    say: str
