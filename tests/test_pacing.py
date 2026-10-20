import pytest

from brain.schemas import BrainResult
from brain.summarizer import MockSummarizer
from config.settings import PauseSettings
from enums import NextMove
from memory import History, SqliteMemoryStore
from pacing import Pacing, wait_from_pauses
from support import base_url, http, sign_up, token_for, with_client
from tools.understand_speech import understand

SETTINGS = PauseSettings(
    start_seconds=2,
    min_seconds=1.5,
    max_seconds=6,
    step_seconds=0.5,
    ignore_over_seconds=10,
    keep=20,
    min_samples=5,
    margin=1.2,
)


@pytest.fixture
def store(tmp_path):
    store = SqliteMemoryStore(tmp_path / "memory.db")
    yield store
    store.close()


class RunNow:
    def __init__(self, target, args=(), daemon=None):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)

    def join(self, timeout=None):
        pass


@pytest.fixture(autouse=True)
def tidy_history_in_line(monkeypatch):
    monkeypatch.setattr("memory.history.Thread", RunNow)


class ScriptedBrain:
    """Answers "go on" until the request has a who, then asks to confirm."""

    def interpret(self, fragments, history="", person=""):
        if "mom" in " ".join(fragments):
            return BrainResult(intent="call", details={"who": "mom"}, next_move=NextMove.CONFIRM, say="Call Mom?")
        return BrainResult(next_move=NextMove.LISTEN, say="Mm-hm, go on.")


def hear(store, heard, pauses_ms=None):
    history = History(store, MockSummarizer(400), recent_messages=10, summary_trigger_words=400)
    pacing = Pacing(store, SETTINGS)
    return understand(ScriptedBrain(), store, history, "demo", "u1", heard, 5, pacing, pauses_ms)


def test_until_there_are_enough_pauses_there_is_no_measured_wait():
    assert wait_from_pauses([2000, 2500, 3000, 2200], SETTINGS) is None


def test_the_wait_covers_three_in_four_pauses_with_a_margin():
    # 75th percentile of 2.0 to 3.0 s is 2.75 s; with the 1.2 margin, 3.3 s.
    assert wait_from_pauses([2000, 2250, 2500, 2750, 3000], SETTINGS) == 3.3


def test_one_odd_long_pause_does_not_slow_alexa_down():
    usual = [2000, 2250, 2500, 2750, 3000]

    assert wait_from_pauses([*usual, 9500], SETTINGS) == wait_from_pauses(usual, SETTINGS)


def test_pauses_over_the_limit_are_not_pauses_in_a_sentence():
    assert wait_from_pauses([2000, 2000, 2000, 2000, 15000, 30000], SETTINGS) is None


@pytest.mark.parametrize(("pauses", "wait"), [([400] * 5, 1.5), ([5800] * 5, 6)])
def test_the_wait_stays_within_its_limits(pauses, wait):
    assert wait_from_pauses(pauses, SETTINGS) == wait


def test_a_new_person_starts_at_the_default_wait(store):
    assert Pacing(store, SETTINGS).wait("demo", "u1") == 2


def test_each_early_answer_adds_to_the_wait_up_to_the_limit(store):
    pacing = Pacing(store, SETTINGS)

    waits = [pacing.learn("demo", "u1", [], answered_too_early=True) for _ in range(12)]

    assert waits[:3] == [2.5, 3, 3.5]
    assert waits[-1] == 6
    assert pacing.wait("demo", "u1") == 6


def test_measured_pauses_take_over_from_early_answers(store):
    pacing = Pacing(store, SETTINGS)
    for _ in range(4):
        pacing.learn("demo", "u1", [], answered_too_early=True)

    wait = pacing.learn("demo", "u1", [2000, 2250, 2500, 2750, 3000], answered_too_early=True)

    assert wait == 3.3


def test_only_the_latest_pauses_count(store):
    pacing = Pacing(store, SETTINGS)
    pacing.learn("demo", "u1", [5000] * 20, answered_too_early=False)

    assert pacing.learn("demo", "u1", [2000] * 20, answered_too_early=False) == 2.4


def test_going_on_after_alexa_said_go_on_means_she_answered_too_early(store):
    first = hear(store, "call")
    second = hear(store, "mom")

    assert first["next_move"] == NextMove.LISTEN
    assert first["wait_seconds"] == 2
    assert second["wait_seconds"] == 2.5


def test_a_new_request_after_a_finished_one_is_not_counted_as_early(store):
    hear(store, "call mom")

    assert hear(store, "call")["wait_seconds"] == 2


def test_the_pauses_the_host_measured_are_learned(store):
    result = hear(store, "call mom", pauses_ms=[2000, 2250, 2500, 2750, 3000])

    assert result["wait_seconds"] == 3.3
    assert store.recent_pauses("demo", "u1", 20) == [3000, 2750, 2500, 2250, 2000]


def test_every_reply_over_mcp_says_how_long_to_wait(server):
    url = server()

    async def turn(client):
        result = await client.call_tool(
            "understand_speech", {"heard": "call mom", "pauses_ms": [2000, 2250, 2500, 2750, 3000]}
        )
        return result.structured_content

    assert with_client(url, turn, token_for(url))["wait_seconds"] == 3.3


def test_signing_in_tells_the_page_the_persons_wait(server):
    url = server()
    token = sign_up(url)

    assert http(f"{base_url(url)}/me", token=token)[1]["wait_seconds"] == 2
