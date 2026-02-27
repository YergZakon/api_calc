from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from ...core.config import settings

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AnalysisRecord:
    id: str
    case_id: str
    analysis_type: str
    status: str
    input_params: Dict[str, Any]
    result: Dict[str, Any]
    error_message: Optional[str]
    ai_model: Optional[str]
    processing_time_ms: Optional[int]
    task_id: Optional[str]
    created_at: str
    updated_at: str


class AnalysisStore:
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
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_params TEXT,
                    result TEXT,
                    error_message TEXT,
                    ai_model TEXT,
                    processing_time_ms INTEGER,
                    task_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_analyses_case ON analyses(case_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_analyses_type ON analyses(analysis_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_analyses_status ON analyses(status)"
            )

    def create_analysis(
        self,
        case_id: str,
        analysis_type: str,
        input_params: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> AnalysisRecord:
        analysis_id = str(uuid.uuid4())
        now = _utc_now()
        input_params = input_params or {}
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO analyses (
                    id, case_id, analysis_type, status, input_params,
                    result, error_message, ai_model, processing_time_ms,
                    task_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_id,
                    case_id,
                    analysis_type,
                    "pending",
                    json.dumps(input_params, ensure_ascii=False),
                    json.dumps({}, ensure_ascii=False),
                    None,
                    None,
                    None,
                    task_id,
                    now,
                    now,
                ),
            )
        return self.get_analysis(analysis_id)

    def update_analysis(
        self,
        analysis_id: str,
        *,
        status: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        ai_model: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
    ) -> None:
        updates = []
        params: list[Any] = []
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if result is not None:
            updates.append("result = ?")
            params.append(json.dumps(result, ensure_ascii=False))
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        if ai_model is not None:
            updates.append("ai_model = ?")
            params.append(ai_model)
        if processing_time_ms is not None:
            updates.append("processing_time_ms = ?")
            params.append(processing_time_ms)
        updates.append("updated_at = ?")
        params.append(_utc_now())
        params.append(analysis_id)

        if not updates:
            return
        with self._lock, self._connect() as conn:
            conn.execute(
                f"UPDATE analyses SET {', '.join(updates)} WHERE id = ?",
                params,
            )

    def get_analysis(self, analysis_id: str) -> Optional[AnalysisRecord]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM analyses WHERE id = ?",
                (analysis_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def list_analyses(
        self,
        case_id: str,
        analysis_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> list[AnalysisRecord]:
        query = "SELECT * FROM analyses WHERE case_id = ?"
        params: list[Any] = [case_id]
        if analysis_type:
            query += " AND analysis_type = ?"
            params.append(analysis_type)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._lock, self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_record(r) for r in rows]

    def latest_completed_risk(self, case_id: str) -> Optional[AnalysisRecord]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM analyses
                WHERE case_id = ? AND analysis_type = 'risk_analysis' AND status = 'completed'
                ORDER BY created_at DESC LIMIT 1
                """,
                (case_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> AnalysisRecord:
        return AnalysisRecord(
            id=row["id"],
            case_id=row["case_id"],
            analysis_type=row["analysis_type"],
            status=row["status"],
            input_params=json.loads(row["input_params"] or "{}"),
            result=json.loads(row["result"] or "{}"),
            error_message=row["error_message"],
            ai_model=row["ai_model"],
            processing_time_ms=row["processing_time_ms"],
            task_id=row["task_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


_STORE: Optional[AnalysisStore] = None


def get_analysis_store(db_path: Optional[str] = None) -> AnalysisStore:
    global _STORE
    if _STORE is None:
        base_dir = Path(settings.data_dir)
        path = db_path or str(base_dir / "ai_analysis.db")
        _STORE = AnalysisStore(path)
    return _STORE
