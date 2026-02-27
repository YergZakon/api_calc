"""Вспомогательные преобразователи входных данных API."""

from __future__ import annotations

from datetime import date


def to_payload_dict(model) -> dict:
    """Преобразует Pydantic-модель (v1/v2) в словарь payload."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def resolve_date(value: date | None, fallback: date) -> date:
    """Возвращает `value`, если задано, иначе дату по умолчанию `fallback`."""
    return value or fallback
