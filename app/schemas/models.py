"""Pydantic-схемы запросов и ответов Punishment API."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PersonIn(BaseModel):
    """Входные данные о лице (персональные и служебные признаки)."""

    birth_date: Optional[date] = Field(default=None, description="Дата рождения лица (FS1R13P1)")
    gender: Optional[str] = Field(default=None, description="Пол (FS1R15P1): 1=male, 2=female, также male/female")
    is_recidivist: Optional[bool] = Field(default=False, description="Признак рецидива")
    has_plea_agreement: Optional[bool] = Field(default=False, description="Наличие процессуального соглашения")

    # Extra fields for future FoxPro parity (not used yet)
    citizenship: Optional[str] = Field(default=None, description="Гражданство (FS1R17P1)")
    dependents: Optional[str] = Field(default=None, description="Коды иждивенцев (FS1R21P1), через запятую")
    additional_marks: Optional[str] = Field(default=None, description="Дополнительные признаки (FS1R231P1), через запятую")
    special_status: Optional[str] = Field(default=None, description="Специальный статус лица (резерв)")
    conviction_type: Optional[str] = Field(default=None, description="Тип осуждения (резерв)")
    fs1r041p1: Optional[str] = Field(default=None, description="Флаг спецпроизводства FS1R041P1")
    fs1r042p1: Optional[str] = Field(default=None, description="Флаг спецпроизводства FS1R042P1")
    fs1r23p1: Optional[str] = Field(default=None, description="Служебное поле формы FS1R23P1")
    fs1r26p1: Optional[str] = Field(default=None, description="Служебное поле формы FS1R26P1")


class CrimeIn(BaseModel):
    """Входные данные по событию преступления и параметрам квалификации."""

    crime_date: Optional[date] = Field(default=None, description="Дата совершения преступления (FS1R51P2)")
    article_code: Optional[str] = Field(default=None, description="7-значный код статьи в формате AAASSPP (FS1R54P1)")
    article: Optional[str] = Field(default=None, description="Номер статьи, если article_code не передан (например, 188)")
    part: Optional[str] = Field(default=None, description="Часть статьи при сборке article_code (например, 1, 3)")
    paragraph: Optional[str] = Field(default=None, description="Пункт статьи; может использоваться как article_parts")

    article_parts: Optional[str] = Field(default="", description="Пункты/части статьи (FS1R54P2), строка через запятую")
    crime_stage: Optional[str] = Field(
        default="3",
        description="Стадия преступления (FS1R56P1): 1=приготовление, 2=покушение, 3=оконченное",
    )
    has_mitigating: Optional[bool] = Field(
        default=False,
        description="Есть смягчающие обстоятельства; если true и mitigating пусто, используется код '1'",
    )
    has_aggravating: Optional[bool] = Field(
        default=False,
        description="Есть отягчающие обстоятельства; если true и aggravating пусто, используется код '1'",
    )

    # Extra fields for future FoxPro parity (not used yet)
    special_condition: Optional[str] = Field(
        default=None,
        description="Особые условия (FS1R573P1): '', 01, 02, 03, 04, 05",
    )
    mitigating: Optional[str] = Field(default=None, description="Коды смягчающих (FS1R571P1), через запятую")
    aggravating: Optional[str] = Field(default=None, description="Коды отягчающих (FS1R572P1), через запятую")
    fs1r56p1: Optional[str] = Field(default=None, description="Поле формы FS1R56P1 (альтернатива crime_stage)")
    fs1r571p1: Optional[str] = Field(default=None, description="Поле формы FS1R571P1 (альтернатива mitigating)")
    fs1r572p1: Optional[str] = Field(default=None, description="Поле формы FS1R572P1 (альтернатива aggravating)")
    fs1r573p1: Optional[str] = Field(default=None, description="Поле формы FS1R573P1 (альтернатива special_condition)")
    fs1r041p1: Optional[str] = Field(default=None, description="Флаг спецпроизводства FS1R041P1")
    fs1r042p1: Optional[str] = Field(default=None, description="Флаг спецпроизводства FS1R042P1")
    fs1r23p1: Optional[str] = Field(default=None, description="Служебное поле формы FS1R23P1")
    fs1r26p1: Optional[str] = Field(default=None, description="Служебное поле формы FS1R26P1")


class CalculateRequest(BaseModel):
    """Тело запроса на расчёт наказания."""

    lang: str = Field(default="ru", description="Язык ответа (сейчас поддерживается только ru)")
    calc_date: Optional[date] = Field(default=None, description="Дата расчёта вместо серверной даты")
    person: PersonIn = Field(description="Данные о лице")
    crime: CrimeIn = Field(description="Данные о преступлении и квалификации")


class PunishmentItem(BaseModel):
    """Унифицированный элемент результата по одному виду наказания."""

    is_applicable: bool = Field(description="Признак применимости наказания")
    min_value: float = Field(default=0, description="Минимальное значение диапазона")
    max_value: float = Field(default=0, description="Максимальное значение диапазона")
    formatted_text: str = Field(default="", description="Готовая человекочитаемая формулировка")
    is_mandatory: Optional[bool] = Field(default=None, description="Обязательность дополнительного наказания")
    min_years: Optional[int] = Field(default=None, description="Минимум: годы")
    min_months: Optional[int] = Field(default=None, description="Минимум: месяцы")
    min_days: Optional[int] = Field(default=None, description="Минимум: дни")
    max_years: Optional[int] = Field(default=None, description="Максимум: годы")
    max_months: Optional[int] = Field(default=None, description="Максимум: месяцы")
    max_days: Optional[int] = Field(default=None, description="Максимум: дни")


class StructuredResponse(BaseModel):
    """Читаемая структура ответа с наказаниями и мета-признаками."""

    punishments: Dict[str, Any] = Field(description="Основные виды наказаний")
    additional_punishments: Dict[str, Any] = Field(description="Дополнительные виды наказаний")
    meta: Dict[str, Any] = Field(description="Мета-признаки расчёта")


class CalculateResponse(BaseModel):
    """Полный ответ API: язык, массив `aNakaz` и структурированный блок."""

    lang: str = Field(description="Язык ответа")
    aNakaz: List[List[Any]] = Field(description="Строгий массив 15x13 с результатами и внутренними метками")
    structured: StructuredResponse = Field(description="Читаемая структурированная форма результата")


class ReferenceStatusResponse(BaseModel):
    """Ответ эндпоинта статуса справочника."""

    source: str = Field(description="Источник данных справочника")
    count: int = Field(description="Количество статей, загруженных в память")
    file_path: str = Field(description="Путь к файлу справочника")


class HealthResponse(BaseModel):
    """Ответ health-check эндпоинта."""

    status: str = Field(default="ok", description="Статус сервиса")
    service: str = Field(default="punishment-api", description="Имя сервиса")
    version: str = Field(default="0.1.0", description="Версия API")
