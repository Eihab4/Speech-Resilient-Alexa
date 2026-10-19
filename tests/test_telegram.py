import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.request import Request, urlopen

import pytest

from messages import ErrorMessage, Reply, TelegramText
from support import base_url, http, sign_up, token_for, with_client

CAIRO = {"latitude": 30.0444, "longitude": 31.2357}
BOT = "sra_test_bot"


class FakeTelegram:
    """The parts of the Telegram Bot API the server uses, on localhost, recording every call."""

    def __init__(self):
        self.calls, self.updates, self.failing = [], [], set()
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                method = self.path.rsplit("/", 1)[-1]
                params = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
                status, body = fake.answer(method, params)
                payload = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        Thread(target=self._server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self._server.server_port}"

    def answer(self, method, params):
        if method == "getUpdates":
            if not self.updates:
                time.sleep(0.2)
            updates, self.updates = self.updates, []
            return 200, {"ok": True, "result": updates}
        self.calls.append((method, params))
        if method in self.failing:
            return 400, {"ok": False, "description": "Bad Request: chat not found"}
        if method == "getMe":
            return 200, {"ok": True, "result": {"username": BOT}}
        return 200, {"ok": True, "result": {}}

    def sent(self, method):
        return [params for name, params in self.calls if name == method]

    def close(self):
        self._server.shutdown()


@pytest.fixture
def telegram():
    fake = FakeTelegram()
    yield fake
    fake.close()


@pytest.fixture
def linked_server(server, telegram):
    def start(**env):
        return server(TELEGRAM_BOT_TOKEN="test-token", TELEGRAM_API_URL=telegram.url, TELEGRAM_POLL_SECONDS="1", **env)

    return start


def wait_for(check, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if result := check():
            return result
        time.sleep(0.1)
    raise AssertionError("timed out")


def call(url, tool, user_id="user1", **arguments):
    async def run(client):
        return (await client.call_tool(tool, arguments)).structured_content

    return with_client(url, run, token_for(url, user_id))


def open_link(telegram, helper, chat_id=555, update_id=1):
    code = helper["link"].split("?start=")[1]
    telegram.updates.append({"update_id": update_id, "message": {"chat": {"id": chat_id}, "text": f"/start {code}"}})
    return wait_for(lambda: [m for m in telegram.sent("sendMessage") if m["chat_id"] == str(chat_id)])


def add_helper(url, token, name="Sara"):
    return http(f"{base_url(url)}/helpers", "POST", {"name": name}, token)


def test_a_new_helper_gets_a_link_to_the_bot(linked_server):
    url = linked_server()

    status, helper = add_helper(url, sign_up(url))

    assert status == 201
    assert helper["name"] == "Sara"
    assert helper["linked"] is False
    assert helper["link"].startswith(f"https://t.me/{BOT}?start=")


def test_opening_the_link_links_the_helper_and_the_bot_says_so(linked_server, telegram):
    url = linked_server()
    token = sign_up(url)
    _, helper = add_helper(url, token)

    [reply] = open_link(telegram, helper)
    _, listed = http(f"{base_url(url)}/helpers", token=token)

    assert reply["text"] == TelegramText.LINKED.format(name="Sara")
    assert listed == {"telegram": True, "helpers": [{"id": helper["id"], "name": "Sara", "linked": True, "link": None}]}


def test_a_wrong_link_links_nobody(linked_server, telegram):
    url = linked_server()
    token = sign_up(url)
    add_helper(url, token)

    telegram.updates.append({"update_id": 1, "message": {"chat": {"id": 777}, "text": "/start not-a-code"}})
    [reply] = wait_for(lambda: telegram.sent("sendMessage"))
    _, listed = http(f"{base_url(url)}/helpers", token=token)

    assert reply == {"chat_id": "777", "text": TelegramText.BAD_LINK}
    assert listed["helpers"][0]["linked"] is False


def test_the_alert_reaches_the_helper_on_telegram_with_a_map_pin(linked_server, telegram):
    url = linked_server()
    _, helper = add_helper(url, sign_up(url, "ahmed", "Ahmed"))
    open_link(telegram, helper)
    call(url, "understand_speech", user_id="ahmed", heard="I fell")

    result = call(url, "emergency_sos", user_id="ahmed", **CAIRO)
    alert = [m for m in telegram.sent("sendMessage") if m["text"].startswith("🚨")]

    assert result["sent_to"] == ["Sara"]
    assert alert[0]["chat_id"] == "555"
    assert alert[0]["text"].startswith('🚨 SOS from Ahmed.\nThey said: "I fell".')
    assert telegram.sent("sendLocation") == [{"chat_id": "555", **CAIRO}]


def test_a_missing_map_pin_still_counts_as_sent(linked_server, telegram):
    url = linked_server()
    _, helper = add_helper(url, sign_up(url))
    open_link(telegram, helper)
    telegram.failing.add("sendLocation")
    call(url, "understand_speech", user_id="ahmed", heard="I fell")

    assert call(url, "emergency_sos", user_id="ahmed", **CAIRO)["sent_to"] == ["Sara"]


def test_when_telegram_refuses_the_alert_alexa_says_so(linked_server, telegram):
    url = linked_server()
    _, helper = add_helper(url, sign_up(url))
    open_link(telegram, helper)
    telegram.failing.add("sendMessage")
    call(url, "understand_speech", user_id="ahmed", heard="I fell")

    assert call(url, "emergency_sos", user_id="ahmed", **CAIRO)["say"] == Reply.SOS_FAILED


def test_without_a_bot_token_helpers_get_no_link(server):
    url = server()
    token = sign_up(url)

    _, helper = add_helper(url, token)
    _, listed = http(f"{base_url(url)}/helpers", token=token)

    assert helper["link"] is None
    assert listed["telegram"] is False


def test_the_profile_is_saved_and_read_back(server):
    url = server()
    token = sign_up(url)

    saved = http(f"{base_url(url)}/profile", "PUT", {"name": " Ahmed ", "home_address": "12 Tahrir St"}, token)
    read = http(f"{base_url(url)}/profile", token=token)

    assert saved == (200, {"name": "Ahmed", "home_address": "12 Tahrir St"})
    assert read == (200, {"name": "Ahmed", "home_address": "12 Tahrir St"})


@pytest.mark.parametrize(("method", "path"), [("PUT", "/profile"), ("POST", "/helpers")])
def test_a_missing_name_is_refused(server, method, path):
    url = server()

    assert http(f"{base_url(url)}{path}", method, {"name": ""}, sign_up(url)) == (
        400,
        {"error": ErrorMessage.NAME_MISSING},
    )


def test_a_helper_can_only_be_removed_by_their_own_person(server):
    url = server()
    ahmed, sara = sign_up(url, "ahmed"), sign_up(url, "sara")
    _, helper = add_helper(url, ahmed, "Omar")
    remove = f"{base_url(url)}/helpers/{helper['id']}"

    assert http(remove, "DELETE", token=sara) == (404, {"error": ErrorMessage.HELPER_NOT_FOUND})
    assert http(remove, "DELETE", token=ahmed)[0] == 204
    assert http(f"{base_url(url)}/helpers", token=ahmed)[1]["helpers"] == []


def test_the_page_may_save_the_profile_from_another_port(server):
    request = Request(f"{base_url(server())}/profile", method="OPTIONS")
    request.add_header("Origin", "http://localhost:5180")
    request.add_header("Access-Control-Request-Method", "PUT")

    with urlopen(request, timeout=10) as response:
        assert "PUT" in response.headers["Access-Control-Allow-Methods"]
