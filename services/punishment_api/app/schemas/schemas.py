from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


def _parse_iso_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        value = str(int(value))
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError("Неверный формат даты. Требуется YYYY-MM-DD") from exc
    raise ValueError("Неверный формат даты. Требуется YYYY-MM-DD")


class PersonIn(BaseModel):
    birth_date: Optional[date] = Field(default=None, description="Дата рождения (YYYY-MM-DD)")
    gender: Optional[str] = Field(default=None, description="1=male, 2=female, or male/female")
    is_recidivist: Optional[bool] = Field(default=False)
    has_plea_agreement: Optional[bool] = Field(default=False)

    # Extra fields for future FoxPro parity (not used yet)
    citizenship: Optional[str] = None
    dependents: Optional[str] = Field(default=None, description="FS1R21P1 codes, comma-separated")
    additional_marks: Optional[str] = Field(default=None, description="FS1R231P1 codes, comma-separated")
    special_status: Optional[str] = None
    conviction_type: Optional[str] = None
    fs1r041p1: Optional[str] = None
    fs1r042p1: Optional[str] = None
    fs1r23p1: Optional[str] = None
    fs1r26p1: Optional[str] = None

    @field_validator("birth_date", mode="before")
    @classmethod
    def _validate_birth_date(cls, value: Any) -> Optional[date]:
        return _parse_iso_date(value)


class CrimeIn(BaseModel):
    crime_date: Optional[date] = Field(default=None, description="Дата преступления (YYYY-MM-DD)")
    article_code: Optional[str] = Field(default=None)
    article: Optional[str] = Field(default=None)
    part: Optional[str] = Field(default=None)
    paragraph: Optional[str] = Field(default=None)

    article_parts: Optional[str] = Field(default="")
    crime_stage: Optional[str] = Field(default="3")  # 1/2/3 or completed/attempt/preparation
    has_mitigating: Optional[bool] = Field(default=False)
    has_aggravating: Optional[bool] = Field(default=False)

    # Extra fields for future FoxPro parity (not used yet)
    special_condition: Optional[str] = None
    mitigating: Optional[str] = None
    aggravating: Optional[str] = None
    fs1r56p1: Optional[str] = None
    fs1r571p1: Optional[str] = None
    fs1r572p1: Optional[str] = None
    fs1r573p1: Optional[str] = None
    fs1r041p1: Optional[str] = None
    fs1r042p1: Optional[str] = None
    fs1r23p1: Optional[str] = None
    fs1r26p1: Optional[str] = None

    @field_validator("crime_date", mode="before")
    @classmethod
    def _validate_crime_date(cls, value: Any) -> Optional[date]:
        return _parse_iso_date(value)


class CalculateRequest(BaseModel):
    lang: str = Field(default="ru")
    calc_date: Optional[date] = Field(
        default=None,
        description="Дата расчёта (YYYY-MM-DD, override server date)",
    )
    person: PersonIn
    crime: CrimeIn

    @field_validator("calc_date", mode="before")
    @classmethod
    def _validate_calc_date(cls, value: Any) -> Optional[date]:
        return _parse_iso_date(value)


class PunishmentItem(BaseModel):
    is_applicable: bool
    min_value: float = 0
    max_value: float = 0
    formatted_text: str = ""
    is_mandatory: Optional[bool] = None
    min_years: Optional[int] = None
    min_months: Optional[int] = None
    min_days: Optional[int] = None
    max_years: Optional[int] = None
    max_months: Optional[int] = None
    max_days: Optional[int] = None


class StructuredResponse(BaseModel):
    punishments: Dict[str, Any]
    additional_punishments: Dict[str, Any]
    meta: Dict[str, Any]


class CalculateResponse(BaseModel):
    lang: str
    aNakaz: List[List[Any]]
    structured: StructuredResponse


class ReferenceStatusResponse(BaseModel):
    source: str
    count: int
    file_path: str


class VectorizeRequest(BaseModel):
    report_text: str = Field(description="Текст справки по делу")
    vector_model: Optional[str] = Field(default="mock-embedding-v1")


class VectorizeResponse(BaseModel):
    success: bool = True
    vector_model: str
    vector: List[float]


class ArticleInfo(BaseModel):
    code: str
    name: str
    severity: str
    imprisonment_min: float
    imprisonment_max: float
    is_excluded: bool
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class ArticleInfoResponse(BaseModel):
    success: bool = True
    article: ArticleInfo


class ErrorResponse(BaseModel):
    success: bool = False
    error: str


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "punishment-api"
    version: str = "0.2.0"


class ReferenceReloadResponse(BaseModel):
    status: str
    count: int
    source: str


class WorkflowResponse(BaseModel):
    success: bool = True
    calculation_id: str
    calculation: Dict[str, Any]
    speech_id: Optional[str] = None
    task_id: Optional[str] = None
    speech_status: Optional[str] = None
    poll_url: Optional[str] = None
