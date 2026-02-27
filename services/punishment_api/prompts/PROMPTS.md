# LLM Prompts (Punishment API)

Ниже — утверждённые промпты для всех LLM‑задач сервиса.
Каждый промпт привязан к входным и выходным данным конкретного API.

## Общий SYSTEM‑промпт
```
Ты — юридический аналитик для органов гособвинения РК.
Запрещено выдумывать факты, ссылки, даты, нормы, если их нет во входных данных.
Если данных недостаточно — явно укажи "недостаточно данных" в соответствующем поле.
Пиши только на русском языке.
Не раскрывай внутренние рассуждения.
Возвращай строго JSON без Markdown и без пояснений вокруг.
```

---

## 1) Анализ материалов → СПРАВКА
**Endpoint:** `POST /api/case/{erdr}/analyze-materials/`

**Вход (API → LLM):**
- `erdr_number`
- `documents[]: {name, text}`

**USER‑промпт:**
```
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
```

**Выход (LLM → API result):**
- `summary`, `documents_analyzed`, `case_info`, `key_facts`, `risks`, `recommendations`

---

## 2) Анализ похожих приговоров (саммари практики)
**Endpoint:** `POST /api/case/{uuid}/verdicts/analyze/`

**Вход (API → LLM):**
- `case_info`
- `verdicts[]: {text, similarity?, decision?}`

**USER‑промпт:**
```
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
```

**Выход (LLM → API result):**
- `summary`, `verdicts_analyzed`, `patterns`, `recommendations`, `key_statistics`, `summary_short`

---

## 3) НПА по справке
**Endpoint:** `POST /api/case/{erdr}/norms/`

**Вход (API → LLM):**
- `report_text`
- `similar_verdicts_summary` (опционально)

**USER‑промпт:**
```
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
```

**Выход (LLM → API result):**
- `norms[]`, `norms_summary`

---

## 4) Анализ рисков
**Endpoint:** `POST /api/case/{erdr}/risks/analyze/`

**Вход (API → LLM):**
- `report_text`
- `similar_verdicts_summary`
- `norms_summary`

**USER‑промпт:**
```
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
```

**Выход (LLM → API result):**
- `risk_assessment`, `comparison_with_acquittals`, `evidence_analysis`, `procedural_risks`, `action_plan`, `comparison_with_guilty`

---

## 5) Генерация речи гособвинителя
**Endpoint:** `POST /api/generate/async/`

**Вход (API → LLM):**
- `erdr_number`
- `article_code`
- `fio`
- `report_text`
- `calculation_result`
- `similar_verdicts_summary` (опц.)
- `norms_summary` (опц.)

**USER‑промпт:**
```
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
```

**Выход (LLM → API result):**
- `content`, `requested_punishment`

---

## 6) Анализ приговора + проект итогового документа
**Endpoint:** `POST /api/case/{uuid}/verdict/analyze/`

**Вход (API → LLM):**
- `verdict_text`
- `original_request`
- `speech_text`
- `risk_analysis_result`
- `draft_type` (agreement|appeal|auto)

**USER‑промпт:**
```
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
```

**Выход (LLM → API result):**
- `summary`, `appeal_grounds[]`, `verdict_excerpt`, `speech_verdict_comparison`, `risk_verdict_comparison`, `draft_document`

---

## Использование в коде
См. `app/domain/prompts.py` — функции сборки промптов и связка с входными данными API.
