"""Репозиторий-адаптер поверх сервиса справочника."""

from __future__ import annotations

from datetime import date

from app.infrastructure.loaders.reference_loader import ArticleRecord, ReferenceService


class ReferenceRepository:
    """Фасад репозитория для поиска статей и метаданных справочника."""

    def __init__(self, service: ReferenceService):
        """Принимает сервис загрузки/поиска справочника."""
        self._service = service

    def get_by_code(self, code: str, crime_date: date) -> ArticleRecord | None:
        """Возвращает запись статьи по коду и дате преступления."""
        return self._service.get_by_code(code=code, crime_date=crime_date)

    def reload(self) -> None:
        """Перезагружает данные справочника."""
        self._service.reload()

    @property
    def source(self) -> str:
        """Текущий источник данных справочника."""
        return self._service.source

    @property
    def count(self) -> int:
        """Количество записей в справочнике."""
        return self._service.count

    @property
    def file_path(self) -> str:
        """Путь к файлу справочника."""
        return self._service.file_path
