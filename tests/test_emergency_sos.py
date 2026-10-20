import pytest

from config.settings import SosSettings
from enums import AlertStatus, NextMove, RequestStatus
from location import NoGeocoder
from memory import Helper, Profile, SqliteMemoryStore
from messages import Reply
from support import token_for, with_client
from tools.emergency_sos import asks_for_sos, emergency_sos, says_stop

CAIRO = {"latitude": 30.0444, "longitude": 31.2357}


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "memory.db"


@pytest.fixture
def store(db_path):
    store = SqliteMemoryStore(db_path)
    yield store
    store.close()


def call(url, tool, user_id="user1", **arguments):
    async def run(client):
        return (await client.call_tool(tool, arguments)).structured_content

    return with_client(url, run, token_for(url, user_id))


def say(url, heard):
    return call(url, "understand_speech", user_id="user1", heard=heard)


def sos(url, **position):
    return call(url, "emergency_sos", user_id="user1", **position)


def set_up(store, *helpers, url=None, name="Ahmed", home_address=None):
    if url:
        token_for(url)
    store.save_profile("demo", "user1", Profile(name=name, home_address=home_address))
    for helper in helpers:
        store.add_helper("demo", "user1", helper)


class FailingNotifier:
    def __init__(self, failing):
        self.failing, self.reached = failing, []

    def notify(self, helper, text, position=None):
        if helper.name in self.failing:
            raise ConnectionError(helper.name)
        self.reached.append(helper.name)


@pytest.mark.parametrize(
    "heard",
    ["I fell", "uh… i fell… floor", "help help", "Help, help me", "EMERGENCY!", "call an ambulance", "I fall down"],
)
def test_sos_words_are_found_even_in_broken_speech(heard):
    assert asks_for_sos(heard)


@pytest.mark.parametrize("heard", ["help", "help me", "call mom", "I feel tired", "tomorrow doctor ten", "fellow"])
def test_a_single_help_or_everyday_words_are_not_sos(heard):
    assert not asks_for_sos(heard)


@pytest.mark.parametrize("heard", ["stop", "Stop.", "I'm okay", "I’m fine", "never mind", "don't send"])
def test_stop_words_are_found(heard):
    assert says_stop(heard)


@pytest.mark.parametrize("heard", ["okay", "yes", "no", "stop calling mom", "help"])
def test_a_yes_or_a_no_is_not_a_stop(heard):
    assert not says_stop(heard)


def test_sos_words_start_the_countdown(server):
    result = say(server(SOS_COUNTDOWN_SECONDS="7"), "uh… I fell")

    assert result["next_move"] == NextMove.SOS
    assert result["countdown_seconds"] == 7
    assert result["say"] == Reply.SOS_COUNTDOWN.format(seconds=7)


def test_sos_works_while_the_brain_is_down(server):
    url = server(LLM_PROVIDER="openrouter", OPENROUTER_API_KEY="invalid", OPENROUTER_BASE_URL="http://127.0.0.1:9/v1")

    async def broken_brain(client):
        return await client.call_tool("understand_speech", {"heard": "call mom"}, raise_on_error=False)

    assert with_client(url, broken_brain, token_for(url)).is_error
    assert say(url, "I fell")["next_move"] == NextMove.SOS


def test_stop_during_the_countdown_goes_back_to_the_open_request(server, db_path):
    url = server()
    question = say(url, "call mom")
    say(url, "help help")

    stopped = say(url, "I'm okay")
    store = SqliteMemoryStore(db_path)
    conversation = store.conversation_for("demo", "user1")
    request, pieces = store.pending_request(conversation), store.turns(conversation, question["pending_id"])
    store.close()

    assert stopped["next_move"] == NextMove.CONFIRM
    assert stopped["say"] == Reply.SOS_STOPPED_BACK.format(question=question["say"])
    assert request.status == RequestStatus.PENDING
    assert [turn.heard for turn in pieces] == ["call mom"]
    assert say(url, "yes")["next_move"] == NextMove.DONE


def test_stop_with_nothing_open_just_listens(server):
    url = server()
    say(url, "I fell")

    stopped = say(url, "stop")

    assert stopped["next_move"] == NextMove.LISTEN
    assert stopped["say"] == Reply.SOS_STOPPED


@pytest.mark.parametrize("heard", ["okay", "please hurry", "help help"])
def test_anything_but_stop_keeps_the_countdown_going(server, heard):
    url = server()
    say(url, "I fell")

    result = say(url, heard)

    assert result["next_move"] == NextMove.SOS
    assert result["say"] == Reply.SOS_KEEP_CALM


def test_the_alert_reaches_every_linked_helper_with_the_map(server, store):
    url = server()
    set_up(
        store,
        Helper(name="Sara", telegram_chat_id="1"),
        Helper(name="Omar", telegram_chat_id="2"),
        Helper(name="Mona"),
        url=url,
    )
    say(url, "I fell")
    say(url, "please hurry")

    result = sos(url, **CAIRO)
    [alert] = store.alerts("demo", "user1")

    assert result == {"sent": True, "sent_to": ["Sara", "Omar"], "say": Reply.SOS_SENT.format(who="Sara and Omar")}
    assert alert.status == AlertStatus.SENT
    assert alert.heard == "I fell … please hurry"
    assert alert.text.startswith('🚨 SOS from Ahmed.\nThey said: "I fell … please hurry".')
    assert "https://maps.google.com/?q=30.0444,31.2357" in alert.text


def test_after_the_alert_the_next_words_are_heard_as_usual(server, store):
    url = server()
    set_up(store, Helper(name="Sara", telegram_chat_id="1"), url=url)
    say(url, "I fell")
    sos(url, **CAIRO)

    assert say(url, "call mom")["next_move"] == NextMove.CONFIRM


def test_without_a_location_the_alert_gives_the_home_address(server, store):
    url = server()
    set_up(store, Helper(name="Sara", telegram_chat_id="1"), home_address="12 Tahrir St, Cairo", url=url)
    say(url, "emergency")

    result = sos(url)
    [alert] = store.alerts("demo", "user1")

    assert result["say"] == Reply.SOS_SENT_NO_PLACE.format(who="Sara")
    assert "Home address: 12 Tahrir St, Cairo" in alert.text


def test_with_no_place_at_all_the_alert_says_so(server, store):
    url = server()
    set_up(store, Helper(name="Sara", telegram_chat_id="1"), url=url)
    say(url, "emergency")

    sos(url)

    assert "Location unknown." in store.alerts("demo", "user1")[0].text


def test_the_same_alert_is_not_sent_twice_in_a_row(server, store):
    url = server(SOS_COOLDOWN_MINUTES="2")
    set_up(store, Helper(name="Sara", telegram_chat_id="1"), url=url)
    say(url, "I fell")
    sos(url, **CAIRO)
    say(url, "I fell")

    again = sos(url, **CAIRO)

    assert again == {"sent": False, "sent_to": [], "say": Reply.SOS_ALREADY_SENT}
    assert len(store.alerts("demo", "user1")) == 1


def test_with_no_linked_helper_alexa_says_so(server, store):
    url = server()
    set_up(store, Helper(name="Mona"), url=url)
    say(url, "I fell")

    result = sos(url, **CAIRO)

    assert result == {"sent": False, "sent_to": [], "say": Reply.SOS_NO_HELPER}
    assert store.alerts("demo", "user1")[0].status == AlertStatus.NO_HELPER


def test_one_failing_helper_does_not_stop_the_others(store):
    set_up(store, Helper(name="Sara", telegram_chat_id="1"), Helper(name="Omar", telegram_chat_id="2"))
    notifier = FailingNotifier(failing={"Sara"})

    result = emergency_sos(store, notifier, NoGeocoder(), SosSettings(), "demo", "user1", **CAIRO)

    assert result["sent_to"] == ["Omar"]
    assert notifier.reached == ["Omar"]


def test_when_every_helper_fails_alexa_says_so(store):
    set_up(store, Helper(name="Sara", telegram_chat_id="1"))

    result = emergency_sos(
        store, FailingNotifier(failing={"Sara"}), NoGeocoder(), SosSettings(), "demo", "user1", **CAIRO
    )

    assert result == {"sent": False, "sent_to": [], "say": Reply.SOS_FAILED}
    assert store.alerts("demo", "user1")[0].status == AlertStatus.FAILED


def test_a_failed_alert_can_be_tried_again_at_once(store):
    set_up(store, Helper(name="Sara", telegram_chat_id="1"))
    emergency_sos(store, FailingNotifier(failing={"Sara"}), NoGeocoder(), SosSettings(), "demo", "user1", **CAIRO)

    retry = emergency_sos(store, FailingNotifier(failing=set()), NoGeocoder(), SosSettings(), "demo", "user1", **CAIRO)

    assert retry["sent_to"] == ["Sara"]


class FakeGeocoder:
    def __init__(self, address):
        self.answer, self.asked = address, []

    def address(self, position):
        self.asked.append(position)
        return self.answer


def test_the_alert_gives_the_address_amazon_location_found(store):
    set_up(store, Helper(name="Sara", telegram_chat_id="1"))
    geocoder = FakeGeocoder("Tahrir Square, Cairo, Egypt")

    emergency_sos(store, FailingNotifier(failing=set()), geocoder, SosSettings(), "demo", "user1", **CAIRO)
    [alert] = store.alerts("demo", "user1")

    assert "Where: Tahrir Square, Cairo, Egypt\nMap: https://maps.google.com/?q=30.0444,31.2357" in alert.text
    assert alert.address == "Tahrir Square, Cairo, Egypt"


def test_without_an_address_the_alert_still_goes_with_the_map(store):
    set_up(store, Helper(name="Sara", telegram_chat_id="1"))

    result = emergency_sos(
        store, FailingNotifier(failing=set()), FakeGeocoder(None), SosSettings(), "demo", "user1", **CAIRO
    )
    [alert] = store.alerts("demo", "user1")

    assert result["sent_to"] == ["Sara"]
    assert "Where:" not in alert.text
    assert "Map: https://maps.google.com/?q=30.0444,31.2357" in alert.text


def test_no_position_means_no_address_lookup(store):
    set_up(store, Helper(name="Sara", telegram_chat_id="1"))
    geocoder = FakeGeocoder("anywhere")

    emergency_sos(store, FailingNotifier(failing=set()), geocoder, SosSettings(), "demo", "user1")

    assert geocoder.asked == []
