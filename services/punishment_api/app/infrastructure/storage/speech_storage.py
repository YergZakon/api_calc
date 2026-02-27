from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ...core.config import settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class SpeechRecord:
    id: str
    case_id: Optional[str]
    status: str
    versions: list[Dict[str, Any]]
    error_message: Optional[str]
    created_by: Optional[str]
    created_at: str
    updated_at: str


class SpeechStore:
    def __init__(self, db_path: str):
        self._db_path = Path(db_path)
        self._lock = threading.Lock()
        self._ensure_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_db(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS speeches (
                    id TEXT PRIMARY KEY,
                    case_id TEXT,
                    status TEXT NOT NULL,
                    versions TEXT,
                    error_message TEXT,
                    created_by TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_speeches_case ON speeches(case_id)")

    def create_speech(
        self,
        case_id: Optional[str],
        created_by: Optional[str] = None,
    ) -> SpeechRecord:
        speech_id = str(uuid.uuid4())
        now = _utc_now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO speeches (
                    id, case_id, status, versions, error_message, created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    speech_id,
                    case_id,
                    "pending",
                    json.dumps([], ensure_ascii=False),
                    None,
                    created_by,
                    now,
                    now,
                ),
            )
        return self.get_speech(speech_id)

    def update_speech(
        self,
        speech_id: str,
        *,
        status: Optional[str] = None,
        error_message: Optional[str] = None,
        versions: Optional[list[Dict[str, Any]]] = None,
    ) -> None:
        updates = []
        params: list[Any] = []
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        if versions is not None:
            updates.append("versions = ?")
            params.append(json.dumps(versions, ensure_ascii=False))
        updates.append("updated_at = ?")
        params.append(_utc_now())
        params.append(speech_id)
        with self._lock, self._connect() as conn:
            conn.execute(
                f"UPDATE speeches SET {', '.join(updates)} WHERE id = ?",
                params,
            )

    def get_speech(self, speech_id: str) -> Optional[SpeechRecord]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM speeches WHERE id = ?",
                (speech_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def add_version(
        self,
        speech_id: str,
        version: Dict[str, Any],
        *,
        status: Optional[str] = None,
    ) -> None:
        record = self.get_speech(speech_id)
        if not record:
            return
        versions = list(record.versions or [])
        versions.append(version)
        self.update_speech(speech_id, versions=versions, status=status)

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> SpeechRecord:
        return SpeechRecord(
            id=row["id"],
            case_id=row["case_id"],
            status=row["status"],
            versions=json.loads(row["versions"] or "[]"),
            error_message=row["error_message"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


_STORE: Optional[SpeechStore] = None


def get_speech_store(db_path: Optional[str] = None) -> SpeechStore:
    global _STORE
    if _STORE is None:
        base_dir = Path(settings.data_dir)
        path = db_path or str(base_dir / "speech.db")
        _STORE = SpeechStore(path)
    return _STORE
