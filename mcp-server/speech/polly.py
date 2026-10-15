import boto3
from botocore.exceptions import BotoCoreError, ClientError

from config.settings import PollySettings
from speech.synthesizer import SpeechUnavailable


class PollySynthesizer:
    def __init__(self, settings: PollySettings, client=None) -> None:
        self._settings = settings
        self._client = client or boto3.client("polly", region_name=settings.region)

    @property
    def media_type(self) -> str:
        return self._settings.output_format.media_type

    def synthesize(self, text: str) -> bytes:
        try:
            response = self._client.synthesize_speech(
                Text=text,
                VoiceId=self._settings.voice_id,
                Engine=self._settings.engine,
                OutputFormat=self._settings.output_format,
            )
        except (BotoCoreError, ClientError) as error:
            raise SpeechUnavailable(str(error)) from error
        return response["AudioStream"].read()
