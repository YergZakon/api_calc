"""Конфигурация приложения и загрузка настроек из окружения/.env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """Настройки FastAPI-сервиса."""

    api_title: str = "Punishment API"
    api_version: str = "0.2.0"
    API_PREFIX: str = ""

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8080
    DEBUG_MODE: bool = True

    reference_file_path: str = str(PROJECT_ROOT / "справочник_УК_обновленный_2025_06_07_1.txt")
    data_dir: str = "/tmp/punishment_api_data"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    """Возвращает кешированный экземпляр настроек приложения."""

    return Settings()


settings = get_settings()
