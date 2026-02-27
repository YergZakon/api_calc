# ABOUT_PROJECT

## 1) Краткий обзор проекта

Проект представляет собой API-сервис на FastAPI для расчёта диапазонов наказаний по данным статьи и параметрам дела/лица. 
Логика расчёта портирована из FoxPro-правил (в т.ч. расчёт сроков, ограничений и текстовых формулировок), 
а справочные данные подтягиваются из табличного файла `справочник_УК_обновленный_2025_06_07_1.txt`.

---

## 2) Текущее дерево и назначение файлов

### Корень проекта
- `Dockerfile` — контейнеризация сервиса, установка зависимостей, запуск `uvicorn`.
- `справочник_УК_обновленный_2025_06_07_1.txt` — основной справочник статей/санкций для расчётов.

### `services/punishment_api/`
- `__init__.py` — маркер Python-пакета.
- `app.py` — точка входа FastAPI, объявление маршрутов `/health`, `/reference/status`, `/reference/reload`, `/calculate`.
- `schemas.py` — Pydantic-модели запроса/ответа API (`CalculateRequest`, `CalculateResponse` и др.).
- `calculator.py` — orchestration-слой: парсинг/нормализация входного JSON, формирование `FoxProInput`, вызов расчёта и сборка структурированного ответа.
- `foxpro_engine.py` — основной движок бизнес-правил (порт FoxPro-логики), вычисляет массив `aNakaz` и дополнительные признаки.
- `foxpro_dates.py` — утилиты дат с FoxPro-поведенческой совместимостью (`gomonth`, `ddtomy`).
- `reference_loader.py` — загрузка/декодирование/кеширование справочника, выбор актуальной записи статьи на дату преступления.
- `localization.py` — локализация сообщений и словоформ для RU (`setlang`, `dmytorus`, `format_number`).
- `bootstrap.py` — добавляет корень репозитория в `sys.path`.
- `requirements.txt` — зависимости Python.
- `README.md` — описание запуска, endpoint-ов и состава входных полей.

---

## 3) Краткое описание ключевых методов и их роли

## `app.py`
- `health()` — health-check сервиса.
- `reference_status()` — метаданные состояния справочника (источник, путь, количество записей).
- `reference_reload()` — принудительная перезагрузка справочника в памяти.
- `calculate(payload)` — валидация языка, вызов `calculate_from_json`, формирование API-ответа.

## `calculator.py`
- `_parse_gender(value)` — нормализация пола в кодовую форму (`1/2`).
- `_parse_stage(value)` — нормализация стадии преступления в код (`1/2/3`).
- `_build_code(article, part, paragraph)` — построение унифицированного кода статьи из компонентов.
- `_resolve_article_code(...)` — выбор итогового `article_code` (явный код или сборка).
- `_parse_date(value)` — преобразование входного значения в `date`.
- `calculate_from_json(payload)` — главный pipeline: подготовка данных -> поиск статьи -> расчёт -> структурирование результата.
- `_build_structured(a_nakaz)` — преобразование массивного формата `aNakaz` в читаемую JSON-структуру.

## `foxpro_engine.py`
- `FoxProInput` (`@dataclass`) — типизированный контейнер входных параметров расчёта.
- `calculate_count_srk(inp, slvst, lang)` — центральный алгоритм расчёта санкций, дополнительных наказаний и мета-ограничений.
- `_default_anakaz()` — создание базовой 15x13 матрицы результата.
- `_has_value`, `_has_code`, `_val`, `_evl` — служебные функции извлечения/проверки значений.
- `_apply_modifiers`, `_floor2` — применение коэффициентов и округлений.
- `_format_range`, `_format_term`, `_format_range_term` — генерация человекочитаемых строк диапазонов.
- `_between` — проверка диапазона строковых кодов.

## `foxpro_dates.py`
- `gomonth(start_date, months)` — сдвиг даты на месяцы в стиле FoxPro.
- `ddtomy(ld_start, ld_stop, ln_mdy)` — вычисление возраста/месяцев/дней по режимам FoxPro.

## `reference_loader.py`
- `ArticleRecord` (`@dataclass`) — структура одной записи справочника санкций.
- `ReferenceService` — сервис справочника с ленивой загрузкой и кешем.
  - `_ensure_loaded()` — гарантирует однократную загрузку.
  - `reload()` — сброс и повторная загрузка.
  - `get_by_code(code, crime_date)` — выбор подходящей версии статьи по дате.
  - `_get_file_path()`, `_load_from_file()`, `_read_file()` — чтение файла и подготовка контента.
  - `_decode_field()`, `_decode_stat_field()`, `_decode_text_field()` — декодирование «сложной» кодировки источника.
  - `_parse_content()`, `_parse_row()` — парсинг строк файла в `ArticleRecord`.
- `_parse_date(value)` — парсинг даты из справочника `dd.mm.yyyy`.
- `get_reference_service()` — singleton-доступ к экземпляру `ReferenceService`.

## `localization.py`
- `normalize_lang(lang)` — нормализация языка (сейчас поддерживается только `ru`).
- `setlang(message_id, lang)` — выдача локализованной фразы по ID.
- `_form_i`, `_form_d`, `dmytorus(...)` — согласование словоформ дней/месяцев/лет.
- `format_number(value)` — форматирование числа для текстовых диапазонов.

---

## 4) Технические наблюдения по текущей архитектуре

1. Проект уже использует FastAPI, но структура близка к «single-module service»: API, доменная логика и инфраструктура находятся в одном пакете.
2. Главный риск расширяемости — очень большой `foxpro_engine.py` с плотной процедурной логикой.
3. Формат `aNakaz` (15x13 массив) хранит legacy-совместимость, но плохо самодокументируется.
4. Сервис справочника реализован как singleton с in-memory кешем — это удобно для runtime, но усложняет тестирование/подмену зависимостей.
5. Есть жёсткая зависимость от конкретного текстового справочника и формата кодировки.

---

## 5) План приведения к расширяемой FastAPI-структуре

Ниже — целевая структура и поэтапный план без ломки текущего API-контракта.

### 5.1 Целевая структура каталогов

```text
.
├── app/
│   ├── main.py                    # создание FastAPI-приложения
│   ├── api/
│   │   ├── deps.py                # DI-зависимости (reference service, settings)
│   │   └── v1/
│   │       ├── router.py          # агрегатор роутеров
│   │       ├── health.py
│   │       ├── reference.py
│   │       └── calculate.py
│   ├── core/
│   │   ├── config.py              # pydantic-settings
│   │   ├── logging.py
│   │   └── i18n.py                # перенос localization
│   ├── domain/
│   │   ├── models/
│   │   │   ├── calculation.py     # доменные модели входа/выхода
│   │   │   └── reference.py
│   │   ├── services/
│   │   │   └── punishment_service.py
│   │   └── engines/
│   │       ├── foxpro_engine.py
│   │       └── foxpro_dates.py
│   ├── infrastructure/
│   │   ├── repositories/
│   │   │   └── reference_repository.py
│   │   └── loaders/
│   │       └── txt_reference_loader.py
│   ├── schemas/
│   │   ├── request.py
│   │   └── response.py
│   └── utils/
│       └── converters.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── scripts/
│   └── smoke_request.sh
├── pyproject.toml
├── Dockerfile
└── ABOUT_PROJECT.md
```

### 5.2 Этапы рефакторинга

1. **Этап 1 — структурный перенос без изменения поведения**
   - Вынести роуты в `api/v1/*`.
   - Вынести конфигурацию (`REFERENCE_FILE_PATH`, версия API) в `core/config.py`.
   - Сохранить текущие endpoint и схему ответов 1:1.

2. **Этап 2 — разделение domain / infrastructure**
   - `reference_loader.py` разделить на:
     - repository-интерфейс,
     - loader конкретного TXT-формата,
     - сервис уровня domain (`PunishmentService`).
   - Внедрить зависимости через FastAPI `Depends`.

3. **Этап 3 — декомпозиция расчётного движка**
   - Разбить `calculate_count_srk` на подмодули по видам наказаний:
     - `main_punishments.py`
     - `additional_punishments.py`
     - `meta_rules.py`
   - Ввести константы/enum для индексов `aNakaz`, чтобы убрать «магические числа».

4. **Этап 4 — контракты и тесты**
   - Unit-тесты на утилиты дат/локализации.
   - Golden tests на набор входов и ожидаемый `aNakaz`.
   - API integration tests (`TestClient`) для `/calculate`, `/reference/status`.

5. **Этап 5 — наблюдаемость и эксплуатация**
   - Структурированное логирование (request id, статья, стадия, время расчёта).
   - Метрики (время расчёта, % ошибок, частота `article_not_found`).
   - Подготовить `/health/ready` с проверкой доступности справочника.

6. **Этап 6 — расширяемость**
   - Версионирование API (`/api/v1`, `/api/v2`).
   - Поддержка нескольких источников справочника (txt/csv/db) через адаптеры.
   - Возможность добавления новых языков в `i18n` без изменения engine-ядра.

---

## 6) Минимальный backlog (приоритет)

### P0 (критично)
- Разбить `app.py` на router-модули и добавить dependency injection.
- Вынести настройки в `pydantic-settings`.
- Зафиксировать контракт `CalculateResponse` тестами.

### P1 (важно)
- Декомпозировать `foxpro_engine.py` и убрать магические индексы.
- Добавить unit/integration тесты и smoke-скрипт.

### P2 (желательно)
- Внедрить метрики и structured logging.
- Подготовить миграцию на альтернативное хранилище справочника.

---

## 7) Ожидаемый результат после реорганизации

- Кодовая база станет модульной и поддерживаемой.
- Появится предсказуемый слой зависимостей и тестируемость каждого модуля.
- Добавление новых правил/источников справочника/языков станет эволюционным, без переписывания API-слоя.
