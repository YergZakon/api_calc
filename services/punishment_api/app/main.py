"""Точка входа FastAPI-приложения."""

from __future__ import annotations

import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from .api.v1.router import router as v1_router
from .core.config import get_settings
from .core.logging import setup_logging
from .core.tags import OPENAPI_TAGS

setup_logging()
logger = logging.getLogger(__name__)


def _ensure_runtime_paths(reference_file_path: str, data_dir: str) -> None:
    ref_path = Path(reference_file_path)
    if not ref_path.exists():
        raise RuntimeError(f"Reference file does not exist: {ref_path}")

    runtime_dir = Path(data_dir)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    probe = runtime_dir / ".write_test"
    try:
        probe.write_text("ok", encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"DATA_DIR is not writable: {runtime_dir}") from exc
    finally:
        if probe.exists():
            probe.unlink()


def create_app() -> FastAPI:
    settings = get_settings()
    _ensure_runtime_paths(settings.reference_file_path, settings.data_dir)

    fastapi_app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        openapi_tags=OPENAPI_TAGS,
    )
    fastapi_app.include_router(v1_router)
    return fastapi_app


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    logger.info("Swagger: http://%s:%s/docs", settings.APP_HOST, settings.APP_PORT)
    uvicorn.run(
        "services.punishment_api.app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG_MODE,
    )
