from memory import MemoryStore
from people.passwords import new_token, token_hash
from utils import hours_from_now


class Sessions:
    def __init__(self, store: MemoryStore, company_id: str, ttl_hours: float) -> None:
        self._store = store
        self._company_id = company_id
        self._ttl_hours = ttl_hours

    def open(self, username: str) -> str:
        token = new_token()
        self._store.add_session(self._company_id, username, token_hash(token), hours_from_now(self._ttl_hours))
        return token

    def user_for(self, token: str) -> str | None:
        return self._store.session_user(self._company_id, token_hash(token)) if token else None

    def close(self, token: str) -> None:
        self._store.remove_session(token_hash(token))
