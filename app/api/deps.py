"""Dependency-фабрики FastAPI для сервисов и справочника."""

from __future__ import annotations

import os

from app.core.config import get_settings
from app.domain.services.punishment_service import PunishmentService
from app.infrastructure.loaders.reference_loader import get_reference_service


def get_reference():
    """Возвращает инициализированный сервис справочника статей."""
    settings = get_settings()
    os.environ.setdefault("REFERENCE_FILE_PATH", settings.reference_file_path)
    return get_reference_service()


def get_punishment_service() -> PunishmentService:
    """Создаёт доменный сервис расчёта наказаний."""
    return PunishmentService()
