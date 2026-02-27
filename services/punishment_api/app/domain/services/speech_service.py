from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

from ...infrastructure.storage.speech_storage import get_speech_store


def start_speech(case_id: Optional[str], payload: Dict[str, Any], created_by: Optional[str] = None) -> str:
    store = get_speech_store()
    speech = store.create_speech(case_id, created_by=created_by)
    return speech.id


def run_speech(speech_id: str, payload: Dict[str, Any]) -> None:
    store = get_speech_store()
    record = store.get_speech(speech_id)
    if not record:
        return

    start = time.time()
    try:
        content = _render_mock_speech(payload)
        generation_time_ms = int((time.time() - start) * 1000)

        version = {
            "id": str(uuid.uuid4()),
            "version_number": 1,
            "content": content,
            "created_at": _now_iso(),
            "created_by": record.created_by,
            "ai_model": "mock/heuristic-v1",
            "generation_time_ms": generation_time_ms,
        }
        store.add_version(speech_id, version, status="draft")
    except Exception as exc:
        store.update_speech(speech_id, status="failed", error_message=str(exc))


def _render_mock_speech(payload: Dict[str, Any]) -> str:
    fio = payload.get("fio") or "Подсудимый"
    article_code = payload.get("article_code") or "статья не указана"
    erdr = payload.get("erdr_number") or payload.get("erdr") or "—"
    report_text = payload.get("report_text") or "Справка по делу отсутствует."
    calc = payload.get("calculation_result") or {}
    verdicts_summary = payload.get("similar_verdicts_summary")
    norms_summary = payload.get("norms_summary")

    punishment_text = ""
    if isinstance(calc, dict):
        structured = calc.get("structured") or {}
        punishments = structured.get("punishments") or {}
        imprisonment = punishments.get("imprisonment") or {}
        formatted = imprisonment.get("formatted_text")
        if not formatted:
            a_nakaz = calc.get("aNakaz") or []
            if len(a_nakaz) > 5 and len(a_nakaz[5]) > 3:
                formatted = a_nakaz[5][3]
        if formatted:
            punishment_text = f"Расчёт наказания: {formatted}."

    parts = [
        f"Уважаемый суд! Рассматривается уголовное дело по ЕРДР {erdr}.",
        f"Подсудимый: {fio}. Квалификация: {article_code}.",
        f"Справка по делу: {report_text}",
    ]
    if punishment_text:
        parts.append(punishment_text)
    if verdicts_summary:
        parts.append(f"Сводка по похожим приговорам: {verdicts_summary}")
    if norms_summary:
        parts.append(f"Нормативные акты: {norms_summary}")
    parts.append("Прошу суд назначить наказание в пределах санкции статьи с учетом обстоятельств дела.")

    return "\n\n".join(parts)


def _now_iso() -> str:
    import datetime

    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
