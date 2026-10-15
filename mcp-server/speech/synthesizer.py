from typing import Protocol


class SpeechUnavailable(Exception):
    pass


class Synthesizer(Protocol):
    @property
    def media_type(self) -> str: ...

    def synthesize(self, text: str) -> bytes: ...
