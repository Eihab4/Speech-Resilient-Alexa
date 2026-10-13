import time

import pytest

from brain.factory import create_client
from brain.interpreter import LlmBrain
from brain.summarizer import LlmSummarizer, MockSummarizer
from config import get_settings
from enums import NextMove
from memory import History, Request, SqliteMemoryStore, Turn
from support import needs_real_llm, with_client


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "memory.db"


@pytest.fixture
def store(db_path):
    store = SqliteMemoryStore(db_path)
    yield store
    store.close()


def call(url, tool, **arguments):
    async def run(client):
        return (await client.call_tool(tool, arguments)).structured_content

    return with_client(url, run)


def finish_a_call(url, user_id="u1"):
    call(url, "understand_speech", user_id=user_id, heard="call mom")
    pending_id = call(url, "understand_speech", user_id=user_id, heard="yes")["pending_id"]
    call(url, "do_confirmed_request", user_id=user_id, pending_id=pending_id)


def wait_for_summary(store, conversation, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        summary = store.summary(conversation)
        if summary.text:
            return summary
        time.sleep(0.1)
    raise TimeoutError("no summary was written")


def finished_request(store, conversation, lines):
    request = Request(intent="call", status="done")
    store.save_request(conversation, request)
    for heard, say in lines:
        store.add_turn(conversation, Turn(request_id=request.id, heard=heard, say=say, next_move=NextMove.CONFIRM))


def test_a_short_conversation_shows_the_brain_the_full_history(store):
    conversation = store.start_conversation("acme", "u1")
    finished_request(store, conversation, [("call mom", "Call Mom?"), ("yes", "Okay.")])
    history = History(store, MockSummarizer(50), recent_messages=10, summary_trigger_words=400)

    history.maintain(conversation)

    assert history.for_brain(conversation) == "person: call mom\nalexa: Call Mom?\nperson: yes\nalexa: Okay."
    assert store.summary(conversation).text == ""


def test_the_request_in_progress_is_never_part_of_the_history(store):
    conversation = store.start_conversation("acme", "u1")
    store.save_request(conversation, Request(intent="reminder"))
    store.add_turn(
        conversation,
        Turn(
            request_id=store.pending_request(conversation).id, heard="tomorrow", say="Go on.", next_move=NextMove.LISTEN
        ),
    )

    assert History(store, MockSummarizer(50), 10, 400).for_brain(conversation) == ""


def test_a_long_conversation_is_summarized_in_the_background_and_nothing_is_deleted(server, db_path):
    url = server(MEMORY_SUMMARY_TRIGGER_WORDS="5", MEMORY_RECENT_MESSAGES="2")
    for _ in range(3):
        finish_a_call(url)

    store = SqliteMemoryStore(db_path)
    conversation = store.conversation_for("demo", "u1")
    summary = wait_for_summary(store, conversation)
    history = History(store, MockSummarizer(5), recent_messages=2, summary_trigger_words=5)
    seen, turns = history.for_brain(conversation), store.turns(conversation)
    store.close()

    assert summary.text
    assert summary.covers_up_to_seq >= 1
    assert len(turns) == 6
    assert seen.startswith(summary.text)
    assert seen[len(summary.text) :].count("person:") == 2


def test_the_summary_grows_from_the_previous_one(store):
    conversation = store.start_conversation("acme", "u1")
    history = History(store, MockSummarizer(50), recent_messages=0, summary_trigger_words=3)
    finished_request(store, conversation, [("call mom", "Call Mom?"), ("yes", "Okay.")])
    history.maintain(conversation)
    first = store.summary(conversation)
    finished_request(store, conversation, [("message ahmed late", "Send it?"), ("yes", "Okay.")])

    history.maintain(conversation)
    second = store.summary(conversation)

    assert second.text.startswith(first.text)
    assert "ahmed" in second.text
    assert second.covers_up_to_seq == 4


def test_a_failing_summarizer_leaves_memory_untouched(store):
    conversation = store.start_conversation("acme", "u1")
    finished_request(store, conversation, [("call mom", "Call Mom?"), ("yes", "Okay.")])

    class Broken:
        def summarize(self, previous, turns):
            raise RuntimeError("llm down")

    with pytest.raises(RuntimeError):
        History(store, Broken(), recent_messages=0, summary_trigger_words=1).maintain(conversation)

    assert store.summary(conversation).text == ""
    assert len(store.turns(conversation)) == 2


@needs_real_llm
def test_the_real_llm_summarizes_and_uses_the_history():
    client = create_client(get_settings())
    turns = [
        Turn(heard="call mom", say="Call Mom?", next_move=NextMove.CONFIRM),
        Turn(heard="yes", say="Okay.", next_move=NextMove.DONE),
    ]

    summary = LlmSummarizer(client).summarize("", turns)
    result = LlmBrain(client).interpret(["message her I'm late"], summary)

    assert "mom" in summary.lower()
    assert "mom" in str(result.details).lower()
