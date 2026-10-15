import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from enums import RequestStatus
from memory.models import Action, Request, Summary, Turn
from utils import hours_ago, utc_now

SCHEMA = (Path(__file__).parent / "schema.sql").read_text()


class SqliteMemoryStore:
    def __init__(self, db_path: Path, unfinished_ttl_hours: float = 24) -> None:
        self._ttl_hours = unfinished_ttl_hours
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(db_path, autocommit=True, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.executescript(SCHEMA)

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
            "SELECT t.seq, t.request_id, t.heard, t.say, t.next_move, t.created_at FROM turns t "
            "JOIN requests r ON r.id = t.request_id "
            "WHERE t.conversation_id = ? AND t.seq > ? AND r.status IN (?, ?) ORDER BY t.seq",
            (conversation_id, after_seq, RequestStatus.DONE, RequestStatus.CANCELLED),
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

    def close(self) -> None:
        self._db.close()
