from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GenerateSpeechRequest(BaseModel):
    erdr_number: str = Field(description="Номер ЕРДР (15 цифр)")
    article_code: str = Field(description="Код статьи из справочника (например, 1880003)")
    fio: str = Field(description="ФИО подсудимого")
    report_text: str = Field(description="Текст справки по делу (из анализа материалов)")
    calculation_result: Dict[str, Any] = Field(description="Полный результат /calculate")
    similar_verdicts_summary: Optional[str] = Field(default=None, description="Сводка по похожим приговорам")
    norms_summary: Optional[str] = Field(default=None, description="Сводка по НПА")
    mode: str = Field(default="async", description="async | sync")


class GenerateSpeechResponse(BaseModel):
    success: bool = True
    speech_id: str
    status: str
    task_id: Optional[str] = None
    poll_url: Optional[str] = None
    version: Optional[int] = None
    content: Optional[str] = None


class SpeechStatusResponse(BaseModel):
    success: bool = True
    speech_id: str
    status: str
    version: int
    content: Optional[str] = None


class SpeechVersionItem(BaseModel):
    id: str
    version_number: int
    created_at: str
    created_by: Optional[str] = None
    ai_model: Optional[str] = None
    generation_time_ms: Optional[int] = None


class SpeechVersionsResponse(BaseModel):
    success: bool = True
    speech_id: str
    current_version: int
    versions: List[SpeechVersionItem]


class SpeechVersionContent(BaseModel):
    id: str
    version_number: int
    content: str
    created_at: str
    created_by: Optional[str] = None
    ai_model: Optional[str] = None
    generation_time_ms: Optional[int] = None


class SpeechVersionContentResponse(BaseModel):
    success: bool = True
    version: SpeechVersionContent
