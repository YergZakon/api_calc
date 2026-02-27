"""Агрегатор роутеров API версии v1."""

from __future__ import annotations

from fastapi import APIRouter

from .routes import router as routes_router
from ...core.config import settings

router = APIRouter()
router.include_router(routes_router, prefix=settings.API_PREFIX)
