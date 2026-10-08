import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from enums import NextMove, RequestStatus
from memory.models import Action, Request, Turn
from utils import utc_now

SCHEMA = (Path(__file__).parent / "schema.sql").read_text()


class SqliteMemoryStore:
    def __init__(self, db_path: Path) -> None:
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

    def add_turn(self, conversation_id: int, heard: str, say: str, next_move: NextMove) -> Turn:
        row = self._db.execute(
            "INSERT INTO turns (conversation_id, seq, heard, say, next_move, created_at) VALUES "
            "(?, (SELECT COALESCE(MAX(seq), 0) + 1 FROM turns WHERE conversation_id = ?), ?, ?, ?, ?) "
            "RETURNING seq, heard, say, next_move, created_at",
            (conversation_id, conversation_id, heard, say, next_move, utc_now()),
        ).fetchone()
        return Turn(**row)

    def turns(self, conversation_id: int) -> list[Turn]:
        rows = self._db.execute(
            "SELECT seq, heard, say, next_move, created_at FROM turns WHERE conversation_id = ? ORDER BY seq",
            (conversation_id,),
        )
        return [Turn(**row) for row in rows]

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
            "WHERE conversation_id = ? AND status IN (?, ?) ORDER BY updated_at DESC LIMIT 1",
            (conversation_id, RequestStatus.PENDING, RequestStatus.CONFIRMED),
        ).fetchone()
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
