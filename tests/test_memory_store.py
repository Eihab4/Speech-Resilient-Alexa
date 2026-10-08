import sqlite3

import pytest

from enums import NextMove, RequestStatus
from memory import Request, SqliteMemoryStore


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "memory.db"


@pytest.fixture
def store(db_path):
    store = SqliteMemoryStore(db_path)
    yield store
    store.close()


def test_turns_come_back_in_the_order_they_were_said(store):
    conversation = store.start_conversation("acme", "u1")
    for heard in ["tomorrow", "doctor ten", "yes"]:
        store.add_turn(conversation, heard, "ok", NextMove.LISTEN)

    assert [turn.heard for turn in store.turns(conversation)] == ["tomorrow", "doctor ten", "yes"]
    assert [turn.seq for turn in store.turns(conversation)] == [1, 2, 3]


def test_memory_survives_closing_and_reopening_the_file(db_path):
    first = SqliteMemoryStore(db_path)
    conversation = first.start_conversation("acme", "u1")
    first.add_turn(conversation, "remind pills", "What time?", NextMove.ASK)
    first.save_request(conversation, Request(intent="reminder", details={"what": "pills"}))
    first.close()

    second = SqliteMemoryStore(db_path)

    assert second.turns(conversation)[0].say == "What time?"
    assert second.pending_request(conversation).details == {"what": "pills"}


def test_same_user_id_in_two_companies_never_shares_a_conversation(store):
    acme = store.start_conversation("acme", "u1")
    globex = store.start_conversation("globex", "u1")
    store.add_turn(acme, "call mom", "Call Mom?", NextMove.CONFIRM)

    assert acme != globex
    assert store.turns(globex) == []


def test_a_turn_cannot_belong_to_a_missing_conversation(store):
    with pytest.raises(sqlite3.IntegrityError):
        store.add_turn(999, "hello", "hi", NextMove.LISTEN)


def test_saving_the_same_request_again_updates_it_in_place(store):
    conversation = store.start_conversation("acme", "u1")
    request = Request(intent="reminder", details={"what": "doctor"})
    store.save_request(conversation, request)
    store.save_request(conversation, request.model_copy(update={"details": {"what": "doctor", "when": "10:00"}}))

    pending = store.pending_request(conversation)

    assert pending.id == request.id
    assert pending.details == {"what": "doctor", "when": "10:00"}


def test_done_and_cancelled_requests_are_no_longer_pending(store):
    conversation = store.start_conversation("acme", "u1")
    for status in [RequestStatus.DONE, RequestStatus.CANCELLED]:
        store.save_request(conversation, Request(intent="call", status=status))

    assert store.pending_request(conversation) is None


def test_actions_are_logged_against_their_request(store):
    conversation = store.start_conversation("acme", "u1")
    request = Request(intent="call", details={"who": "mom"})
    store.save_request(conversation, request)

    store.log_action(request.id, "Called Mom")

    assert [action.result for action in store.actions(conversation)] == ["Called Mom"]
    assert store.actions(store.start_conversation("acme", "u2")) == []


def test_a_failed_conversation_start_leaves_nothing_behind(store, db_path, monkeypatch):
    monkeypatch.setattr("memory.sqlite.utc_now", lambda: None)

    with pytest.raises(sqlite3.IntegrityError):
        store.start_conversation("acme", "u1")

    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM companies").fetchone()[0] == 0
