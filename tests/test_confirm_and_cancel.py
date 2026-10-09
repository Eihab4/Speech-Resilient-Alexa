import pytest

from enums import NextMove, RequestStatus
from memory import SqliteMemoryStore
from messages import Reply
from support import with_client


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "memory.db"


def call(url, tool, **arguments):
    async def run(client):
        return (await client.call_tool(tool, arguments)).structured_content

    return with_client(url, run)


def say(url, heard, user_id="u1"):
    return call(url, "understand_speech", user_id=user_id, heard=heard)


def confirmed_reminder(url):
    say(url, "tomorrow")
    say(url, "doctor ten")
    return say(url, "yes")


def inspect(db_path, user_id="u1"):
    store = SqliteMemoryStore(db_path)
    conversation = store.conversation_for("demo", user_id)
    pending, actions = store.pending_request(conversation), store.actions(conversation)
    store.close()
    return pending, actions


def test_a_yes_then_do_confirmed_request_performs_the_action(server, db_path):
    url = server()
    yes = confirmed_reminder(url)

    done = call(url, "do_confirmed_request", user_id="u1", pending_id=yes["pending_id"])
    pending, actions = inspect(db_path)

    assert yes["next_move"] == NextMove.DONE
    assert done == {"done": True, "say": "Done. Reminder set: doctor appointment, tomorrow 10:00."}
    assert [action.result for action in actions] == ["Reminder set: doctor appointment, tomorrow 10:00."]
    assert pending is None


@pytest.mark.parametrize("word", ["yeah", "mm-hm", "Yep"])
def test_any_kind_of_yes_counts(server, word):
    url = server()
    say(url, "call mom")

    assert say(url, word)["next_move"] == NextMove.DONE


def test_nothing_happens_before_a_yes(server, db_path):
    url = server()
    say(url, "call mom")
    pending_id = say(url, "tomorrow")["pending_id"]

    result = call(url, "do_confirmed_request", user_id="u1", pending_id=pending_id)

    assert result == {"done": False, "say": Reply.NEEDS_YES}
    assert inspect(db_path)[1] == []


def test_another_user_cannot_run_someone_elses_request(server, db_path):
    url = server()
    yes = confirmed_reminder(url)

    result = call(url, "do_confirmed_request", user_id="u2", pending_id=yes["pending_id"])

    assert result["done"] is False
    assert inspect(db_path)[1] == []


def test_a_request_runs_only_once(server, db_path):
    url = server()
    pending_id = confirmed_reminder(url)["pending_id"]
    call(url, "do_confirmed_request", user_id="u1", pending_id=pending_id)

    again = call(url, "do_confirmed_request", user_id="u1", pending_id=pending_id)

    assert again["done"] is False
    assert len(inspect(db_path)[1]) == 1


def test_a_plain_no_asks_what_to_change_and_keeps_the_request(server, db_path):
    url = server()
    say(url, "call mom")

    result = say(url, "no")

    assert result["next_move"] == NextMove.ASK
    assert result["say"] == Reply.WHAT_TO_CHANGE
    assert inspect(db_path)[0].status == RequestStatus.PENDING


def test_a_no_with_a_correction_changes_only_that_part(server):
    url = server()
    say(url, "call sara")

    result = say(url, "no mom")

    assert result["details"] == {"who": "mom"}
    assert result["changed"] == ["who"]
    assert result["next_move"] == NextMove.CONFIRM


def test_cancel_drops_the_request_and_the_next_words_start_fresh(server, db_path):
    url = server()
    say(url, "tomorrow")

    cancelled = call(url, "cancel_request", user_id="u1")
    fresh = say(url, "doctor")

    assert cancelled == {"cancelled": True, "say": Reply.CANCELLED}
    assert inspect(db_path)[0].status == RequestStatus.PENDING
    assert fresh["say"] == "What time?"


def test_never_mind_tells_the_agent_to_cancel_then_clears_the_request(server, db_path):
    url = server()
    say(url, "tomorrow")

    decision = say(url, "never mind")
    cancelled = call(url, "cancel_request", user_id="u1")

    assert decision["next_move"] == NextMove.CANCEL
    assert cancelled == {"cancelled": True, "say": Reply.CANCELLED}
    assert inspect(db_path)[0] is None


def test_cancel_with_nothing_pending_says_so(server):
    assert call(server(), "cancel_request", user_id="u1") == {"cancelled": False, "say": Reply.NOTHING_PENDING}


def test_after_done_the_next_words_start_a_new_request(server):
    url = server()
    pending_id = confirmed_reminder(url)["pending_id"]
    call(url, "do_confirmed_request", user_id="u1", pending_id=pending_id)

    assert say(url, "doctor")["say"] == "What time?"


def test_every_tool_tells_the_agent_when_to_use_it(server):
    async def descriptions(client):
        return {tool.name: tool.description for tool in await client.list_tools()}

    tools = with_client(server(), descriptions)

    assert set(tools) == {"understand_speech", "do_confirmed_request", "cancel_request", "resume_unfinished"}
    assert all(description for description in tools.values())
