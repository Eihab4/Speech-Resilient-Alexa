import io

import boto3
import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber

from config import Settings
from speech import PollySynthesizer, SpeechUnavailable


@pytest.fixture
def polly(monkeypatch):
    monkeypatch.setenv("POLLY_VOICE_ID", "Matthew")
    monkeypatch.setenv("POLLY_ENGINE", "generative")
    monkeypatch.setenv("POLLY_OUTPUT_FORMAT", "mp3")
    client = boto3.client("polly", region_name="us-east-1")
    with Stubber(client) as stub:
        yield PollySynthesizer(Settings().polly, client), stub


def test_polly_is_asked_for_the_configured_voice(polly):
    synthesizer, stub = polly
    audio = b"mp3 bytes"
    stub.add_response(
        "synthesize_speech",
        {"AudioStream": StreamingBody(io.BytesIO(audio), len(audio)), "ContentType": "audio/mpeg"},
        {"Text": "Mm-hm, go on.", "VoiceId": "Matthew", "Engine": "generative", "OutputFormat": "mp3"},
    )

    assert synthesizer.synthesize("Mm-hm, go on.") == audio
    assert synthesizer.media_type == "audio/mpeg"
    stub.assert_no_pending_responses()


def test_a_polly_failure_is_reported_as_unavailable(polly):
    synthesizer, stub = polly
    stub.add_client_error("synthesize_speech", "UnrecognizedClientException", "bad credentials")

    with pytest.raises(SpeechUnavailable, match="bad credentials"):
        synthesizer.synthesize("Done.")


@pytest.mark.skipif(not boto3.Session().get_credentials(), reason="needs AWS credentials")
def test_real_polly_returns_audio():
    audio = PollySynthesizer(Settings().polly).synthesize("Done.")

    assert len(audio) > 1000
