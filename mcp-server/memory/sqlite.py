import json
import sqlite3
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from threading import RLock

from enums import AlertStatus, Intent, RequestStatus
from memory.models import Action, Alert, Helper, Profile, Request, Summary, Turn
from utils import hours_ago, utc_now

SCHEMA = (Path(__file__).parent / "schema.sql").read_text()
HELPER_COLUMNS = "h.id, h.name, h.link_code, h.telegram_chat_id, h.linked_at, h.created_at"
ALERT_COLUMNS = "a.id, a.heard, a.latitude, a.longitude, a.address, a.text, a.status, a.created_at"
OF_USER = "JOIN users u ON u.id = {table}.user_id WHERE u.company_id = ? AND u.external_id = ?"


def _one_call_at_a_time(cls):
    """Runs every public method under the store's lock. The MCP tools (in a thread pool), the history
    tidy-up and the Telegram bot share one connection, and SQLite must not see two of them at once."""

    def locked(method):
        @wraps(method)
        def call(self, *args, **kwargs):
            with self._lock:
                return method(self, *args, **kwargs)

        return call

    for name, member in list(vars(cls).items()):
        if callable(member) and not name.startswith("_"):
            setattr(cls, name, locked(member))
    return cls


@_one_call_at_a_time
class SqliteMemoryStore:
    def __init__(self, db_path: Path, unfinished_ttl_hours: float = 24) -> None:
        self._ttl_hours = unfinished_ttl_hours
        # Re-entrant, because some methods call others.
        self._lock = RLock()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(db_path, autocommit=True, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.executescript(SCHEMA)
        self._repair_older_files()

    def _repair_older_files(self) -> None:
        columns = {row["name"] for row in self._db.execute("PRAGMA table_info(sessions)")}
        if "expires_at" not in columns:
            self._db.execute("ALTER TABLE sessions ADD COLUMN expires_at TEXT NOT NULL DEFAULT ''")
        placeholders = ", ".join("?" * len(Intent))
        self._db.execute(f"UPDATE requests SET intent = NULL WHERE intent NOT IN ({placeholders})", list(Intent))

    @contextmanager
    def _transaction(self):
        self._db.execute("BEGIN")
        try:
            yield
        except BaseException:
            self._db.execute("ROLLBACK")
            raise
        self._db.execute("COMMIT")

    def start_conversation(self, company_id: str, user_id: str) -> int:
        with self._transaction():
            self._db.execute("INSERT OR IGNORE INTO companies (id) VALUES (?)", (company_id,))
            self._db.execute(
                "INSERT OR IGNORE INTO users (company_id, external_id) VALUES (?, ?)", (company_id, user_id)
            )
            row = self._db.execute(
                "INSERT INTO conversations (user_id, started_at) "
                "SELECT id, ? FROM users WHERE company_id = ? AND external_id = ? RETURNING id",
                (utc_now(), company_id, user_id),
            ).fetchone()
        return row["id"]

    def conversation_for(self, company_id: str, user_id: str) -> int:
        row = self._db.execute(
            "SELECT c.id FROM conversations c JOIN users u ON u.id = c.user_id "
            "WHERE u.company_id = ? AND u.external_id = ? ORDER BY c.id DESC LIMIT 1",
            (company_id, user_id),
        ).fetchone()
        return row["id"] if row else self.start_conversation(company_id, user_id)

    def add_turn(self, conversation_id: int, turn: Turn) -> Turn:
        row = self._db.execute(
            "INSERT INTO turns (conversation_id, request_id, seq, heard, say, next_move, created_at) VALUES "
            "(?, ?, (SELECT COALESCE(MAX(seq), 0) + 1 FROM turns WHERE conversation_id = ?), ?, ?, ?, ?) "
            "RETURNING seq, request_id, heard, say, next_move, created_at",
            (conversation_id, turn.request_id, conversation_id, turn.heard, turn.say, turn.next_move, turn.created_at),
        ).fetchone()
        return Turn(**row)

    def turns(self, conversation_id: int, request_id: str | None = None) -> list[Turn]:
        rows = self._db.execute(
            "SELECT seq, request_id, heard, say, next_move, created_at FROM turns "
            "WHERE conversation_id = ? AND (? IS NULL OR request_id = ?) ORDER BY seq",
            (conversation_id, request_id, request_id),
        )
        return [Turn(**row) for row in rows]

    def last_turn(self, conversation_id: int) -> Turn | None:
        row = self._db.execute(
            "SELECT seq, request_id, heard, say, next_move, created_at FROM turns "
            "WHERE conversation_id = ? ORDER BY seq DESC LIMIT 1",
            (conversation_id,),
        ).fetchone()
        return Turn(**row) if row else None

    def finished_turns(self, conversation_id: int, after_seq: int) -> list[Turn]:
        rows = self._db.execute(
            "SELECT t.seq, t.request_id, t.heard, t.say, t.next_move, t.created_at, r.status AS request_status "
            "FROM turns t JOIN requests r ON r.id = t.request_id "
            "WHERE t.conversation_id = ? AND t.seq > ? AND r.status IN (?, ?, ?) ORDER BY t.seq",
            (conversation_id, after_seq, RequestStatus.DONE, RequestStatus.CANCELLED, RequestStatus.REPLACED),
        )
        return [Turn(**row) for row in rows]

    def summary(self, conversation_id: int) -> Summary:
        row = self._db.execute(
            "SELECT text, covers_up_to_seq FROM summaries WHERE conversation_id = ?", (conversation_id,)
        ).fetchone()
        return Summary(**row) if row else Summary()

    def save_summary(self, conversation_id: int, summary: Summary) -> None:
        self._db.execute(
            "INSERT INTO summaries (conversation_id, text, covers_up_to_seq, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (conversation_id) DO UPDATE SET text = excluded.text, "
            "covers_up_to_seq = excluded.covers_up_to_seq, updated_at = excluded.updated_at",
            (conversation_id, summary.text, summary.covers_up_to_seq, utc_now()),
        )

    def save_request(self, conversation_id: int, request: Request) -> None:
        self._db.execute(
            "INSERT INTO requests (id, conversation_id, intent, details, status, updated_at) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (id) DO UPDATE SET intent = excluded.intent, details = excluded.details, "
            "status = excluded.status, updated_at = excluded.updated_at",
            (request.id, conversation_id, request.intent, json.dumps(request.details), request.status, utc_now()),
        )

    def pending_request(self, conversation_id: int) -> Request | None:
        row = self._db.execute(
            "SELECT id, intent, details, status, updated_at FROM requests "
            "WHERE conversation_id = ? AND status IN (?, ?) AND updated_at >= ? ORDER BY updated_at DESC LIMIT 1",
            (conversation_id, RequestStatus.PENDING, RequestStatus.CONFIRMED, hours_ago(self._ttl_hours)),
        ).fetchone()
        return self._request(row)

    def request(self, conversation_id: int, request_id: str) -> Request | None:
        row = self._db.execute(
            "SELECT id, intent, details, status, updated_at FROM requests WHERE conversation_id = ? AND id = ?",
            (conversation_id, request_id),
        ).fetchone()
        return self._request(row)

    @staticmethod
    def _request(row: sqlite3.Row | None) -> Request | None:
        return Request(**{**row, "details": json.loads(row["details"])}) if row else None

    def log_action(self, request_id: str, result: str) -> Action:
        row = self._db.execute(
            "INSERT INTO actions (request_id, result, created_at) VALUES (?, ?, ?) RETURNING request_id, result, created_at",
            (request_id, result, utc_now()),
        ).fetchone()
        return Action(**row)

    def actions(self, conversation_id: int) -> list[Action]:
        rows = self._db.execute(
            "SELECT a.request_id, a.result, a.created_at FROM actions a JOIN requests r ON r.id = a.request_id "
            "WHERE r.conversation_id = ? ORDER BY a.id",
            (conversation_id,),
        )
        return [Action(**row) for row in rows]

    def _user_id(self, company_id: str, user_id: str) -> int:
        with self._transaction():
            self._db.execute("INSERT OR IGNORE INTO companies (id) VALUES (?)", (company_id,))
            self._db.execute(
                "INSERT OR IGNORE INTO users (company_id, external_id) VALUES (?, ?)", (company_id, user_id)
            )
            row = self._db.execute(
                "SELECT id FROM users WHERE company_id = ? AND external_id = ?", (company_id, user_id)
            ).fetchone()
        return row["id"]

    def save_profile(self, company_id: str, user_id: str, profile: Profile) -> None:
        self._db.execute(
            "INSERT INTO profiles (user_id, name, home_address, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (user_id) DO UPDATE SET name = excluded.name, home_address = excluded.home_address, "
            "updated_at = excluded.updated_at",
            (self._user_id(company_id, user_id), profile.name, profile.home_address, utc_now()),
        )

    def profile(self, company_id: str, user_id: str) -> Profile | None:
        row = self._db.execute(
            f"SELECT p.name, p.home_address FROM profiles p {OF_USER.format(table='p')}", (company_id, user_id)
        ).fetchone()
        return Profile(**row) if row else None

    def add_helper(self, company_id: str, user_id: str, helper: Helper) -> Helper:
        self._db.execute(
            "INSERT INTO helpers (id, user_id, name, link_code, telegram_chat_id, linked_at, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                helper.id,
                self._user_id(company_id, user_id),
                helper.name,
                helper.link_code,
                helper.telegram_chat_id,
                helper.linked_at,
                helper.created_at,
            ),
        )
        return helper

    def helpers(self, company_id: str, user_id: str) -> list[Helper]:
        rows = self._db.execute(
            f"SELECT {HELPER_COLUMNS} FROM helpers h {OF_USER.format(table='h')} ORDER BY h.rowid",
            (company_id, user_id),
        )
        return [Helper(**row) for row in rows]

    def link_helper(self, link_code: str, telegram_chat_id: str) -> Helper | None:
        row = self._db.execute(
            "UPDATE helpers SET telegram_chat_id = ?, linked_at = ? "
            "WHERE link_code = ? AND (telegram_chat_id IS NULL OR telegram_chat_id = ?) "
            "RETURNING id, name, link_code, telegram_chat_id, linked_at, created_at",
            (telegram_chat_id, utc_now(), link_code, telegram_chat_id),
        ).fetchone()
        return Helper(**row) if row else None

    def remove_helper(self, company_id: str, user_id: str, helper_id: str) -> bool:
        row = self._db.execute(
            "DELETE FROM helpers WHERE id = ? AND user_id = "
            "(SELECT id FROM users WHERE company_id = ? AND external_id = ?) RETURNING id",
            (helper_id, company_id, user_id),
        ).fetchone()
        return row is not None

    def add_alert(self, company_id: str, user_id: str, alert: Alert) -> Alert:
        self._db.execute(
            "INSERT INTO alerts (id, user_id, heard, latitude, longitude, address, text, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                alert.id,
                self._user_id(company_id, user_id),
                alert.heard,
                alert.latitude,
                alert.longitude,
                alert.address,
                alert.text,
                alert.status,
                alert.created_at,
            ),
        )
        return alert

    def last_sent_alert(self, company_id: str, user_id: str) -> Alert | None:
        row = self._db.execute(
            f"SELECT {ALERT_COLUMNS} FROM alerts a {OF_USER.format(table='a')} AND a.status = ? "
            "ORDER BY a.rowid DESC LIMIT 1",
            (company_id, user_id, AlertStatus.SENT),
        ).fetchone()
        return Alert(**row) if row else None

    def alerts(self, company_id: str, user_id: str) -> list[Alert]:
        rows = self._db.execute(
            f"SELECT {ALERT_COLUMNS} FROM alerts a {OF_USER.format(table='a')} ORDER BY a.rowid", (company_id, user_id)
        )
        return [Alert(**row) for row in rows]

    def create_account(self, company_id: str, username: str, password_hash: str) -> bool:
        """False when the username already has an account. Memory saved under it before stays with it."""
        row = self._db.execute(
            "INSERT INTO accounts (user_id, password_hash, created_at) VALUES (?, ?, ?) "
            "ON CONFLICT (user_id) DO NOTHING RETURNING user_id",
            (self._user_id(company_id, username), password_hash, utc_now()),
        ).fetchone()
        return row is not None

    def password_hash(self, company_id: str, username: str) -> str | None:
        row = self._db.execute(
            f"SELECT a.password_hash FROM accounts a {OF_USER.format(table='a')}", (company_id, username)
        ).fetchone()
        return row["password_hash"] if row else None

    def add_session(self, company_id: str, username: str, token_hash: str, expires_at: str) -> None:
        self._db.execute(
            "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token_hash, self._user_id(company_id, username), utc_now(), expires_at),
        )

    def session_user(self, company_id: str, token_hash: str) -> str | None:
        row = self._db.execute(
            "SELECT u.external_id FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash = ? AND u.company_id = ? AND s.expires_at > ?",
            (token_hash, company_id, utc_now()),
        ).fetchone()
        return row["external_id"] if row else None

    def remove_session(self, token_hash: str) -> None:
        self._db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))

    def add_pauses(self, company_id: str, user_id: str, pauses_ms: list[int]) -> None:
        user, now = self._user_id(company_id, user_id), utc_now()
        self._db.executemany(
            "INSERT INTO pauses (user_id, ms, created_at) VALUES (?, ?, ?)", [(user, ms, now) for ms in pauses_ms]
        )

    def recent_pauses(self, company_id: str, user_id: str, limit: int) -> list[int]:
        rows = self._db.execute(
            f"SELECT p.ms FROM pauses p {OF_USER.format(table='p')} ORDER BY p.id DESC LIMIT ?",
            (company_id, user_id, limit),
        )
        return [row["ms"] for row in rows]

    def pause_wait(self, company_id: str, user_id: str) -> float | None:
        row = self._db.execute(
            f"SELECT w.seconds FROM pause_waits w {OF_USER.format(table='w')}", (company_id, user_id)
        ).fetchone()
        return row["seconds"] if row else None

    def save_pause_wait(self, company_id: str, user_id: str, seconds: float) -> None:
        self._db.execute(
            "INSERT INTO pause_waits (user_id, seconds, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT (user_id) DO UPDATE SET seconds = excluded.seconds, updated_at = excluded.updated_at",
            (self._user_id(company_id, user_id), seconds, utc_now()),
        )

    def close(self) -> None:
        self._db.close()
