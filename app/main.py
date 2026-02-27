"""Точка входа FastAPI-приложения для расчёта наказаний."""

from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.logging import setup_logging

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Создаёт и конфигурирует экземпляр FastAPI с роутами API v1."""
    app_settings = get_settings()
    fastapi_app = FastAPI(title=app_settings.api_title, version=app_settings.api_version)
    fastapi_app.include_router(v1_router)
    return fastapi_app


app = create_app()

if __name__ == "__main__":
    settings = get_settings()
    logger.info(f"Swagger: http://{settings.APP_HOST}:{settings.APP_PORT}/docs")
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG_MODE
    )
