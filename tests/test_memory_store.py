import sqlite3

import pytest

from enums import NextMove, RequestStatus
from memory import Helper, Profile, Request, SqliteMemoryStore, Turn


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
        store.add_turn(conversation, Turn(heard=heard, say="ok", next_move=NextMove.LISTEN))

    assert [turn.heard for turn in store.turns(conversation)] == ["tomorrow", "doctor ten", "yes"]
    assert [turn.seq for turn in store.turns(conversation)] == [1, 2, 3]


def test_memory_survives_closing_and_reopening_the_file(db_path):
    first = SqliteMemoryStore(db_path)
    conversation = first.start_conversation("acme", "u1")
    first.add_turn(conversation, Turn(heard="remind pills", say="What time?", next_move=NextMove.ASK))
    first.save_request(conversation, Request(intent="reminder", details={"what": "pills"}))
    first.close()

    second = SqliteMemoryStore(db_path)

    assert second.turns(conversation)[0].say == "What time?"
    assert second.pending_request(conversation).details == {"what": "pills"}


def test_same_user_id_in_two_companies_never_shares_a_conversation(store):
    acme = store.start_conversation("acme", "u1")
    globex = store.start_conversation("globex", "u1")
    store.add_turn(acme, Turn(heard="call mom", say="Call Mom?", next_move=NextMove.CONFIRM))

    assert acme != globex
    assert store.turns(globex) == []


def test_a_turn_cannot_belong_to_a_missing_conversation(store):
    with pytest.raises(sqlite3.IntegrityError):
        store.add_turn(999, Turn(heard="hello", say="hi", next_move=NextMove.LISTEN))


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


def test_turns_can_be_filtered_to_one_request(store):
    conversation = store.start_conversation("acme", "u1")
    old, current = Request(intent="call"), Request(intent="reminder")
    for request in [old, current]:
        store.save_request(conversation, request)
    store.add_turn(conversation, Turn(request_id=old.id, heard="call mom", say="Call Mom?", next_move=NextMove.CONFIRM))
    store.add_turn(conversation, Turn(request_id=current.id, heard="tomorrow", say="Go on.", next_move=NextMove.LISTEN))

    assert [turn.heard for turn in store.turns(conversation, current.id)] == ["tomorrow"]
    assert len(store.turns(conversation)) == 2


def test_conversation_for_reuses_the_latest_one(store):
    first = store.conversation_for("acme", "u1")

    assert store.conversation_for("acme", "u1") == first
    assert store.conversation_for("acme", "u2") != first


def test_a_profile_is_saved_once_per_person_and_updated_in_place(store):
    store.save_profile("acme", "u1", Profile(name="Ahmed"))
    store.save_profile("acme", "u1", Profile(name="Ahmed Ali", home_address="12 Tahrir St"))

    assert store.profile("acme", "u1") == Profile(name="Ahmed Ali", home_address="12 Tahrir St")
    assert store.profile("acme", "u2") is None


def test_helpers_belong_to_one_person_and_link_with_their_code(store):
    sara = store.add_helper("acme", "u1", Helper(name="Sara"))
    store.add_helper("acme", "u2", Helper(name="Omar"))

    linked = store.link_helper(sara.link_code, "12345")

    assert [helper.name for helper in store.helpers("acme", "u1")] == ["Sara"]
    assert linked.telegram_chat_id == "12345"
    assert store.helpers("acme", "u1")[0].linked
    assert store.link_helper("not-a-code", "999") is None
