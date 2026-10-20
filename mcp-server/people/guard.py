from collections.abc import Awaitable, Callable
from http import HTTPStatus

from starlette.requests import HTTPConnection, Request
from starlette.responses import JSONResponse, Response

from enums import SocketProtocol
from messages import ErrorMessage
from people.sessions import Sessions


def bearer(connection: HTTPConnection) -> str:
    scheme, _, token = connection.headers.get("authorization", "").partition(" ")
    return token.strip() if scheme.lower() == "bearer" else ""


def offered_token(connection: HTTPConnection) -> str:
    protocols = [name.strip() for name in connection.headers.get("sec-websocket-protocol", "").split(",")]
    return protocols[1] if len(protocols) == 2 and protocols[0] == SocketProtocol.BEARER else ""


class Guard:
    def __init__(self, sessions: Sessions) -> None:
        self._sessions = sessions

    def user(self, connection: HTTPConnection) -> str | None:
        return self._sessions.user_for(bearer(connection) or offered_token(connection))

    def require(self, handler: Callable[[Request, str], Awaitable[Response]]) -> Callable:
        async def endpoint(request: Request) -> Response:
            if not (username := self.user(request)):
                return JSONResponse({"error": ErrorMessage.NOT_SIGNED_IN}, status_code=HTTPStatus.UNAUTHORIZED)
            return await handler(request, username)

        return endpoint
