from enum import StrEnum


class PollyEngine(StrEnum):
    STANDARD = "standard"
    NEURAL = "neural"
    LONG_FORM = "long-form"
    GENERATIVE = "generative"


class AudioFormat(StrEnum):
    MP3 = "mp3"
    OGG_VORBIS = "ogg_vorbis"

    @property
    def media_type(self) -> str:
        return MEDIA_TYPES[self]


MEDIA_TYPES = {AudioFormat.MP3: "audio/mpeg", AudioFormat.OGG_VORBIS: "audio/ogg"}
