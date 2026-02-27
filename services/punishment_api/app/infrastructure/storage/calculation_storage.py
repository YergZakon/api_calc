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
class CalculationRecord:
    id: str
    case_id: Optional[str]
    article_code: str
    article_name: str
    min_months: Optional[float]
    max_months: Optional[float]
    formatted_result: str
    calculation_log: list
    modifiers_applied: list
    warnings: list
    created_at: str
    created_by: Optional[str]
    payload: Dict[str, Any]
    result: Dict[str, Any]


class CalculationStore:
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
                CREATE TABLE IF NOT EXISTS calculations (
                    id TEXT PRIMARY KEY,
                    case_id TEXT,
                    article_code TEXT,
                    article_name TEXT,
                    min_months REAL,
                    max_months REAL,
                    formatted_result TEXT,
                    calculation_log TEXT,
                    modifiers_applied TEXT,
                    warnings TEXT,
                    created_at TEXT NOT NULL,
                    created_by TEXT,
                    payload TEXT,
                    result TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_calculations_case ON calculations(case_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_calculations_user ON calculations(created_by)")

    def create_calculation(
        self,
        *,
        case_id: Optional[str],
        article_code: str,
        article_name: str,
        min_months: Optional[float],
        max_months: Optional[float],
        formatted_result: str,
        calculation_log: Optional[list] = None,
        modifiers_applied: Optional[list] = None,
        warnings: Optional[list] = None,
        created_by: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> CalculationRecord:
        calc_id = str(uuid.uuid4())
        now = _utc_now()
        calculation_log = calculation_log or []
        modifiers_applied = modifiers_applied or []
        warnings = warnings or []
        payload = payload or {}
        result = result or {}

        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO calculations (
                    id, case_id, article_code, article_name, min_months, max_months,
                    formatted_result, calculation_log, modifiers_applied, warnings,
                    created_at, created_by, payload, result
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    calc_id,
                    case_id,
                    article_code,
                    article_name,
                    min_months,
                    max_months,
                    formatted_result,
                    json.dumps(calculation_log, ensure_ascii=False),
                    json.dumps(modifiers_applied, ensure_ascii=False),
                    json.dumps(warnings, ensure_ascii=False),
                    now,
                    created_by,
                    json.dumps(payload, ensure_ascii=False),
                    json.dumps(result, ensure_ascii=False),
                ),
            )

        return self.get_calculation(calc_id)

    def get_calculation(self, calc_id: str) -> Optional[CalculationRecord]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM calculations WHERE id = ?",
                (calc_id,),
            ).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def list_calculations(
        self,
        *,
        user_id: Optional[str],
        limit: int,
        offset: int,
    ) -> tuple[int, list[CalculationRecord]]:
        params: list[Any] = []
        base = "FROM calculations"
        if user_id:
            base += " WHERE created_by = ?"
            params.append(user_id)

        with self._lock, self._connect() as conn:
            total_row = conn.execute(f"SELECT COUNT(*) as cnt {base}", params).fetchone()
            total = int(total_row["cnt"]) if total_row else 0

            query = f"SELECT * {base} ORDER BY created_at DESC LIMIT ? OFFSET ?"
            rows = conn.execute(query, params + [limit, offset]).fetchall()

        return total, [self._row_to_record(r) for r in rows]

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> CalculationRecord:
        return CalculationRecord(
            id=row["id"],
            case_id=row["case_id"],
            article_code=row["article_code"] or "",
            article_name=row["article_name"] or "",
            min_months=row["min_months"],
            max_months=row["max_months"],
            formatted_result=row["formatted_result"] or "",
            calculation_log=json.loads(row["calculation_log"] or "[]"),
            modifiers_applied=json.loads(row["modifiers_applied"] or "[]"),
            warnings=json.loads(row["warnings"] or "[]"),
            created_at=row["created_at"],
            created_by=row["created_by"],
            payload=json.loads(row["payload"] or "{}"),
            result=json.loads(row["result"] or "{}"),
        )


_STORE: Optional[CalculationStore] = None


def get_calculation_store(db_path: Optional[str] = None) -> CalculationStore:
    global _STORE
    if _STORE is None:
        base_dir = Path(settings.data_dir)
        path = db_path or str(base_dir / "calculations.db")
        _STORE = CalculationStore(path)
    return _STORE
