from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PersonIn(BaseModel):
    birth_date: Optional[date] = Field(default=None)
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


class CrimeIn(BaseModel):
    crime_date: Optional[date] = Field(default=None)
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


class CalculateRequest(BaseModel):
    lang: str = Field(default="ru")
    calc_date: Optional[date] = Field(default=None, description="Override calculation date (server date)")
    person: PersonIn
    crime: CrimeIn


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


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "punishment-api"
    version: str = "0.1.0"
