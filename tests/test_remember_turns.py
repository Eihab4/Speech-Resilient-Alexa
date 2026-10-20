import sqlite3

import pytest

from enums import NextMove
from memory import SqliteMemoryStore
from support import token_for, with_client


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "memory.db"


async def understand(client, heard):
    result = await client.call_tool("understand_speech", {"heard": heard})
    return result.structured_content


def say(url, user_id, heard):
    return with_client(url, lambda client: understand(client, heard), token_for(url, user_id))


def test_pieces_from_earlier_turns_are_combined(server):
    url = server()

    first = say(url, "user1", "tomorrow")
    second = say(url, "user1", "doctor ten")

    assert first["next_move"] == NextMove.LISTEN
    assert second["next_move"] == NextMove.CONFIRM
    assert "doctor" in second["say"]


def test_pieces_survive_a_server_restart(server):
    say(server(), "user1", "tomorrow")

    result = say(server(), "user1", "doctor ten")

    assert result["next_move"] == NextMove.CONFIRM


def test_users_never_hear_each_others_pieces(server):
    url = server()
    say(url, "user1", "tomorrow")

    result = say(url, "user2", "doctor")

    assert result["say"] == "What time?"


def test_every_turn_is_saved_with_what_alexa_said(server, db_path):
    url = server()
    say(url, "user1", "tomorrow")
    say(url, "user1", "   ")
    say(url, "user1", "doctor ten")

    store = SqliteMemoryStore(db_path)
    turns = store.turns(store.conversation_for("demo", "user1"))
    store.close()

    assert [(turn.heard, turn.say) for turn in turns] == [
        ("tomorrow", "Mm-hm, go on."),
        ("doctor ten", "Should I set a reminder for your doctor appointment tomorrow at 10 AM?"),
    ]
    assert len({turn.request_id for turn in turns}) == 1


def test_the_company_comes_from_settings_not_from_the_caller(server, db_path):
    say(server(MEMORY_COMPANY_ID="acme"), "user1", "tomorrow")

    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT company_id FROM users").fetchall() == [("acme",)]
