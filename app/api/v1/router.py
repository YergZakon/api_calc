"""Агрегатор роутеров API версии v1."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.calculate import router as calculate_router
from app.api.v1.health import router as health_router
from app.api.v1.reference import router as reference_router
from app.core.config import settings



router = APIRouter()
router.include_router(health_router, prefix=settings.API_PREFIX)
router.include_router(reference_router, prefix=settings.API_PREFIX)
router.include_router(calculate_router, prefix=settings.API_PREFIX)
