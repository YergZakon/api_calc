from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .calculator import calculate_from_json
from .localization import normalize_lang
from .reference_loader import get_reference_service
from .schemas import (
    CalculateRequest,
    CalculateResponse,
    HealthResponse,
    ReferenceStatusResponse,
)

app = FastAPI(title="Punishment API", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.get("/reference/status", response_model=ReferenceStatusResponse)
def reference_status() -> ReferenceStatusResponse:
    ref = get_reference_service()
    return ReferenceStatusResponse(source=ref.source, count=ref.count, file_path=ref.file_path)


@app.post("/reference/reload")
def reference_reload() -> dict:
    ref = get_reference_service()
    ref.reload()
    return {"status": "reloaded", "count": ref.count, "source": ref.source}


@app.post("/calculate", response_model=CalculateResponse)
def calculate(payload: CalculateRequest) -> CalculateResponse:
    lang = normalize_lang(payload.lang)
    if lang != "ru":
        raise HTTPException(status_code=400, detail="Only 'ru' is supported for now")

    if hasattr(payload, "model_dump"):
        data = payload.model_dump()
    else:
        data = payload.dict()

    aNakaz, structured = calculate_from_json(data)

    return CalculateResponse(
        lang=lang,
        aNakaz=aNakaz,
        structured=structured,
    )
