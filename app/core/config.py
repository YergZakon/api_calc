"""Конфигурация приложения и загрузка настроек из окружения/.env."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

model_config = SettingsConfigDict(
    env_file=str(BASE_DIR / ".env"),
    env_file_encoding="utf-8"
)

class Settings(BaseSettings):
    """Настройки FastAPI-сервиса и пути к справочнику санкций."""
    api_title: str = "Punishment API"
    api_version: str = "0.1.0"
    reference_file_path: str = str(
        Path(__file__).resolve().parents[2] / "reference_uk_2025_06_07.txt"
    )
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 9000
    DEBUG_MODE: bool = True
    API_PREFIX: str = "/api/v1"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8"
    )

@lru_cache
def get_settings() -> Settings:
    """Возвращает кешированный экземпляр настроек приложения."""
    return Settings()

settings = get_settings()
