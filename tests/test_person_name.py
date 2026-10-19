import json

import pytest

from brain.interpreter import LlmBrain
from brain.schemas import BrainResult
from brain.summarizer import MockSummarizer
from enums import NextMove
from memory import History, Profile, SqliteMemoryStore
from messages import Prompt
from tools.understand_speech import understand


class RunNow:
    def __init__(self, target, args=(), daemon=None):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)

    def join(self, timeout=None):
        pass


@pytest.fixture(autouse=True)
def tidy_history_in_line(monkeypatch):
    # understand() tidies the history in a background thread. Run it in line, or the store below can be
    # closed while that thread is still reading it, and SQLite crashes the whole test run.
    monkeypatch.setattr("memory.history.Thread", RunNow)


@pytest.fixture
def store(tmp_path):
    store = SqliteMemoryStore(tmp_path / "memory.db")
    yield store
    store.close()


class RecordingBrain:
    def __init__(self):
        self.people = []

    def interpret(self, fragments, history="", person=""):
        self.people.append(person)
        return BrainResult(next_move=NextMove.LISTEN, say="Mm-hm.")


class CapturingClient:
    def complete(self, system, user, schema=None):
        self.system, self.user = system, json.loads(user)
        return BrainResult(next_move=NextMove.LISTEN, say="Mm-hm.").model_dump_json()


def hear(store, brain, heard):
    history = History(store, MockSummarizer(400), recent_messages=10, summary_trigger_words=400)
    return understand(brain, store, history, "demo", "user1", heard, countdown_seconds=5)


def test_the_brain_gets_the_name_the_person_signed_in_with(store):
    store.save_profile("demo", "user1", Profile(name="Ahmed"))
    brain = RecordingBrain()

    hear(store, brain, "call mom")

    assert brain.people == ["Ahmed"]


def test_without_a_name_the_brain_gets_none(store):
    brain = RecordingBrain()

    hear(store, brain, "call mom")

    assert brain.people == [""]


def test_the_name_reaches_the_llm_with_the_rule_for_using_it():
    client = CapturingClient()

    LlmBrain(client).interpret(["call mom"], "", "Ahmed")

    assert client.user["person"] == "Ahmed"
    assert '"person"' in Prompt.UNDERSTAND_SPEECH.text
    assert "never the person to call or message" in client.system
