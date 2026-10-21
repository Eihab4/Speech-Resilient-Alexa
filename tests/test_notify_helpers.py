import pytest

from enums import AlertStatus
from memory import Helper, SqliteMemoryStore
from notify import linked_helpers, names, outcome, reach


class FailingNotifier:
    def __init__(self, failing):
        self.failing, self.reached = failing, []

    def notify(self, helper, text, position=None):
        if helper.name in self.failing:
            raise ConnectionError(helper.name)
        self.reached.append((helper.name, text))


@pytest.fixture
def store(tmp_path):
    store = SqliteMemoryStore(tmp_path / "memory.db")
    yield store
    store.close()


def test_only_helpers_who_opened_their_link_are_reached(store):
    store.add_helper("demo", "user1", Helper(name="Sara", telegram_chat_id="1"))
    store.add_helper("demo", "user1", Helper(name="Mona"))

    assert [helper.name for helper in linked_helpers(store, "demo", "user1")] == ["Sara"]


def test_one_failing_channel_does_not_stop_the_others():
    notifier = FailingNotifier(failing={"Omar"})
    helpers = [Helper(name="Sara", telegram_chat_id="1"), Helper(name="Omar", telegram_chat_id="2")]

    assert reach(notifier, helpers, "hi") == ["Sara"]
    assert notifier.reached == [("Sara", "hi")]


@pytest.mark.parametrize(
    ("helpers", "sent_to", "status"),
    [
        ([], [], AlertStatus.NO_HELPER),
        ([Helper(name="Sara")], [], AlertStatus.FAILED),
        ([Helper(name="Sara")], ["Sara"], AlertStatus.SENT),
    ],
)
def test_the_outcome_says_whether_anyone_got_it(helpers, sent_to, status):
    assert outcome(helpers, sent_to) == status


@pytest.mark.parametrize(("sent_to", "said"), [(["Sara"], "Sara"), (["Sara", "Omar", "Mona"], "Sara, Omar and Mona")])
def test_names_read_like_a_sentence(sent_to, said):
    assert names(sent_to) == said
