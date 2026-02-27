from __future__ import annotations

from typing import List, Optional, Literal, Dict, Any

from pydantic import BaseModel


class CaseParticipant(BaseModel):
    role: str
    name: str
    birth_date: Optional[str] = None
    sex: Optional[str] = None


class MaterialNode(BaseModel):
    type: Literal["folder", "file"] = "file"
    name: str
    ext: Optional[str] = None
    pages: Optional[int] = None
    ocr: Optional[Literal["ok", "low"]] = None
    date: Optional[str] = None
    children: Optional[List["MaterialNode"]] = None


class TimelineItem(BaseModel):
    date: str
    title: str
    status: Literal["done", "current", "upcoming", "warning", "danger"]
    detail: Optional[str] = None
    countdown: bool = False


class SimilarVerdict(BaseModel):
    article: str
    court: str
    result: str
    similarity: int
    date: str
    decision: Literal["guilty", "acquittal", "return"] = "guilty"


class SimilarVerdictFile(BaseModel):
    id: str
    file_name: str
    mime: str
    similarity: float
    source: str
    text: str
    decision: Optional[Literal["guilty", "acquittal", "return"]] = None


class SimilarVerdictsSearchRequest(BaseModel):
    erdr_number: str
    case_vector: List[float]
    vector_model: Optional[str] = None
    limit: Optional[int] = 10
    min_similarity: Optional[float] = 0.0
    decision: Optional[Literal["guilty", "acquittal", "return"]] = None
    limit_guilty: Optional[int] = None
    limit_acquittal: Optional[int] = None


class Acquittal(BaseModel):
    article: str
    court: str
    result: str
    reason: str
    date: str
    type: Literal["acquittal", "return"]


class NormativeDecree(BaseModel):
    title: str
    subtitle: str
    relevance: Literal["high", "medium", "low"] = "medium"
    summary: Optional[str] = None


class NormsSearchRequest(BaseModel):
    report_text: str
    similar_verdicts_summary: Optional[str] = None


class InterimMaterial(BaseModel):
    type: str
    title: str
    date: str
    status: Optional[Literal["granted", "rejected"]] = None
    icon: str = "📄"
    color: str = "var(--accent)"


class AppealGround(BaseModel):
    title: str
    text: str
    basis: str
    strength: Literal["high", "medium", "low"]


class VerdictResult(BaseModel):
    date: str
    decision: str
    sentence: str
    requested: str
    assigned: str
    difference: str
    appeal_deadline: str
    days_left: int
    appeal_grounds: List[AppealGround]
    recommendation: str


class CaseInfo(BaseModel):
    id: Optional[str] = None
    erdr_number: str
    article: str
    article_title: str
    status: str
    status_label: str
    court: str
    judge: str
    region: str
    unit: str
    start_date: str
    prosecutor: str
    defendant: Optional[str] = None


class PunishmentStats(BaseModel):
    average_term: str
    median_term: str
    conditional_percent: float
    acquittal_percent: float
    return_percent: float
    distribution: Dict[str, Any]


class CaseResponse(BaseModel):
    success: bool = True
    case: CaseInfo
    participants: List[CaseParticipant]
    materials: List[MaterialNode]
    similar_verdicts: List[SimilarVerdict]
    acquittals: List[Acquittal]
    norms: List[NormativeDecree]
    timeline: List[TimelineItem]
    interim_materials: List[InterimMaterial]
    punishment_stats: Optional[PunishmentStats] = None


class VerdictResponse(BaseModel):
    success: bool = True
    case_id: str
    verdict: VerdictResult


class SimilarVerdictsResponse(BaseModel):
    success: bool = True
    case_id: str
    count: int
    verdicts: List[SimilarVerdict]


class SimilarVerdictFilesResponse(BaseModel):
    success: bool = True
    case_id: str
    count: int
    verdicts: List[SimilarVerdictFile]


class AcquittalsResponse(BaseModel):
    success: bool = True
    case_id: str
    count: int
    acquittals: List[Acquittal]


class NormsResponse(BaseModel):
    success: bool = True
    case_id: str
    count: int
    norms: List[NormativeDecree]


class AppealGroundsResponse(BaseModel):
    success: bool = True
    case_id: str
    appeal_grounds: List[AppealGround]
    recommendation: str


class VerdictContent(BaseModel):
    id: str
    decision_type: Optional[str] = None
    decision_type_display: Optional[str] = None
    article: Optional[str] = None
    article_code: Optional[str] = None
    court: Optional[str] = None
    case_number: Optional[str] = None
    decision_date: Optional[str] = None
    result: Optional[str] = None
    reason: Optional[str] = None
    content: Optional[str] = None
    source: Optional[str] = None


class VerdictContentResponse(BaseModel):
    success: bool = True
    verdict: VerdictContent


class VerdictListResponse(BaseModel):
    success: bool = True
    erdr_number: str
    count: int
    verdicts: List[VerdictContent]


MaterialNode.model_rebuild()
