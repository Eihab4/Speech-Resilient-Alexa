from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BrainResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    changed: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    next_move: Literal["listen", "ask", "confirm"]
    say: str
