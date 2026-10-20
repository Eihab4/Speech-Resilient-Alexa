from fastmcp.server.auth import AccessToken, TokenVerifier
from starlette.concurrency import run_in_threadpool

from people.sessions import Sessions


class SessionVerifier(TokenVerifier):
    def __init__(self, sessions: Sessions) -> None:
        super().__init__()
        self._sessions = sessions

    async def verify_token(self, token: str) -> AccessToken | None:
        username = await run_in_threadpool(self._sessions.user_for, token)
        if username is None:
            return None
        return AccessToken(token=token, client_id=username, scopes=[], subject=username)
