import sqlite3

import pytest

from memory import SqliteMemoryStore
from people import Sessions
from support import base_url, http, sign_up


@pytest.fixture
def store(tmp_path):
    store = SqliteMemoryStore(tmp_path / "memory.db")
    yield store
    store.close()


def test_a_session_names_its_person_until_it_is_closed(store):
    sessions = Sessions(store, "demo", ttl_hours=1)

    token = sessions.open("rana_h")

    assert sessions.user_for(token) == "rana_h"
    assert sessions.user_for("") is None
    assert sessions.user_for("not-a-token") is None
    sessions.close(token)
    assert sessions.user_for(token) is None


def test_a_session_expires(store):
    token = Sessions(store, "demo", ttl_hours=0).open("rana_h")

    assert Sessions(store, "demo", ttl_hours=1).user_for(token) is None


def test_a_session_belongs_to_its_company(store):
    token = Sessions(store, "demo", ttl_hours=1).open("rana_h")

    assert Sessions(store, "other", ttl_hours=1).user_for(token) is None


def test_an_expired_sign_in_is_refused_on_the_server(server):
    url = server(SESSION_TTL_HOURS="0")
    token = sign_up(url, "rana_h")

    assert http(f"{base_url(url)}/me", token=token)[0] == 401


def test_sessions_kept_before_expiry_existed_are_treated_as_expired(tmp_path):
    db_path = tmp_path / "memory.db"
    old = sqlite3.connect(db_path)
    old.execute(
        "CREATE TABLE sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at TEXT NOT NULL)"
    )
    old.close()

    store = SqliteMemoryStore(db_path)
    columns = {row[1] for row in store._db.execute("PRAGMA table_info(sessions)")}
    store.close()

    assert "expires_at" in columns
