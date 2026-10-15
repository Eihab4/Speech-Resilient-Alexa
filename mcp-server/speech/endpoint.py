import logging
from http import HTTPStatus

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from messages import ErrorMessage
from speech.synthesizer import SpeechUnavailable, Synthesizer

logger = logging.getLogger(__name__)


class SpeakRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1)


def _error(message: ErrorMessage, status: HTTPStatus) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def create_speak_endpoint(synthesizer: Synthesizer):
    async def endpoint(request: Request) -> Response:
        try:
            spoken = SpeakRequest.model_validate_json(await request.body())
        except ValidationError:
            return _error(ErrorMessage.SPEECH_TEXT_MISSING, HTTPStatus.BAD_REQUEST)
        try:
            audio = await run_in_threadpool(synthesizer.synthesize, spoken.text)
        except SpeechUnavailable:
            logger.exception(ErrorMessage.SPEECH_UNAVAILABLE)
            return _error(ErrorMessage.SPEECH_UNAVAILABLE, HTTPStatus.SERVICE_UNAVAILABLE)
        return Response(audio, media_type=synthesizer.media_type)

    return endpoint
