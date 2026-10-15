import json
from http import HTTPStatus
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import boto3
import pytest

from messages import ErrorMessage


def speak_url(url: str) -> str:
    return url.rsplit("/", 1)[0] + "/speak"


def post(url: str, body: bytes):
    request = Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urlopen(request) as response:
            return response.status, response.headers["Content-Type"], response.read()
    except HTTPError as error:
        return error.code, error.headers["Content-Type"], error.read()


def test_speaking_needs_text(server):
    status, _, body = post(speak_url(server()), json.dumps({"text": "  "}).encode())

    assert status == HTTPStatus.BAD_REQUEST
    assert json.loads(body)["error"] == ErrorMessage.SPEECH_TEXT_MISSING


def test_the_page_is_told_when_polly_is_unavailable(server):
    url = speak_url(server(AWS_ACCESS_KEY_ID="invalid", AWS_SECRET_ACCESS_KEY="invalid", AWS_SESSION_TOKEN=None))

    status, _, body = post(url, json.dumps({"text": "Done."}).encode())

    assert status == HTTPStatus.SERVICE_UNAVAILABLE
    assert json.loads(body)["error"] == ErrorMessage.SPEECH_UNAVAILABLE


@pytest.mark.skipif(not boto3.Session().get_credentials(), reason="needs AWS credentials")
def test_the_page_gets_audio_back(server):
    status, content_type, body = post(speak_url(server()), json.dumps({"text": "Done."}).encode())

    assert status == HTTPStatus.OK
    assert content_type == "audio/mpeg"
    assert len(body) > 1000
