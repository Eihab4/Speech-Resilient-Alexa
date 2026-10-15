import pytest

from enums import NextMove, RequestStatus
from memory import SqliteMemoryStore
from messages import Reply
from support import with_client

SWITCH_QUESTION = "Should I stop the doctor reminder and call Mom instead?"
REMINDER_QUESTION = "Should I set a reminder for your doctor appointment tomorrow at 10 AM?"


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "memory.db"


def call(url, tool, **arguments):
    async def run(client):
        return (await client.call_tool(tool, arguments)).structured_content

    return with_client(url, run)


def say(url, heard):
    return call(url, "understand_speech", user_id="u1", heard=heard)


def call_mom_during_a_reminder(url):
    say(url, "tomorrow")
    reminder = say(url, "doctor ten")
    return reminder, say(url, "call mom")


def inspect(db_path, request_id):
    store = SqliteMemoryStore(db_path)
    conversation = store.conversation_for("demo", "u1")
    request, pieces = store.request(conversation, request_id), store.turns(conversation, request_id)
    store.close()
    return request, [turn.heard for turn in pieces]


def test_a_correction_stays_in_the_same_request(server):
    url = server()
    first = say(url, "call sara")

    corrected = say(url, "no mom")

    assert corrected["next_move"] == NextMove.CONFIRM
    assert corrected["details"] == {"who": "mom"}
    assert corrected["pending_id"] == first["pending_id"]


def test_a_new_request_asks_before_dropping_the_open_one(server, db_path):
    url = server()

    reminder, switch = call_mom_during_a_reminder(url)
    request, pieces = inspect(db_path, reminder["pending_id"])

    assert switch["next_move"] == NextMove.SWITCH
    assert switch["say"] == SWITCH_QUESTION
    assert request.status == RequestStatus.PENDING
    assert request.details == {"what": "doctor appointment", "when": "tomorrow 10:00"}
    assert pieces == ["tomorrow", "doctor ten"]


def test_yes_cancels_the_open_request_and_starts_the_new_one(server, db_path):
    url = server()
    reminder, _ = call_mom_during_a_reminder(url)

    switched = say(url, "yes")
    old, _ = inspect(db_path, reminder["pending_id"])
    new, new_pieces = inspect(db_path, switched["pending_id"])

    assert switched["next_move"] == NextMove.CONFIRM
    assert switched["say"] == "Call Mom?"
    assert switched["pending_id"] != reminder["pending_id"]
    assert old.status == RequestStatus.CANCELLED
    assert (new.intent, new.details, new_pieces) == ("call", {"who": "mom"}, ["call mom"])


def test_the_new_request_can_then_be_carried_out(server):
    url = server()
    call_mom_during_a_reminder(url)
    say(url, "yes")

    confirmed = say(url, "yes")
    done = call(url, "do_confirmed_request", user_id="u1", pending_id=confirmed["pending_id"])

    assert done == {"done": True, "say": "Done. Calling mom."}


def test_no_keeps_the_open_request_and_asks_its_question_again(server, db_path):
    url = server()
    reminder, _ = call_mom_during_a_reminder(url)

    kept = say(url, "no")
    request, pieces = inspect(db_path, reminder["pending_id"])

    assert kept["say"] == Reply.BACK_TO_IT.format(question=REMINDER_QUESTION)
    assert kept["next_move"] == NextMove.CONFIRM
    assert kept["pending_id"] == reminder["pending_id"]
    assert request.status == RequestStatus.PENDING
    assert pieces == ["tomorrow", "doctor ten"]


def test_after_no_a_yes_confirms_the_open_request(server):
    url = server()
    call_mom_during_a_reminder(url)
    say(url, "no")

    confirmed = say(url, "yes")
    done = call(url, "do_confirmed_request", user_id="u1", pending_id=confirmed["pending_id"])

    assert done == {"done": True, "say": "Done. Reminder set: doctor appointment, tomorrow 10:00."}
