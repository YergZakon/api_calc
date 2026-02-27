"""Адаптер для инициализации загрузчика TXT-справочника."""

from __future__ import annotations

from app.infrastructure.loaders.reference_loader import ReferenceService


class TxtReferenceLoader:
    """Тонкая обёртка вокруг `ReferenceService` для TXT-источника."""

    def __init__(self, file_path: str | None = None):
        """Создаёт сервис загрузки справочника из заданного пути."""
        self._service = ReferenceService(file_path=file_path)

    def service(self) -> ReferenceService:
        """Возвращает внутренний сервис доступа к справочнику."""
        return self._service
