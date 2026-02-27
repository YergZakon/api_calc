from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class AIProviderResult:
    model: str
    content: Dict[str, Any]


class MockAIProvider:
    name = "mock"
    model = "heuristic-v1"

    def analyze_materials(self, documents_text: List[str], case_info: Optional[Dict[str, Any]] = None) -> AIProviderResult:
        case_info = case_info or {}
        doc_count = len(documents_text)
        summary = "Анализ материалов выполнен."
        if doc_count == 0:
            summary = "Материалы не предоставлены."
        elif doc_count < 3:
            summary = "Небольшой объём материалов. Нужна дополнительная проверка."

        content = {
            "summary": summary,
            "documents_analyzed": doc_count,
            "case_info": case_info,
            "key_facts": case_info.get("circumstances", ""),
            "risks": ["Недостаточно материалов"] if doc_count == 0 else [],
            "recommendations": [
                "Проверить полноту материалов",
                "Сверить доказательственную базу с фабулой дела",
            ],
        }
        return AIProviderResult(model=f"{self.name}/{self.model}", content=content)

    def analyze_risks(self, case_data: Optional[Dict[str, Any]] = None, materials_analysis: Optional[Dict[str, Any]] = None) -> AIProviderResult:
        case_data = case_data or {}
        materials_analysis = materials_analysis or {}
        doc_count = materials_analysis.get("documents_analyzed", 0) or 0

        if doc_count >= 5:
            overall_risk = "low"
            probability = 75
        elif doc_count >= 2:
            overall_risk = "medium"
            probability = 55
        else:
            overall_risk = "high"
            probability = 35

        content = {
            "risk_assessment": {
                "overall_risk": overall_risk,
                "conviction_probability_percent": probability,
                "summary": "Оценка основана на объёме материалов и общих признаках дела.",
            },
            "comparison_with_acquittals": {
                "risk_factors": [
                    {
                        "risk": "Недостаточная полнота доказательственной базы",
                        "probability": overall_risk,
                        "current_case_status": "Требуется дополнительная проверка",
                        "acquittal_reference": "N/A",
                        "mitigation": "Дополнить материалы и устранить пробелы",
                    }
                ]
            },
            "evidence_analysis": {
                "weaknesses": [
                    {
                        "evidence": "Показания ключевого свидетеля",
                        "why_weak": "Не подтверждены независимыми источниками",
                        "how_to_fix": "Запросить дополнительные документы и экспертизу",
                    }
                ],
                "missing_evidence": [
                    {
                        "what": "Экспертиза",
                        "importance": "high" if overall_risk == "high" else "medium",
                    }
                ],
            },
            "procedural_risks": [
                {
                    "issue": "Нарушение сроков",
                    "stage": "досудебное расследование",
                    "consequence": "риск исключения доказательств",
                    "recommendation": "Проверить соблюдение сроков и основания продления",
                }
            ],
            "action_plan": [
                {
                    "priority": 1,
                    "action": "Собрать недостающие материалы",
                    "deadline": "7 дней",
                    "responsible": "следователь",
                }
            ],
            "comparison_with_guilty": {
                "summary": "Сопоставление с обвинительными приговорами требует дополнений.",
            },
        }
        return AIProviderResult(model=f"{self.name}/{self.model}", content=content)

    def analyze_similar_verdicts(self, verdicts_text: List[str], case_info: Optional[Dict[str, Any]] = None) -> AIProviderResult:
        verdicts_count = len(verdicts_text)
        content = {
            "summary": "Сравнительный анализ аналогичных приговоров выполнен.",
            "verdicts_analyzed": verdicts_count,
            "patterns": [
                "Часто применяются условные сроки при наличии смягчающих обстоятельств",
                "Суд учитывает характер вреда и позицию потерпевшего",
            ],
            "recommendations": [
                "Усилить доказательственную базу по ключевым эпизодам",
                "Подготовить аргументацию по отягчающим обстоятельствам",
            ],
            "case_info": case_info or {},
        }
        return AIProviderResult(model=f"{self.name}/{self.model}", content=content)

    def analyze_verdict(self, verdict_text: str, context: Optional[Dict[str, Any]] = None) -> AIProviderResult:
        context = context or {}
        original_request = context.get("original_request") or {}
        speech_text = context.get("speech_text") or ""
        risk_result = context.get("risk_analysis_result") or {}
        draft_type = (context.get("draft_type") or "auto").lower()

        verdict_excerpt = verdict_text[:500] if verdict_text else ""
        requested_punishment = "Из речи: наказание не извлечено"
        if speech_text:
            requested_punishment = "Из речи: требуется наказание (см. текст речи)"
        verdict_punishment = "Из приговора: наказание не извлечено"
        if verdict_text:
            verdict_punishment = "Из приговора: назначено наказание (см. текст приговора)"

        mismatches = []
        if speech_text and verdict_text:
            mismatches.append(
                {
                    "area": "наказание",
                    "speech": requested_punishment,
                    "verdict": verdict_punishment,
                    "comment": "Сверить запрошенное наказание с назначенным судом.",
                }
            )
        elif speech_text and not verdict_text:
            mismatches.append(
                {
                    "area": "данные",
                    "speech": "Речь предоставлена",
                    "verdict": "Текст приговора не предоставлен",
                    "comment": "Невозможно выполнить сравнение без текста приговора.",
                }
            )

        confirmed = []
        unconfirmed = []
        risks = risk_result.get("risks") if isinstance(risk_result, dict) else []
        for item in risks or []:
            level = (item.get("level") or "").lower()
            entry = {
                "title": item.get("title"),
                "level": item.get("level"),
                "category": item.get("category"),
            }
            if level in ("высокий", "high"):
                confirmed.append(entry)
            else:
                unconfirmed.append(entry)

        if draft_type not in ("agreement", "appeal", "auto"):
            draft_type = "auto"
        if draft_type == "auto":
            draft_type = "appeal" if mismatches else "agreement"

        draft_title = "Проект заключения о согласии с приговором"
        draft_text = "С учетом анализа оснований для обжалования не выявлено. Предлагается согласиться с приговором."
        if draft_type == "appeal":
            draft_title = "Проект апелляционного ходатайства"
            draft_text = "Предлагается подготовить апелляционную жалобу с учетом выявленных несоответствий."

        content = {
            "summary": "Анализ приговора выполнен.",
            "appeal_grounds": [
                {
                    "title": "Несоответствие выводов суда фактическим обстоятельствам",
                    "basis": "ст. 437 УПК РК",
                    "strength": "medium",
                    "text": "Рекомендуется проверить полноту исследования доказательств.",
                }
            ],
            "verdict_excerpt": verdict_excerpt,
            "original_request": original_request,
            "speech_verdict_comparison": {
                "requested_punishment": requested_punishment,
                "verdict_punishment": verdict_punishment,
                "mismatches": mismatches,
            },
            "risk_verdict_comparison": {
                "confirmed_risks": confirmed,
                "unconfirmed_risks": unconfirmed,
                "notes": "Сопоставление рисков с приговором выполнено в упрощенном режиме.",
            },
            "draft_document": {
                "type": draft_type,
                "title": draft_title,
                "text": draft_text,
            },
        }
        return AIProviderResult(model=f"{self.name}/{self.model}", content=content)
