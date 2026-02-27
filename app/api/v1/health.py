"""HTTP health-check эндпоинт."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.response import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Возвращает базовый статус готовности сервиса."""
    return HealthResponse()
