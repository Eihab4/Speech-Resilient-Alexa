import sqlite3

import pytest

from enums import NextMove
from memory import Request, SqliteMemoryStore
from messages import Reply
from support import token_for, with_client


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "memory.db"


def call(url, tool, user_id="user1", **arguments):
    async def run(client):
        return (await client.call_tool(tool, arguments)).structured_content

    return with_client(url, run, token_for(url, user_id))


def age_requests(db_path, days):
    with sqlite3.connect(db_path) as db:
        db.execute("UPDATE requests SET updated_at = datetime('now', ?)", (f"-{days} days",))


def test_the_comeback_scenario(server):
    call(server(), "understand_speech", user_id="user1", heard="remind pills")

    url = server()
    resumed = call(url, "resume_unfinished", user_id="user1")
    time = call(url, "understand_speech", user_id="user1", heard="eight")
    yes = call(url, "understand_speech", user_id="user1", heard="yes")

    assert resumed["found"] is True
    assert resumed["say"] == "You didn't finish your reminder last time. Want to pick it up?"
    assert time["next_move"] == NextMove.CONFIRM
    assert time["details"] == {"what": "pills", "when": "8:00"}
    assert yes["next_move"] == NextMove.DONE
    assert yes["pending_id"] == resumed["pending_id"]


def test_nothing_to_resume_says_so(server):
    assert call(server(), "resume_unfinished", user_id="user1") == {"found": False, "say": Reply.NOTHING_PENDING}


def test_a_finished_request_is_not_offered_again(server):
    url = server()
    call(url, "understand_speech", user_id="user1", heard="call mom")
    pending_id = call(url, "understand_speech", user_id="user1", heard="yes")["pending_id"]
    call(url, "do_confirmed_request", user_id="user1", pending_id=pending_id)

    assert call(url, "resume_unfinished", user_id="user1")["found"] is False


def test_an_old_unfinished_request_expires_and_new_words_start_fresh(server, db_path):
    call(server(), "understand_speech", user_id="user1", heard="remind pills")
    age_requests(db_path, days=2)

    url = server()
    resumed = call(url, "resume_unfinished", user_id="user1")
    fresh = call(url, "understand_speech", user_id="user1", heard="doctor")

    assert resumed["found"] is False
    assert fresh["say"] == "What time?"


def test_the_expiry_window_comes_from_settings(server, db_path):
    call(server(), "understand_speech", user_id="user1", heard="remind pills")
    age_requests(db_path, days=2)

    assert call(server(MEMORY_UNFINISHED_TTL_HOURS="72"), "resume_unfinished", user_id="user1")["found"] is True


def test_the_store_hides_expired_pending_requests(db_path):
    store = SqliteMemoryStore(db_path, unfinished_ttl_hours=1)
    conversation = store.start_conversation("acme", "user1")
    store.save_request(conversation, Request(intent="reminder"))
    age_requests(db_path, days=1)

    assert store.pending_request(conversation) is None
    store.close()
