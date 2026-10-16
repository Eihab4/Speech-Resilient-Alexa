import json
import logging
from threading import Event
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config.settings import TelegramSettings
from memory import Helper, MemoryStore
from messages import ErrorMessage, LogMessage, TelegramText
from notify.base import Position

logger = logging.getLogger(__name__)

USER_AGENT = "speech-resilient-alexa/0.1"
# How long to wait before asking Telegram again after it could not be reached.
RETRY_SECONDS = 5


class TelegramError(RuntimeError):
    pass


class TelegramBot:
    """Plain HTTPS calls to the Telegram Bot API. The token is part of every URL, so URLs are never logged."""

    def __init__(self, settings: TelegramSettings) -> None:
        self._settings = settings
        self._base = f"{settings.api_url.rstrip('/')}/bot{settings.bot_token.get_secret_value()}"
        self._username: str | None = None

    def call(self, method: str, params: dict[str, Any] | None = None, wait: float | None = None) -> Any:
        request = Request(
            f"{self._base}/{method}",
            data=json.dumps(params or {}).encode(),
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
            method="POST",
        )
        try:
            with urlopen(request, timeout=wait or self._settings.timeout_seconds) as response:
                body = json.loads(response.read().decode())
        except HTTPError as error:
            detail = error.read().decode()
            raise TelegramError(ErrorMessage.TELEGRAM_FAILED.format(method=method, detail=detail)) from None
        except (URLError, TimeoutError) as error:
            raise TelegramError(ErrorMessage.TELEGRAM_UNREACHABLE.format(method=method)) from error
        if not body.get("ok"):
            detail = body.get("description", "")
            raise TelegramError(ErrorMessage.TELEGRAM_FAILED.format(method=method, detail=detail))
        return body["result"]

    def username(self) -> str:
        """The bot's @name, for the links helpers open. Asked once, then remembered."""
        if self._username is None:
            self._username = self.call("getMe")["username"]
        return self._username

    def send_message(self, chat_id: str, text: str) -> None:
        self.call("sendMessage", {"chat_id": chat_id, "text": text})

    def send_location(self, chat_id: str, position: Position) -> None:
        self.call("sendLocation", {"chat_id": chat_id, "latitude": position.latitude, "longitude": position.longitude})

    def updates(self, offset: int | None) -> list[dict[str, Any]]:
        """New messages to the bot. Waits on Telegram's side until one comes or poll_seconds pass."""
        poll = self._settings.poll_seconds
        params = {"offset": offset, "timeout": poll, "allowed_updates": ["message"]}
        return self.call("getUpdates", params, wait=poll + self._settings.timeout_seconds)


class TelegramNotifier:
    def __init__(self, bot: TelegramBot) -> None:
        self._bot = bot

    def notify(self, helper: Helper, text: str, position: Position | None = None) -> None:
        self._bot.send_message(helper.telegram_chat_id, text)
        if position is None:
            return
        # The message already says where; a missing pin must not count the alert as failed.
        try:
            self._bot.send_location(helper.telegram_chat_id, position)
        except TelegramError:
            logger.exception(LogMessage.TELEGRAM_PIN_FAILED.format(helper=helper.name))


class HelperLinker:
    """Links a helper to their Telegram chat when they open their link, which sends the bot /start <link_code>."""

    def __init__(self, bot: TelegramBot, store: MemoryStore) -> None:
        self._bot = bot
        self._store = store

    def handle(self, update: dict[str, Any]) -> None:
        message = update.get("message") or {}
        chat_id = (message.get("chat") or {}).get("id")
        words = (message.get("text") or "").split()
        if chat_id is None or not words or words[0] != "/start":
            return
        helper = self._store.link_helper(words[1], str(chat_id)) if len(words) == 2 else None
        reply = TelegramText.LINKED.format(name=helper.name) if helper else TelegramText.BAD_LINK
        self._bot.send_message(str(chat_id), reply)

    def run(self, stop: Event) -> None:
        offset = None
        while not stop.is_set():
            try:
                updates = self._bot.updates(offset)
            except TelegramError:
                logger.exception(LogMessage.TELEGRAM_UPDATES_FAILED)
                stop.wait(RETRY_SECONDS)
                continue
            for update in updates:
                offset = update["update_id"] + 1
                try:
                    self.handle(update)
                except Exception:
                    logger.exception(LogMessage.TELEGRAM_UPDATE_FAILED)
