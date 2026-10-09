from typing import Protocol

from pydantic import BaseModel


class LlmClient(Protocol):
    def complete(self, system: str, user: str, schema: type[BaseModel] | None = None) -> str: ...
