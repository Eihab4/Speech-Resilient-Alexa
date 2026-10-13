from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from enums import NextMove


class BrainResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    changed: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    next_move: NextMove
    say: str
