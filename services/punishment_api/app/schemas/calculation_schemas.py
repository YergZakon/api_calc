from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class CalculationListItem(BaseModel):
    id: str
    article_code: str
    article_name: str
    formatted_result: str
    created_at: str


class CalculationHistoryResponse(BaseModel):
    success: bool = True
    count: int
    limit: int
    offset: int
    calculations: List[CalculationListItem]


class CalculationDetail(BaseModel):
    id: str
    case_id: Optional[str] = None
    article_code: str
    article_name: str
    min_months: Optional[float] = None
    max_months: Optional[float] = None
    formatted_result: str
    calculation_log: List[Any]
    modifiers_applied: List[Any]
    warnings: List[Any]
    created_at: str
    created_by: Optional[str] = None
    raw_response: Dict[str, Any] = {}


class CalculationDetailResponse(BaseModel):
    success: bool = True
    calculation: CalculationDetail
