import asyncio
import logging
from collections.abc import Callable

from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.exceptions import SDKError
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from awscrt.exceptions import AwsCrtError
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from config.settings import TranscribeSettings
from enums import SocketProtocol, TranscriptType

logger = logging.getLogger(__name__)

# Policy violation: the page's origin is not one we serve.
FORBIDDEN_ORIGIN = 1008


class _Relay(TranscriptResultStreamHandler):
    """Passes every transcript Transcribe produces back to the page."""

    def __init__(self, output_stream, websocket: WebSocket) -> None:
        super().__init__(output_stream)
        self._websocket = websocket
        self.heard_anything = False

    async def handle_transcript_event(self, transcript_event) -> None:
        for result in transcript_event.transcript.results:
            text = result.alternatives[0].transcript.strip() if result.alternatives else ""
            if not text:
                continue
            self.heard_anything = True
            kind = TranscriptType.PARTIAL if result.is_partial else TranscriptType.FINAL
            await _send(self._websocket, kind, text)


async def _send(websocket: WebSocket, kind: TranscriptType, text: str = "") -> None:
    if websocket.application_state == WebSocketState.CONNECTED:
        await websocket.send_json({"type": kind, "text": text})


async def _forward_audio(websocket: WebSocket, input_stream) -> None:
    """Binary messages are audio. A text message (or the page going away) means the person stopped."""
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect" or message.get("text") is not None:
                break
            if message.get("bytes"):
                await input_stream.send_audio_event(audio_chunk=message["bytes"])
    except WebSocketDisconnect:
        pass
    finally:
        await input_stream.end_stream()


def create_transcribe_endpoint(
    settings: TranscribeSettings,
    is_allowed_origin: Callable[[str | None], bool],
    user_of: Callable[[WebSocket], str | None],
):
    """A WebSocket endpoint: 16-bit mono PCM in, {"type", "text"} transcripts out.

    The AWS credentials stay on the server; the browser only ever sees text.
    """

    async def endpoint(websocket: WebSocket) -> None:
        # Browsers always send Origin, and CORS does not cover WebSockets, so check it here.
        if not is_allowed_origin(websocket.headers.get("origin")) or user_of(websocket) is None:
            await websocket.close(code=FORBIDDEN_ORIGIN)
            return
        offered = SocketProtocol.BEARER in websocket.headers.get("sec-websocket-protocol", "")
        await websocket.accept(subprotocol=SocketProtocol.BEARER if offered else None)

        relay = None
        try:
            stream = await TranscribeStreamingClient(region=settings.region).start_stream_transcription(
                language_code=settings.language_code,
                media_sample_rate_hz=settings.sample_rate_hz,
                media_encoding="pcm",
            )
            relay = _Relay(stream.output_stream, websocket)
            await asyncio.gather(_forward_audio(websocket, stream.input_stream), relay.handle_events())
        except (SDKError, AwsCrtError):
            logger.exception("Amazon Transcribe failed")
            # Before anything was heard, the page can still switch to the browser's own recognition.
            failed = TranscriptType.ERROR if relay and relay.heard_anything else TranscriptType.UNAVAILABLE
            await _send(websocket, failed)
        finally:
            if websocket.application_state == WebSocketState.CONNECTED:
                await websocket.close()

    return endpoint
