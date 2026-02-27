from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

SYSTEM_PROMPT = (
    "Ты — юридический аналитик для органов гособвинения РК.\n"
    "Запрещено выдумывать факты, ссылки, даты, нормы, если их нет во входных данных.\n"
    "Если данных недостаточно — явно укажи \"недостаточно данных\" в соответствующем поле.\n"
    "Пиши только на русском языке.\n"
    "Не раскрывай внутренние рассуждения.\n"
    "Возвращай строго JSON без Markdown и без пояснений вокруг."
)


def _as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _build_prompt(template: str, payload: Dict[str, Any]) -> Dict[str, str]:
    user = template.replace("{INPUT_JSON}", _as_json(payload))
    return {"system": SYSTEM_PROMPT, "user": user}


MATERIALS_TEMPLATE = """
Входные данные (JSON):
{INPUT_JSON}

Задача: сформировать справку по делу на основе текста документов.
Укажи ключевые факты, пробелы, риски и рекомендации. Не выдумывай.

Верни JSON следующей структуры:
{
  "summary": "краткая справка (3-6 предложений)",
  "documents_analyzed": число,
  "case_info": { "erdr_number": "..." },
  "key_facts": "сжатое изложение фактов/обстоятельств (если есть)",
  "risks": ["список рисков/пробелов"],
  "recommendations": ["рекомендации по доработке материалов"]
}
""".strip()


def build_materials_prompt(erdr_number: Optional[str], documents: List[Dict[str, Any]]) -> Dict[str, str]:
    payload = {
        "erdr_number": erdr_number,
        "documents": documents,
    }
    return _build_prompt(MATERIALS_TEMPLATE, payload)


SIMILAR_VERDICTS_TEMPLATE = """
Входные данные (JSON):
{INPUT_JSON}

Задача: сделать аналитическую сводку по похожим приговорам.
Выяви повторяющиеся паттерны, типовые наказания, типовые обстоятельства.
Не выдумывай факты, используй только текст приговоров.

Верни JSON:
{
  "summary": "общий вывод по практике (3-6 предложений)",
  "verdicts_analyzed": число,
  "patterns": ["паттерн 1", "паттерн 2", "паттерн 3"],
  "recommendations": ["рекомендация 1", "рекомендация 2"],
  "key_statistics": {
    "common_punishments": "строка с типовыми наказаниями",
    "average_terms": "если можно вывести, иначе 'недостаточно данных'",
    "acquittal_signals": "если есть, иначе 'недостаточно данных'"
  },
  "summary_short": "краткая сводка (1-2 предложения) для последующих сервисов"
}
""".strip()


def build_similar_verdicts_prompt(case_info: Optional[Dict[str, Any]], verdicts: List[Dict[str, Any]]) -> Dict[str, str]:
    payload = {
        "case_info": case_info or {},
        "verdicts": verdicts,
    }
    return _build_prompt(SIMILAR_VERDICTS_TEMPLATE, payload)


NORMS_TEMPLATE = """
Входные данные (JSON):
{INPUT_JSON}

Задача: подобрать релевантные НПА (кодексы, постановления) и кратко описать применимость.
Не выдумывай конкретные номера статей, если нет оснований — пиши общую ссылку на раздел.

Верни JSON:
{
  "norms": [
    {
      "title": "Название НПА",
      "subtitle": "короткая расшифровка/применимость",
      "relevance": "high|medium|low",
      "summary": "краткое пояснение применимости"
    }
  ],
  "norms_summary": "краткая сводка НПА (1-2 предложения)"
}
""".strip()


def build_norms_prompt(report_text: str, similar_verdicts_summary: Optional[str] = None) -> Dict[str, str]:
    payload = {
        "report_text": report_text,
        "similar_verdicts_summary": similar_verdicts_summary,
    }
    return _build_prompt(NORMS_TEMPLATE, payload)


RISKS_TEMPLATE = """
Входные данные (JSON):
{INPUT_JSON}

Задача: выявить риски, оценить вероятность обвинительного приговора и сформировать план действий.
Если данных мало — укажи это явно.

Верни JSON:
{
  "risk_assessment": {
    "overall_risk": "high|medium|low",
    "conviction_probability_percent": 0-100,
    "summary": "краткая оценка"
  },
  "comparison_with_acquittals": {
    "risk_factors": [
      {
        "risk": "наименование риска",
        "probability": "high|medium|low",
        "current_case_status": "состояние в текущем деле",
        "acquittal_reference": "если нет данных, 'N/A'",
        "mitigation": "как снизить риск"
      }
    ]
  },
  "evidence_analysis": {
    "weaknesses": [
      {
        "evidence": "слабое доказательство",
        "why_weak": "почему слабое",
        "how_to_fix": "как усилить"
      }
    ],
    "missing_evidence": [
      {
        "what": "чего не хватает",
        "importance": "high|medium|low"
      }
    ]
  },
  "procedural_risks": [
    {
      "issue": "процессуальный риск",
      "stage": "стадия",
      "consequence": "последствие",
      "recommendation": "рекомендация"
    }
  ],
  "action_plan": [
    {
      "priority": 1,
      "action": "действие",
      "deadline": "срок (например, 7 дней)",
      "responsible": "ответственный"
    }
  ],
  "comparison_with_guilty": {
    "summary": "сопоставление с обвинительными приговорами"
  }
}
""".strip()


def build_risks_prompt(
    report_text: str,
    similar_verdicts_summary: Optional[str],
    norms_summary: Optional[str],
) -> Dict[str, str]:
    payload = {
        "report_text": report_text,
        "similar_verdicts_summary": similar_verdicts_summary,
        "norms_summary": norms_summary,
    }
    return _build_prompt(RISKS_TEMPLATE, payload)


SPEECH_TEMPLATE = """
Входные данные (JSON):
{INPUT_JSON}

Задача: сгенерировать речь гособвинителя.
Структура: вступление → фактические обстоятельства → правовая квалификация → оценка доказательств → наказание → заключение.
Наказание формулируй с опорой на calculation_result.

Верни JSON:
{
  "content": "полный текст речи",
  "requested_punishment": "как сформулировано требуемое наказание (1-2 предложения)"
}
""".strip()


def build_speech_prompt(
    erdr_number: str,
    article_code: str,
    fio: str,
    report_text: str,
    calculation_result: Dict[str, Any],
    similar_verdicts_summary: Optional[str] = None,
    norms_summary: Optional[str] = None,
) -> Dict[str, str]:
    payload = {
        "erdr_number": erdr_number,
        "article_code": article_code,
        "fio": fio,
        "report_text": report_text,
        "calculation_result": calculation_result,
        "similar_verdicts_summary": similar_verdicts_summary,
        "norms_summary": norms_summary,
    }
    return _build_prompt(SPEECH_TEMPLATE, payload)


VERDICT_ANALYSIS_TEMPLATE = """
Входные данные (JSON):
{INPUT_JSON}

Задача:
1) Сравнить речь и приговор (наказание, выводы).
2) Сопоставить риски с итогом.
3) Сформировать проект: согласие или апелляция.

Верни JSON:
{
  "summary": "итоговый вывод",
  "appeal_grounds": [
    {
      "title": "основание",
      "basis": "норма/основание (если известно)",
      "strength": "high|medium|low",
      "text": "пояснение"
    }
  ],
  "verdict_excerpt": "первые 500-800 символов приговора",
  "original_request": { ... },
  "speech_verdict_comparison": {
    "requested_punishment": "наказание из речи (если извлекается)",
    "verdict_punishment": "назначенное наказание (если извлекается)",
    "mismatches": [
      {
        "area": "наказание|факты|квалификация",
        "speech": "как в речи",
        "verdict": "как в приговоре",
        "comment": "комментарий"
      }
    ]
  },
  "risk_verdict_comparison": {
    "confirmed_risks": [
      {"title": "...", "level": "...", "category": "..."}
    ],
    "unconfirmed_risks": [
      {"title": "...", "level": "...", "category": "..."}
    ],
    "notes": "краткое пояснение"
  },
  "draft_document": {
    "type": "agreement|appeal",
    "title": "название документа",
    "text": "текст проекта"
  }
}
""".strip()


def build_verdict_analysis_prompt(
    verdict_text: str,
    original_request: Optional[Dict[str, Any]],
    speech_text: Optional[str],
    risk_analysis_result: Optional[Dict[str, Any]],
    draft_type: Optional[str] = None,
) -> Dict[str, str]:
    payload = {
        "verdict_text": verdict_text,
        "original_request": original_request or {},
        "speech_text": speech_text,
        "risk_analysis_result": risk_analysis_result,
        "draft_type": draft_type or "auto",
    }
    return _build_prompt(VERDICT_ANALYSIS_TEMPLATE, payload)


PROMPT_BUILDERS = {
    "materials": build_materials_prompt,
    "similar_verdicts": build_similar_verdicts_prompt,
    "norms": build_norms_prompt,
    "risk_analysis": build_risks_prompt,
    "speech": build_speech_prompt,
    "verdict_analysis": build_verdict_analysis_prompt,
}
