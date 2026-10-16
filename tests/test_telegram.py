import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from messages import ErrorMessage, Reply, TelegramText
from support import with_client

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


def base(url):
    return url.removesuffix("/mcp")


def http(url, method="GET", body=None):
    request = Request(url, data=json.dumps(body).encode() if body is not None else None, method=method)
    request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read() or b"null")
    except HTTPError as error:
        return error.code, json.loads(error.read() or b"null")


def wait_for(check, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if result := check():
            return result
        time.sleep(0.1)
    raise AssertionError("timed out")


def call(url, tool, **arguments):
    async def run(client):
        return (await client.call_tool(tool, arguments)).structured_content

    return with_client(url, run)


def open_link(telegram, helper, chat_id=555, update_id=1):
    code = helper["link"].split("?start=")[1]
    telegram.updates.append({"update_id": update_id, "message": {"chat": {"id": chat_id}, "text": f"/start {code}"}})
    return wait_for(lambda: [m for m in telegram.sent("sendMessage") if m["chat_id"] == str(chat_id)])


def test_a_new_helper_gets_a_link_to_the_bot(linked_server):
    url = base(linked_server())

    status, helper = http(f"{url}/helpers", "POST", {"user_id": "u1", "name": "Sara"})

    assert status == 201
    assert helper["name"] == "Sara"
    assert helper["linked"] is False
    assert helper["link"].startswith(f"https://t.me/{BOT}?start=")


def test_opening_the_link_links_the_helper_and_the_bot_says_so(linked_server, telegram):
    url = base(linked_server())
    _, helper = http(f"{url}/helpers", "POST", {"user_id": "u1", "name": "Sara"})

    [reply] = open_link(telegram, helper)
    _, listed = http(f"{url}/helpers?user_id=u1")

    assert reply["text"] == TelegramText.LINKED.format(name="Sara")
    assert listed == {"telegram": True, "helpers": [{"id": helper["id"], "name": "Sara", "linked": True, "link": None}]}


def test_a_wrong_link_links_nobody(linked_server, telegram):
    url = base(linked_server())
    http(f"{url}/helpers", "POST", {"user_id": "u1", "name": "Sara"})

    telegram.updates.append({"update_id": 1, "message": {"chat": {"id": 777}, "text": "/start not-a-code"}})
    [reply] = wait_for(lambda: telegram.sent("sendMessage"))
    _, listed = http(f"{url}/helpers?user_id=u1")

    assert reply == {"chat_id": "777", "text": TelegramText.BAD_LINK}
    assert listed["helpers"][0]["linked"] is False


def test_the_alert_reaches_the_helper_on_telegram_with_a_map_pin(linked_server, telegram):
    url = linked_server()
    http(f"{base(url)}/profile", "PUT", {"user_id": "u1", "name": "Ahmed"})
    _, helper = http(f"{base(url)}/helpers", "POST", {"user_id": "u1", "name": "Sara"})
    open_link(telegram, helper)
    call(url, "understand_speech", user_id="u1", heard="I fell")

    result = call(url, "emergency_sos", user_id="u1", **CAIRO)
    alert = [m for m in telegram.sent("sendMessage") if m["text"].startswith("🚨")]

    assert result["sent_to"] == ["Sara"]
    assert alert[0]["chat_id"] == "555"
    assert alert[0]["text"].startswith('🚨 SOS from Ahmed.\nThey said: "I fell".')
    assert telegram.sent("sendLocation") == [{"chat_id": "555", **CAIRO}]


def test_a_missing_map_pin_still_counts_as_sent(linked_server, telegram):
    url = linked_server()
    _, helper = http(f"{base(url)}/helpers", "POST", {"user_id": "u1", "name": "Sara"})
    open_link(telegram, helper)
    telegram.failing.add("sendLocation")
    call(url, "understand_speech", user_id="u1", heard="I fell")

    assert call(url, "emergency_sos", user_id="u1", **CAIRO)["sent_to"] == ["Sara"]


def test_when_telegram_refuses_the_alert_alexa_says_so(linked_server, telegram):
    url = linked_server()
    _, helper = http(f"{base(url)}/helpers", "POST", {"user_id": "u1", "name": "Sara"})
    open_link(telegram, helper)
    telegram.failing.add("sendMessage")
    call(url, "understand_speech", user_id="u1", heard="I fell")

    assert call(url, "emergency_sos", user_id="u1", **CAIRO)["say"] == Reply.SOS_FAILED


def test_without_a_bot_token_helpers_get_no_link(server):
    url = base(server())

    _, helper = http(f"{url}/helpers", "POST", {"user_id": "u1", "name": "Sara"})
    _, listed = http(f"{url}/helpers?user_id=u1")

    assert helper["link"] is None
    assert listed["telegram"] is False


def test_the_profile_is_saved_and_read_back(server):
    url = base(server())

    saved = http(f"{url}/profile", "PUT", {"user_id": "u1", "name": " Ahmed ", "home_address": "12 Tahrir St"})
    read = http(f"{url}/profile?user_id=u1")

    assert saved == (200, {"name": "Ahmed", "home_address": "12 Tahrir St"})
    assert read == (200, {"name": "Ahmed", "home_address": "12 Tahrir St"})


@pytest.mark.parametrize(
    ("method", "path", "body", "error"),
    [
        ("PUT", "/profile", {"user_id": "u1", "name": ""}, ErrorMessage.NAME_MISSING),
        ("POST", "/helpers", {"user_id": "", "name": "Sara"}, ErrorMessage.USER_ID_MISSING),
        ("GET", "/helpers", None, ErrorMessage.USER_ID_MISSING),
        ("GET", "/profile", None, ErrorMessage.USER_ID_MISSING),
    ],
)
def test_missing_fields_are_refused(server, method, path, body, error):
    assert http(f"{base(server())}{path}", method, body) == (400, {"error": error})


def test_a_helper_can_only_be_removed_by_their_own_person(server):
    url = base(server())
    _, helper = http(f"{url}/helpers", "POST", {"user_id": "u1", "name": "Sara"})

    assert http(f"{url}/helpers/{helper['id']}?user_id=u2", "DELETE") == (404, {"error": ErrorMessage.HELPER_NOT_FOUND})
    assert http(f"{url}/helpers/{helper['id']}?user_id=u1", "DELETE")[0] == 204
    assert http(f"{url}/helpers?user_id=u1")[1]["helpers"] == []


def test_the_page_may_save_the_profile_from_another_port(server):
    request = Request(f"{base(server())}/profile", method="OPTIONS")
    request.add_header("Origin", "http://localhost:5180")
    request.add_header("Access-Control-Request-Method", "PUT")

    with urlopen(request, timeout=10) as response:
        assert "PUT" in response.headers["Access-Control-Allow-Methods"]
