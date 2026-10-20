import pytest

from brain.interpreter import LlmBrain
from brain.schemas import BrainResult
from brain.summarizer import MockSummarizer
from config.settings import PauseSettings
from enums import AskMode, NextMove
from memory import History, SqliteMemoryStore
from pacing import Pacing
from support import CapturingClient, token_for, with_client
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
        self.modes = []

    def interpret(self, fragments, history="", person="", question="", mode=AskMode.OPEN):
        self.calls.append((fragments, question))
        self.modes.append(mode)
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


def test_the_brain_is_told_what_alexa_last_said_about_the_request(store):
    brain = ScriptedBrain(
        ask("Who do you want to call?"),
        BrainResult(intent="call", details={"who": "mom"}, next_move=NextMove.CONFIRM, say="Call Mom?"),
    )

    hear(store, brain, "call")
    hear(store, brain, "mom")

    assert brain.calls == [(["call"], ""), (["call", "mom"], "Who do you want to call?")]


def test_the_question_reaches_the_model(store):
    client = CapturingClient()

    hear(store, LlmBrain(client), "call")

    assert client.user["question"] == ""
    assert "question" in client.system


def test_after_a_few_failed_asks_the_brain_is_told_to_guess_yes_or_no(store):
    brain = ScriptedBrain(ask("Who?"), ask("Who?"), ask("Who?"), ask("Mom?"), ask("Sara?"))

    for heard in ["call", "c", "cuh", "k", "no"]:
        hear(store, brain, heard)

    assert brain.modes == [AskMode.OPEN, AskMode.OPEN, AskMode.OPEN, AskMode.YES_NO, AskMode.YES_NO]


def test_the_threshold_is_a_setting(store):
    brain = ScriptedBrain(ask("Who?"), ask("Mom?"))

    hear(store, brain, "call")
    understand(
        brain,
        store,
        History(store, MockSummarizer(400), 10, 400),
        "demo",
        "user1",
        "c",
        5,
        Pacing(store, PauseSettings()),
        yes_no_after_tries=1,
    )

    assert brain.modes == [AskMode.OPEN, AskMode.YES_NO]


def test_the_mode_reaches_the_model(store):
    client = CapturingClient()

    hear(store, LlmBrain(client), "call")

    assert client.user["mode"] == AskMode.OPEN
    assert "yes_no" in client.system


def say(url, heard):
    async def run(client):
        return (await client.call_tool("understand_speech", {"heard": heard})).structured_content

    return with_client(url, run, token_for(url))


def test_over_mcp_alexa_guesses_and_a_yes_confirms_it(server):
    url = server()

    replies = [say(url, heard) for heard in ["call", "c", "cuh", "k", "yes", "yes"]]

    assert [reply["say"] for reply in replies[:4]] == [
        "Who do you want to call?",
        "Say the name once more?",
        "I didn't catch it. Who?",
        "Mom?",
    ]
    assert [reply["tries"] for reply in replies[:4]] == [1, 2, 3, 4]
    assert replies[4]["next_move"] == NextMove.CONFIRM
    assert replies[5]["next_move"] == NextMove.DONE
    assert replies[5]["details"] == {"who": "mom"}


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
