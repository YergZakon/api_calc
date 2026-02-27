from __future__ import annotations

import time
from typing import Any, Dict, Optional

from .ai_analysis_provider import MockAIProvider
from ...infrastructure.storage.ai_analysis_storage import AnalysisRecord, get_analysis_store


ANALYSIS_TYPE_DISPLAY = {
    "materials": "Анализ материалов",
    "risk_analysis": "Анализ рисков",
    "similar_verdicts": "Анализ приговоров",
    "verdict_analysis": "Анализ приговора",
}


def start_analysis(case_id: str, analysis_type: str, input_params: Optional[Dict[str, Any]] = None) -> AnalysisRecord:
    store = get_analysis_store()
    task_id = f"task-{case_id}-{analysis_type}"
    return store.create_analysis(case_id, analysis_type, input_params=input_params, task_id=task_id)


def run_analysis(analysis_id: str) -> None:
    store = get_analysis_store()
    record = store.get_analysis(analysis_id)
    if not record:
        return

    store.update_analysis(analysis_id, status="processing")

    provider = MockAIProvider()
    started = time.time()

    try:
        result = _execute_provider(provider, record)
        processing_time_ms = int((time.time() - started) * 1000)
        store.update_analysis(
            analysis_id,
            status="completed",
            result=result["content"],
            ai_model=result["model"],
            processing_time_ms=processing_time_ms,
        )
    except Exception as exc:
        store.update_analysis(
            analysis_id,
            status="failed",
            error_message=str(exc),
        )


def _execute_provider(provider: MockAIProvider, record: AnalysisRecord) -> Dict[str, Any]:
    payload = record.input_params or {}

    if record.analysis_type == "materials":
        documents = payload.get("documents") or []
        texts = [doc.get("text", "") for doc in documents if isinstance(doc, dict)]
        case_info = {"erdr_number": payload.get("erdr_number")}
        result = provider.analyze_materials(texts, case_info)
        return {"model": result.model, "content": result.content}

    if record.analysis_type == "risk_analysis":
        case_data = {
            "erdr_number": payload.get("erdr_number"),
            "report_text": payload.get("report_text"),
            "similar_verdicts_summary": payload.get("similar_verdicts_summary"),
            "norms_summary": payload.get("norms_summary"),
        }
        materials_analysis = {"report_text": payload.get("report_text")}
        result = provider.analyze_risks(case_data, materials_analysis)
        return {"model": result.model, "content": result.content}

    if record.analysis_type == "similar_verdicts":
        verdicts = payload.get("verdicts") or []
        texts = []
        for item in verdicts:
            if isinstance(item, dict):
                texts.append(item.get("text", ""))
            else:
                texts.append(str(item))
        case_info = payload.get("case_info") or {}
        result = provider.analyze_similar_verdicts(texts, case_info)
        return {"model": result.model, "content": result.content}

    if record.analysis_type == "verdict_analysis":
        verdict_text = payload.get("verdict_text") or ""
        context = {
            "original_request": payload.get("original_request") or {},
            "speech_text": payload.get("speech_text"),
            "risk_analysis_result": payload.get("risk_analysis_result"),
            "draft_type": payload.get("draft_type") or "auto",
        }
        result = provider.analyze_verdict(verdict_text, context)
        return {"model": result.model, "content": result.content}

    raise ValueError(f"Unsupported analysis type: {record.analysis_type}")


def build_risk_analysis_response(record: AnalysisRecord) -> Dict[str, Any]:
    result = record.result or {}
    risks = _transform_risk_items(result)

    high_count = sum(1 for r in risks if r["level"] == "высокий")
    medium_count = sum(1 for r in risks if r["level"] == "средний")
    low_count = sum(1 for r in risks if r["level"] == "низкий")

    return {
        "success": True,
        "case_id": record.case_id,
        "risks": risks,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "sources": {"model": record.ai_model or "unknown"},
        "analysis_date": record.created_at[:10],
        "analysis_id": record.id,
        "processing_time_ms": record.processing_time_ms,
        "raw_assessment": result.get("risk_assessment"),
        "action_plan": result.get("action_plan", []),
        "comparison_with_guilty": result.get("comparison_with_guilty"),
    }


def _transform_risk_items(result: Dict[str, Any]) -> list[Dict[str, Any]]:
    risks: list[Dict[str, Any]] = []

    if risk_assessment := result.get("risk_assessment"):
        overall_risk = risk_assessment.get("overall_risk", "medium")
        level = "high" if overall_risk in ("high", "critical") else overall_risk
        if level not in ("high", "medium", "low"):
            level = "medium"
        level_ru = _risk_level_ru(level)

        probability = risk_assessment.get("conviction_probability_percent", 0)
        summary = risk_assessment.get("summary", "")

        risks.append(
            {
                "level": level_ru,
                "category": "общий",
                "title": f"Общая оценка: {probability}% вероятность обвинения",
                "text": summary,
                "recommendation": "См. детальный анализ рисков ниже.",
            }
        )

    if comparison := result.get("comparison_with_acquittals", {}):
        for rf in comparison.get("risk_factors", []):
            prob = rf.get("probability", "medium")
            level = prob if prob in ("high", "medium", "low") else "medium"
            level_ru = _risk_level_ru(level)
            risks.append(
                {
                    "level": level_ru,
                    "category": "практика",
                    "title": rf.get("risk", "Риск из практики оправданий"),
                    "text": f"{rf.get('current_case_status', '')} (Случай: {rf.get('acquittal_reference', 'N/A')})",
                    "recommendation": rf.get("mitigation", "Требуется анализ."),
                }
            )

    if evidence := result.get("evidence_analysis", {}):
        for weakness in evidence.get("weaknesses", []):
            risks.append(
                {
                    "level": _risk_level_ru("medium"),
                    "category": "доказательства",
                    "title": weakness.get("evidence", "Слабое доказательство"),
                    "text": weakness.get("why_weak", "Требует внимания."),
                    "recommendation": weakness.get("how_to_fix", "Усилить доказательную базу."),
                }
            )

        for missing in evidence.get("missing_evidence", []):
            importance = missing.get("importance", "medium")
            level = importance if importance in ("high", "medium", "low") else "medium"
            level_ru = _risk_level_ru(level)
            risks.append(
                {
                    "level": level_ru,
                    "category": "доказательства",
                    "title": f"Отсутствует: {missing.get('what', 'доказательство')}",
                    "text": f"Важность: {importance}",
                    "recommendation": "Запросить недостающие материалы.",
                }
            )

    for proc_risk in result.get("procedural_risks", []):
        risks.append(
            {
                "level": _risk_level_ru("high"),
                "category": "процессуальные",
                "title": proc_risk.get("issue", "Процессуальное нарушение"),
                "text": f"{proc_risk.get('consequence', '')} (Стадия: {proc_risk.get('stage', 'N/A')})",
                "recommendation": proc_risk.get("recommendation", "Устранить нарушение."),
            }
        )

    if not risks:
        risks.append(
            {
                "level": _risk_level_ru("low"),
                "category": "прочее",
                "title": "Значительных рисков не выявлено",
                "text": "Анализ не выявил существенных рисков для обвинения.",
                "recommendation": "Продолжить работу по делу в стандартном режиме.",
            }
        )

    return risks


def _risk_level_ru(level: str) -> str:
    mapping = {
        "high": "высокий",
        "medium": "средний",
        "low": "низкий",
        "critical": "высокий",
    }
    return mapping.get(level, "средний")
