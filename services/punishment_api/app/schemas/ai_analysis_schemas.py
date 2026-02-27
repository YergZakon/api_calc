from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentInput(BaseModel):
    name: str
    text: str = Field(default="")


class AnalyzeMaterialsRequest(BaseModel):
    erdr_number: Optional[str] = None
    documents: List[DocumentInput]
    mode: Optional[str] = "async"


class GenericAnalyzeResponse(BaseModel):
    success: bool = True
    analysis_id: str
    task_id: str
    status: str
    poll_url: str


class AnalyzeMaterialsResponse(BaseModel):
    success: bool = True
    erdr_number: str
    analysis_id: str
    task_id: str
    status: str
    poll_url: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class AnalyzeRisksRequest(BaseModel):
    erdr_number: Optional[str] = None
    report_text: str
    similar_verdicts_summary: str
    norms_summary: str
    mode: Optional[str] = "async"


class AnalyzeRisksResponse(BaseModel):
    success: bool = True
    erdr_number: str
    analysis_id: str
    task_id: str
    status: str
    poll_url: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class AnalyzeSimilarVerdictsRequest(BaseModel):
    verdicts: List[Dict[str, Any]]
    case_info: Optional[Dict[str, Any]] = None
    mode: Optional[str] = Field(default="async", description="async | sync")


class AnalyzeVerdictRequest(BaseModel):
    verdict_text: str
    original_request: Optional[Dict[str, Any]] = None
    speech_text: Optional[str] = None
    risk_analysis_result: Optional[Dict[str, Any]] = None
    draft_type: Optional[str] = Field(default="auto", description="agreement | appeal | auto")
    mode: Optional[str] = Field(default="async", description="async | sync")


class VerdictAnalyzeResponse(BaseModel):
    success: bool = True
    analysis_id: str
    case_id: str
    analysis_type: str
    status: str
    task_id: Optional[str] = None
    poll_url: Optional[str] = None
    processing_time_ms: Optional[int] = None
    ai_model: Optional[str] = None
    created_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class SimilarVerdictsAnalyzeResponse(BaseModel):
    success: bool = True
    analysis_id: str
    case_id: str
    analysis_type: str
    status: str
    task_id: Optional[str] = None
    poll_url: Optional[str] = None
    processing_time_ms: Optional[int] = None
    ai_model: Optional[str] = None
    created_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class AnalysisStatusResponse(BaseModel):
    success: bool = True
    analysis_id: str
    case_id: str
    analysis_type: str
    status: str
    processing_time_ms: Optional[int] = None
    ai_model: Optional[str] = None
    created_at: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class AnalysisListItem(BaseModel):
    id: str
    analysis_type: str
    analysis_type_display: str
    status: str
    ai_model: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: str
    has_result: Optional[bool] = None
    error_message: Optional[str] = None


class CaseAnalysesResponse(BaseModel):
    success: bool = True
    case_id: str
    count: int
    analyses: List[AnalysisListItem]


class ReportLatestResponse(BaseModel):
    success: bool = True
    erdr_number: str
    analysis_id: str
    created_at: str
    result: Dict[str, Any]


class RiskItem(BaseModel):
    level: str
    title: str
    text: str
    recommendation: str


class RiskAnalysisResponse(BaseModel):
    success: bool = True
    case_id: str
    risks: List[RiskItem]
    high_count: int
    medium_count: int
    low_count: int
    sources: Dict[str, Any]
    analysis_date: str
    analysis_id: Optional[str] = None
    processing_time_ms: Optional[int] = None
    raw_assessment: Optional[Dict[str, Any]] = None
    action_plan: Optional[List[Dict[str, Any]]] = None
    comparison_with_guilty: Optional[Dict[str, Any]] = None
