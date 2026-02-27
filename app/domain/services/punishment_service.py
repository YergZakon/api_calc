"""Фасад доменного сервиса расчёта наказаний."""

from __future__ import annotations

from app.domain.services.calculator import calculate_from_json


class PunishmentService:
    """Доменный сервис, делегирующий расчёт в orchestration-слой."""

    def calculate(self, payload: dict) -> tuple[list[list], dict]:
        """Рассчитывает наказания по входному JSON-подобному payload."""
        return calculate_from_json(payload)
