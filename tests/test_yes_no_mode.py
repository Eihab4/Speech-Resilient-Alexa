import pytest

from brain.schemas import BrainResult
from brain.summarizer import MockSummarizer
from config.settings import PauseSettings
from enums import NextMove
from memory import History, SqliteMemoryStore
from pacing import Pacing
from tools.do_confirmed_request import do_confirmed_request
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

    def interpret(self, fragments, history="", person=""):
        self.calls.append(fragments)
        return self.answers.pop(0)


def ask(question):
    return BrainResult(intent="call", next_move=NextMove.ASK, say=question)


def hear(store, brain, heard):
    history = History(store, MockSummarizer(400), recent_messages=10, summary_trigger_words=400)
    return understand(
        brain, store, history, "demo", "user1", heard, countdown_seconds=5, pacing=Pacing(store, PauseSettings())
    )


def test_every_reply_counts_how_often_alexa_had_to_ask(store):
    brain = ScriptedBrain(
        BrainResult(next_move=NextMove.LISTEN, say="Mm-hm."),
        ask("Who do you want to call?"),
        ask("Say the name once more?"),
        BrainResult(intent="call", details={"who": "mom"}, next_move=NextMove.CONFIRM, say="Call Mom?"),
    )

    tries = [hear(store, brain, heard)["tries"] for heard in ["call", "c", "cuh", "mom"]]

    assert tries == [0, 1, 2, 2]


def test_a_new_request_starts_counting_again(store):
    brain = ScriptedBrain(
        ask("Who do you want to call?"),
        BrainResult(intent="call", details={"who": "mom"}, next_move=NextMove.CONFIRM, say="Call Mom?"),
        ask("Remind you of what?"),
    )
    hear(store, brain, "call")
    hear(store, brain, "mom")
    do_confirmed_request(store, "demo", "user1", hear(store, brain, "yes")["pending_id"])

    assert hear(store, brain, "remind")["tries"] == 1
