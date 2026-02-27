"""HTTP-обработчики статуса и перезагрузки справочника."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_reference
from app.schemas.response import ReferenceStatusResponse
from app.infrastructure.loaders.reference_loader import ReferenceService

router = APIRouter()


@router.get("/reference/status", response_model=ReferenceStatusResponse)
def reference_status(ref: ReferenceService = Depends(get_reference)) -> ReferenceStatusResponse:
    """Возвращает источник, количество и путь к текущему справочнику."""
    return ReferenceStatusResponse(source=ref.source, count=ref.count, file_path=ref.file_path)


@router.post("/reference/reload")
def reference_reload(ref: ReferenceService = Depends(get_reference)) -> dict:
    """Принудительно перечитывает справочник из источника."""
    ref.reload()
    return {"status": "reloaded", "count": ref.count, "source": ref.source}
