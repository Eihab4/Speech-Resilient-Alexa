import sqlite3

import pytest

from enums import NextMove, RequestStatus
from memory import DayTries, Request, SqliteMemoryStore, Turn


@pytest.fixture
def store(tmp_path):
    store = SqliteMemoryStore(tmp_path / "memory.db")
    yield store
    store.close()


def finished_request(store, conversation, asks, days_ago, status=RequestStatus.DONE):
    request = Request(intent="call", status=status)
    store.save_request(conversation, request)
    moves = [NextMove.ASK] * asks + [NextMove.CONFIRM, NextMove.DONE]
    for move in moves:
        store.add_turn(conversation, Turn(request_id=request.id, heard="…", say="…", next_move=move))
    store._db.execute(
        "UPDATE turns SET created_at = datetime('now', ?) WHERE request_id = ?", (f"-{days_ago} days", request.id)
    )
    return request


def day(days_ago):
    return sqlite3.connect(":memory:").execute("SELECT date('now', ?)", (f"-{days_ago} days",)).fetchone()[0]


def test_tries_are_averaged_per_request_and_listed_oldest_day_first(store):
    conversation = store.start_conversation("demo", "user1")
    finished_request(store, conversation, asks=4, days_ago=2)
    finished_request(store, conversation, asks=2, days_ago=2)
    finished_request(store, conversation, asks=1, days_ago=0)

    assert store.tries_per_day(conversation, days=14) == [
        DayTries(day=day(2), requests=2, tries=3),
        DayTries(day=day(0), requests=1, tries=1),
    ]


def test_only_finished_requests_count_and_only_the_last_days(store):
    conversation = store.start_conversation("demo", "user1")
    finished_request(store, conversation, asks=5, days_ago=3)
    finished_request(store, conversation, asks=3, days_ago=1)
    finished_request(store, conversation, asks=9, days_ago=0, status=RequestStatus.CANCELLED)

    assert store.tries_per_day(conversation, days=1) == [DayTries(day=day(1), requests=1, tries=3)]


def test_another_persons_requests_are_not_mixed_in(store):
    mine = store.start_conversation("demo", "user1")
    theirs = store.start_conversation("demo", "user2")
    finished_request(store, theirs, asks=4, days_ago=0)

    assert store.tries_per_day(mine, days=14) == []
