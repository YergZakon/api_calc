"""OpenAPI tags metadata."""

TAG_MATERIALS = "01. Материалы (TXT→Справка)"
TAG_VECTOR = "02. Векторизация справки"
TAG_SIMILAR = "03. Похожие приговоры"
TAG_SIMILAR_ANALYSIS = "04. Анализ приговоров"
TAG_NORMS = "05. НПА"
TAG_RISKS = "06. Анализ рисков"
TAG_CALC = "07. Расчёт наказания"
TAG_SPEECH = "08. Речь ГО"
TAG_VERDICT_GET = "09. Получение приговора"
TAG_VERDICT_ANALYSIS = "10. Анализ приговора / итоговый документ"
TAG_WORKFLOW = "Сквозной сценарий"
TAG_SERVICE = "Служебные"

OPENAPI_TAGS = [
    {
        "name": TAG_MATERIALS,
        "description": "Вход: текстовые документы → выход: справка/summary.",
    },
    {
        "name": TAG_VECTOR,
        "description": "Векторизация справки для поиска практики.",
    },
    {
        "name": TAG_SIMILAR,
        "description": "Поиск похожих приговоров (векторный запрос) и практика.",
    },
    {
        "name": TAG_SIMILAR_ANALYSIS,
        "description": "ИИ‑анализ похожих приговоров.",
    },
    {
        "name": TAG_NORMS,
        "description": "Подбор и анализ НПА по справке.",
    },
    {
        "name": TAG_RISKS,
        "description": "ИИ‑анализ рисков и результаты по делу.",
    },
    {
        "name": TAG_CALC,
        "description": "Калькулятор наказания и история расчётов.",
    },
    {
        "name": TAG_SPEECH,
        "description": "Генерация речи гособвинителя.",
    },
    {
        "name": TAG_VERDICT_GET,
        "description": "Получение приговора (по id или по ЕРДР).",
    },
    {
        "name": TAG_VERDICT_ANALYSIS,
        "description": "Анализ приговора и подготовка итогового документа.",
    },
    {
        "name": TAG_WORKFLOW,
        "description": "Сквозной сценарий (расчёт + речь).",
    },
    {
        "name": TAG_SERVICE,
        "description": "Служебные эндпоинты и справочники.",
    },
]
