# AI-анализа - поля и допустимые значения

Документ описывает все поля для AI-анализов:
- `POST /api/case/<uuid>/analyze-materials/`
- `POST /api/case/<uuid>/risks/analyze/`
- `POST /api/case/<uuid>/verdicts/analyze/`
- `POST /api/case/<uuid>/verdict/analyze/`
- `GET /api/case/<uuid>/risks/`
- `GET /api/analysis/<uuid>/status/`
- `GET /api/case/<uuid>/analyses/`

## Общий процесс
1. Запускаете анализ через `POST .../analyze/`.
2. В ответе получаете `analysis_id` и `poll_url`.
3. Проверяете статус через `GET /api/analysis/<analysis_id>/status/`.
4. Получаете результат при статусе `completed`.

## Общие типы и значения
- `analysis_type`:
  - `materials`
  - `risk_analysis`
  - `similar_verdicts`
  - `verdict_analysis`
- `status`:
  - `pending`
  - `processing`
  - `completed`
  - `failed`
- `analysis_id`, `case_id` - UUID (строка).
- Заголовок `X-User-ID` - опционально, строка (для аудита и связки с пользователем).

---

## POST `/api/case/<uuid>/analyze-materials/`
Запуск анализа материалов дела.

### Request body (JSON, опционально)
- `document_ids` - массив UUID документов для анализа. Если не указан, анализируются все документы дела с `ocr_status="completed"`.

### Response (200)
- `success` - `true`
- `analysis_id` - UUID анализа
- `task_id` - строка ID Celery-задачи
- `status` - строка, обычно `pending`
- `poll_url` - строка URL для проверки статуса

### Ошибки
- `404` - дело не найдено
- `400` - неверный JSON

---

## POST `/api/case/<uuid>/risks/analyze/`
Запуск анализа рисков по делу.

### Request body
Не требуется.

### Response (200)
- `success` - `true`
- `analysis_id` - UUID анализа
- `task_id` - строка ID Celery-задачи
- `status` - `pending`
- `poll_url` - URL статуса

### Ошибки
- `404` - дело не найдено

---

## POST `/api/case/<uuid>/verdicts/analyze/`
Запуск анализа аналогичных приговоров.

### Request body
Не требуется.

### Response (200)
- `success` - `true`
- `analysis_id` - UUID анализа
- `task_id` - строка ID Celery-задачи
- `status` - `pending`
- `poll_url` - URL статуса

### Ошибки
- `404` - дело не найдено

---

## POST `/api/case/<uuid>/verdict/analyze/`
Запуск анализа вынесенного приговора (для апелляции).

### Request body
Не требуется.

### Response (200)
- `success` - `true`
- `analysis_id` - UUID анализа
- `task_id` - строка ID Celery-задачи
- `status` - `pending`
- `poll_url` - URL статуса

### Ошибки
- `404` - дело не найдено

---

## GET `/api/analysis/<uuid>/status/`
Проверка статуса анализа.

### Response (200)
- `success` - `true`
- `analysis_id` - UUID анализа
- `case_id` - UUID дела
- `analysis_type` - `materials | risk_analysis | similar_verdicts | verdict_analysis`
- `status` - `pending | processing | completed | failed`
- `processing_time_ms` - время обработки, мс (может быть `null`)
- `ai_model` - строка вида `provider/model` или `null`
- `created_at` - ISO-дата/время
- `result` - присутствует, если `status=completed`
- `error_message` - присутствует, если `status=failed`

### Особенность для `risk_analysis`
Если `analysis_type=risk_analysis` и статус `completed`, поле `result` возвращается в формате `RiskAnalysisResponse` (см. ниже).

---

## GET `/api/case/<uuid>/analyses/`
Список анализов по делу.

### Query params (опционально)
- `type` - фильтр по типу: `materials | risk_analysis | similar_verdicts | verdict_analysis`
- `status` - фильтр по статусу: `pending | processing | completed | failed`

### Response (200)
- `success` - `true`
- `case_id` - UUID дела
- `count` - количество записей
- `analyses` - массив объектов анализа (не более 50)

### Поля элемента `analyses[]`
- `id` - UUID анализа
- `analysis_type` - тип анализа
- `analysis_type_display` - человекочитаемое название
- `status` - статус
- `ai_model` - строка модели или `null`
- `processing_time_ms` - мс или `null`
- `created_at` - ISO-дата/время
- `has_result` - bool (только если `completed`)
- `error_message` - строка (только если `failed`)

---

## GET `/api/case/<uuid>/risks/`
Получение последнего завершенного анализа рисков.

### Response (200) если анализ есть
Возвращается объект `RiskAnalysisResponse` (см. ниже).

### Response (200) если анализа нет
- `success` - `true`
- `case_id` - UUID дела
- `analysis` - `null`
- `message` - строка

---

## RiskAnalysisResponse

### Поля
- `success` - `true`
- `case_id` - UUID дела
- `risks` - массив `RiskItem`
- `high_count` - количество рисков уровня `high`
- `medium_count` - количество рисков уровня `medium`
- `low_count` - количество рисков уровня `low`
- `sources` - объект, обычно `{ "model": "provider/model" }`
- `analysis_date` - дата анализа `YYYY-MM-DD`
- `analysis_id` - UUID анализа
- `processing_time_ms` - время обработки, мс
- `raw_assessment` - объект (оригинальный блок AI, может быть `null`)
- `action_plan` - массив (может быть пустым)
- `comparison_with_guilty` - объект или `null`

---

## RiskItem
- `level` - `high | medium | low`
- `title` - строка
- `text` - строка
- `recommendation` - строка
