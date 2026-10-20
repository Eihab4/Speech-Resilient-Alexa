import pytest

from brain.schemas import BrainResult
from brain.summarizer import MockSummarizer
from config.settings import PauseSettings
from enums import AlertKind, AlertStatus, AskMode, NextMove, RequestStatus
from memory import Helper, History, SqliteMemoryStore
from messages import Reply
from pacing import Pacing
from test_emergency_sos import CAIRO, call, set_up
from test_notify_helpers import FailingNotifier
from tools.ask_for_help import ask_for_help, asks_for_help
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


def hear(store, brain, heard, help_after_tries=5):
    history = History(store, MockSummarizer(400), recent_messages=10, summary_trigger_words=400)
    return understand(
        brain,
        store,
        history,
        "demo",
        "user1",
        heard,
        countdown_seconds=5,
        pacing=Pacing(store, PauseSettings()),
        help_after_tries=help_after_tries,
    )


def ask(question):
    return BrainResult(intent="call", next_move=NextMove.ASK, say=question)


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


def test_after_too_many_questions_alexa_asks_the_helper_once(store):
    brain = ScriptedBrain(*(ask(f"Question {n}?") for n in range(1, 6)))

    replies = [hear(store, brain, piece, help_after_tries=3) for piece in ["c", "cuh", "k", "ca", "caw"]]
    conversation = store.conversation_for("demo", "user1")
    turns = store.turns(conversation, replies[0]["pending_id"])

    assert [reply["next_move"] for reply in replies] == [NextMove.ASK] * 2 + [NextMove.HELP] + [NextMove.ASK] * 2
    assert replies[2]["say"] == Reply.HELP_STUCK
    assert [reply["tries"] for reply in replies] == [1, 2, 3, 4, 5]
    assert [turn.next_move for turn in turns][2] == NextMove.HELP
    assert turns[2].say == "Question 3?"


def say(url, heard):
    return call(url, "understand_speech", heard=heard)


def test_the_helper_gets_what_was_understood_and_alexa_repeats_her_question(server, store):
    url = server()
    set_up(store, Helper(name="Sara", telegram_chat_id="1"), url=url)
    question = say(url, "tomorrow")
    assert say(url, "help")["next_move"] == NextMove.HELP

    result = call(url, "ask_for_help")
    [alert] = store.alerts("demo", "user1")

    assert result == {
        "sent": True,
        "sent_to": ["Sara"],
        "say": f"{Reply.HELP_SENT.format(who='Sara')} {question['say']}",
    }
    assert alert.kind == AlertKind.HELP
    assert alert.status == AlertStatus.SENT
    assert alert.text.startswith(
        'Ahmed asked Alexa for help.\nUnderstood so far: reminder, when: tomorrow.\nThey said: "tomorrow".'
    )
    assert say(url, "doctor ten")["next_move"] == NextMove.CONFIRM


def test_when_alexa_gives_up_the_helper_is_told_how_many_questions_it_took(server, store):
    url = server(HELP_AFTER_TRIES="2")
    set_up(store, Helper(name="Sara", telegram_chat_id="1"), url=url)
    say(url, "blah")
    stuck = say(url, "blah")

    result = call(url, "ask_for_help")
    [alert] = store.alerts("demo", "user1")

    assert stuck["next_move"] == NextMove.HELP
    assert result["say"] == f"{Reply.HELP_SENT.format(who='Sara')} What would you like me to do?"
    assert alert.text.startswith(
        'Alexa couldn\'t understand Ahmed after 2 questions.\nNothing was understood yet.\nThey said: "blah … blah".'
    )


def test_a_help_message_does_not_delay_a_later_emergency_alert(server, store):
    url = server()
    set_up(store, Helper(name="Sara", telegram_chat_id="1"), url=url)
    say(url, "help")
    call(url, "ask_for_help")
    say(url, "I fell")

    assert call(url, "emergency_sos", **CAIRO)["sent"] is True


def test_without_a_linked_helper_alexa_says_so_and_stays(store):
    store.start_conversation("demo", "user1")

    result = ask_for_help(store, FailingNotifier(set()), "demo", "user1")

    assert result == {"sent": False, "sent_to": [], "say": f"{Reply.HELP_NO_HELPER} {Reply.HELP_HERE}"}
    assert store.alerts("demo", "user1")[0].status == AlertStatus.NO_HELPER


def test_when_no_helper_can_be_reached_alexa_says_so(store):
    store.start_conversation("demo", "user1")
    store.add_helper("demo", "user1", Helper(name="Sara", telegram_chat_id="1"))

    result = ask_for_help(store, FailingNotifier({"Sara"}), "demo", "user1")

    assert result["say"] == f"{Reply.HELP_FAILED} {Reply.HELP_HERE}"
