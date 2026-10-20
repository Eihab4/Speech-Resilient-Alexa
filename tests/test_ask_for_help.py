import pytest

from brain.schemas import BrainResult
from brain.summarizer import MockSummarizer
from config.settings import PauseSettings
from enums import AskMode, NextMove, RequestStatus
from memory import History, SqliteMemoryStore
from messages import Reply
from pacing import Pacing
from tools.ask_for_help import asks_for_help
from tools.understand_speech import understand

pytestmark = pytest.mark.usefixtures("history_in_line")


@pytest.fixture
def store(tmp_path):
    store = SqliteMemoryStore(tmp_path / "memory.db")
    yield store
    store.close()


class ScriptedBrain:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = []

    def interpret(self, fragments, history="", person="", question="", mode=AskMode.OPEN):
        self.calls.append(fragments)
        return self.answers.pop(0)


def hear(store, brain, heard):
    history = History(store, MockSummarizer(400), recent_messages=10, summary_trigger_words=400)
    return understand(
        brain, store, history, "demo", "user1", heard, countdown_seconds=5, pacing=Pacing(store, PauseSettings())
    )


@pytest.mark.parametrize("heard", ["help", "Help!", "help me", "I need help.", "get help"])
def test_asking_for_help_is_heard_as_the_whole_piece(heard):
    assert asks_for_help(heard)


@pytest.mark.parametrize("heard", ["help help", "call mom", "helpful", "help me call mom"])
def test_other_words_are_not_a_call_for_help(heard):
    assert not asks_for_help(heard)


def test_saying_help_keeps_the_open_request_and_never_reaches_the_brain(store):
    brain = ScriptedBrain(
        BrainResult(intent="call", next_move=NextMove.ASK, say="Who do you want to call?"),
        BrainResult(intent="call", details={"who": "mom"}, next_move=NextMove.CONFIRM, say="Call Mom?"),
    )
    started = hear(store, brain, "call")

    helped = hear(store, brain, "help")
    went_on = hear(store, brain, "mom")

    assert helped["next_move"] == NextMove.HELP
    assert helped["say"] == Reply.HELP_ASKED
    assert helped["pending_id"] == started["pending_id"]
    assert helped["intent"] == "call"
    assert brain.calls == [["call"], ["call", "mom"]]
    assert went_on["next_move"] == NextMove.CONFIRM
    assert store.pending_request(store.conversation_for("demo", "user1")).status == RequestStatus.PENDING


def test_help_with_nothing_open_belongs_to_no_request(store):
    result = hear(store, ScriptedBrain(), "help me")

    assert result["next_move"] == NextMove.HELP
    assert result["pending_id"] is None
