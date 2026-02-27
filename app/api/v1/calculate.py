"""HTTP-обработчик расчёта наказаний."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_punishment_service
from app.core.i18n import normalize_lang
from app.domain.services.punishment_service import PunishmentService
from app.schemas.request import CalculateRequest
from app.schemas.response import CalculateResponse
from app.utils.converters import to_payload_dict

router = APIRouter()


@router.post("/calculate", response_model=CalculateResponse)
def calculate(payload: CalculateRequest, service: PunishmentService = Depends(get_punishment_service)) -> CalculateResponse:
    """Валидирует язык и возвращает рассчитанный массив `aNakaz` и structured-ответ."""
    lang = normalize_lang(payload.lang)
    if lang != "ru":
        raise HTTPException(status_code=400, detail="Only 'ru' is supported for now")

    a_nakaz, structured = service.calculate(to_payload_dict(payload))

    return CalculateResponse(
        lang=lang,
        aNakaz=a_nakaz,
        structured=structured,
    )
