from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Body, File, Header, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from ...core.i18n import normalize_lang
from ...core.tags import (
    TAG_CALC,
    TAG_MATERIALS,
    TAG_NORMS,
    TAG_RISKS,
    TAG_SERVICE,
    TAG_SIMILAR,
    TAG_SIMILAR_ANALYSIS,
    TAG_SPEECH,
    TAG_VECTOR,
    TAG_VERDICT_ANALYSIS,
    TAG_VERDICT_GET,
    TAG_WORKFLOW,
)
from ...domain.services.ai_analysis_service import (
    ANALYSIS_TYPE_DISPLAY,
    build_risk_analysis_response,
    run_analysis,
    start_analysis,
)
from ...domain.services.article_parser import ArticleParser, parse_article
from ...domain.services.calculator import calculate_from_json
from ...domain.services.speech_service import run_speech, start_speech
from ...infrastructure.loaders.reference_loader import get_reference_service
from ...infrastructure.mock_data import (
    MOCK_ACQUITTALS,
    MOCK_NORMS,
    MOCK_SIMILAR_VERDICT_FILES,
    MOCK_SIMILAR_VERDICTS,
    MOCK_VERDICT_CONTENT,
    MOCK_VERDICT_LIST,
    get_full_case_response,
    get_risk_analysis_response,
    get_verdict_response,
)
from ...infrastructure.storage.ai_analysis_storage import get_analysis_store
from ...infrastructure.storage.calculation_storage import get_calculation_store
from ...infrastructure.storage.speech_storage import get_speech_store
from ...schemas.ai_analysis_schemas import (
    AnalyzeMaterialsRequest,
    AnalyzeMaterialsResponse,
    AnalyzeRisksRequest,
    AnalyzeRisksResponse,
    AnalyzeSimilarVerdictsRequest,
    AnalyzeVerdictRequest,
    AnalysisStatusResponse,
    CaseAnalysesResponse,
    GenericAnalyzeResponse,
    ReportLatestResponse,
    RiskAnalysisResponse,
    SimilarVerdictsAnalyzeResponse,
    VerdictAnalyzeResponse,
)
from ...schemas.calculation_schemas import CalculationDetailResponse, CalculationHistoryResponse
from ...schemas.case_schemas import (
    AcquittalsResponse,
    AppealGroundsResponse,
    CaseResponse,
    NormsResponse,
    NormsSearchRequest,
    SimilarVerdictFilesResponse,
    SimilarVerdictsSearchRequest,
    SimilarVerdictsResponse,
    VerdictListResponse,
    VerdictContentResponse,
    VerdictResponse,
)
from ...schemas.schemas import (
    ArticleInfoResponse,
    CalculateRequest,
    CalculateResponse,
    ErrorResponse,
    HealthResponse,
    ReferenceReloadResponse,
    ReferenceStatusResponse,
    VectorizeRequest,
    VectorizeResponse,
    WorkflowResponse,
)
from ...schemas.speech_schemas import (
    GenerateSpeechRequest,
    GenerateSpeechResponse,
    SpeechStatusResponse,
    SpeechVersionContentResponse,
    SpeechVersionsResponse,
)
router = APIRouter()


_SEVERITY_NAMES = {
    0: "MINOR",
    1: "SMALL",
    2: "MEDIUM",
    3: "SERIOUS",
    4: "ESPECIALLY_SERIOUS",
}

_EXCLUDED_MARKERS = (
    "(Исключена)",
    "(Исключен",
    "(8A:;NG5=0)",
    "(8A:;NG5=",
    "Исключена",
    "Исключен",
)


def _parse_severity(value: str) -> str:
    try:
        severity = int(str(value).strip())
    except ValueError:
        severity = 0
    severity = max(0, min(severity, 4))
    return _SEVERITY_NAMES.get(severity, "MINOR")


def _parse_float(value: str) -> float:
    if value is None:
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    clean = "".join(ch for ch in text if ch.isdigit() or ch in ".-")
    if not clean or clean in {"-", ".", "-.", ".-"}:
        return 0.0
    try:
        return float(clean)
    except ValueError:
        return 0.0


def _is_excluded(stat: str) -> bool:
    if not stat:
        return False
    return any(marker in stat for marker in _EXCLUDED_MARKERS)


def _validate_erdr(value: str) -> bool:
    return bool(value and value.isdigit() and len(value) == 15)


def _vectorize_text(text: str, dim: int = 128) -> list[float]:
    import hashlib
    import random

    seed = int(hashlib.md5(text.encode("utf-8", errors="ignore")).hexdigest()[:8], 16)
    rng = random.Random(seed)
    return [round(rng.uniform(-1, 1), 6) for _ in range(dim)]


def _ensure_text_file(file: UploadFile) -> str:
    filename = (file.filename or "").lower()
    if file.content_type and not file.content_type.startswith("text/"):
        if not filename.endswith(".txt"):
            raise ValueError("Недопустимый формат документа, требуется текст")

    raw = file.file.read()
    if not raw:
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return raw.decode("cp1251")
        except UnicodeDecodeError as exc:
            raise ValueError("Недопустимый формат документа, требуется текст") from exc


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=[TAG_SERVICE],
    summary="Health check",
)
def health() -> HealthResponse:
    return HealthResponse()


@router.get(
    "/api/health/",
    response_model=HealthResponse,
    tags=[TAG_SERVICE],
    summary="Health check (alias)",
)
def health_alias() -> HealthResponse:
    return HealthResponse()


@router.get(
    "/reference/status",
    response_model=ReferenceStatusResponse,
    tags=[TAG_SERVICE],
    summary="Reference status",
)
def reference_status() -> ReferenceStatusResponse:
    ref = get_reference_service()
    return ReferenceStatusResponse(source=ref.source, count=ref.count, file_path=ref.file_path)


@router.post(
    "/reference/reload",
    response_model=ReferenceReloadResponse,
    tags=[TAG_SERVICE],
    summary="Reload reference",
    responses={400: {"model": ErrorResponse}},
)
def reference_reload() -> ReferenceReloadResponse:
    ref = get_reference_service()
    ref.reload()
    return ReferenceReloadResponse(status="reloaded", count=ref.count, source=ref.source)


@router.post(
    "/api/vectorize/",
    response_model=VectorizeResponse,
    tags=[TAG_VECTOR],
    summary="Vectorize case report (mock)",
    responses={400: {"model": ErrorResponse}},
)
def vectorize(payload: VectorizeRequest) -> VectorizeResponse | JSONResponse:
    if hasattr(payload, "model_dump"):
        data = payload.model_dump(mode="json")
    else:
        data = payload.dict()
    report_text = str(data.get("report_text") or "").strip()
    if not report_text:
        return JSONResponse(status_code=400, content={"success": False, "error": "report_text обязателен"})
    vector = _vectorize_text(report_text)
    model = data.get("vector_model") or "mock-embedding-v1"
    return VectorizeResponse(vector_model=model, vector=vector)


@router.post(
    "/calculate",
    response_model=CalculateResponse,
    tags=[TAG_CALC],
    summary="Calculate punishment",
    responses={400: {"model": ErrorResponse}},
)
def calculate(
    payload: CalculateRequest,
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
) -> CalculateResponse:
    lang = normalize_lang(payload.lang)
    if lang != "ru":
        raise HTTPException(status_code=400, detail="Only 'ru' is supported for now")

    if hasattr(payload, "model_dump"):
        data = payload.model_dump(mode="json")
    else:
        data = payload.dict()

    aNakaz, structured = calculate_from_json(data)

    # Store calculation history
    store = get_calculation_store()
    crime = data.get("crime", {}) or {}
    article_code = str(crime.get("article_code") or "").strip()
    if not article_code and crime.get("article"):
        article_text = f"ст. {crime.get('article')}"
        if crime.get("part"):
            article_text += f" ч.{crime.get('part')}"
        parsed = parse_article(article_text)
        if parsed and parsed.code:
            article_code = parsed.code
    if article_code.isdigit() and len(article_code) < 7:
        article_code = article_code.zfill(7)

    article_name = ""
    if article_code:
        ref = get_reference_service()
        article = ref.get_by_code(article_code, date.today())
        if article and article.stat:
            article_name = article.stat

    imprisonment = aNakaz[5] if len(aNakaz) > 5 else [False, 0, 0, ""]
    min_months = imprisonment[1] if imprisonment else None
    max_months = imprisonment[2] if imprisonment else None
    formatted = imprisonment[3] if imprisonment and len(imprisonment) > 3 else ""

    store.create_calculation(
        case_id=data.get("case_id"),
        article_code=article_code or "",
        article_name=article_name or "",
        min_months=min_months,
        max_months=max_months,
        formatted_result=formatted or "",
        created_by=x_user_id,
        payload=data,
        result={"aNakaz": aNakaz, "structured": structured},
    )

    return CalculateResponse(
        lang=lang,
        aNakaz=aNakaz,
        structured=structured,
    )


@router.get(
    "/api/article/",
    response_model=ArticleInfoResponse,
    tags=[TAG_CALC],
    summary="Article info",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def article_info(q: str = Query(default="")) -> ArticleInfoResponse | JSONResponse:
    query = q.strip()
    if not query:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Параметр q не указан"},
        )

    parsed = parse_article(query)
    if not parsed or not parsed.code:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": f'Статья "{query}" не найдена'},
        )

    ref = get_reference_service()
    article, effective_from, effective_to = ref.get_with_range(parsed.code, date.max)
    if not article:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": f'Статья "{query}" не найдена'},
        )

    name = article.stat.strip() if article.stat else ArticleParser.to_display_name(
        parsed.article,
        parsed.part,
        parsed.paragraph,
    )

    return ArticleInfoResponse(
        article={
            "code": article.article_code,
            "name": name,
            "severity": _parse_severity(article.hard),
            "imprisonment_min": _parse_float(article.fs1r64_01n),
            "imprisonment_max": _parse_float(article.fs1r64_01x),
            "is_excluded": _is_excluded(article.stat),
            "effective_from": effective_from,
            "effective_to": effective_to,
        }
    )


# =============================================================================
# Case / external data (mock)
# =============================================================================


@router.get(
    "/api/case/{erdr}/",
    response_model=CaseResponse,
    tags=[TAG_MATERIALS],
    summary="Case search by ERDR (mock)",
    responses={400: {"model": ErrorResponse}},
)
def case_search(erdr: str) -> CaseResponse | JSONResponse:
    if not _validate_erdr(erdr):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Неверный формат номера ЕРДР"},
        )
    return CaseResponse(**get_full_case_response(erdr))


@router.get(
    "/api/case/{case_id}/verdicts/similar/",
    response_model=SimilarVerdictsResponse,
    tags=[TAG_SIMILAR],
    summary="Similar verdicts (mock)",
)
def similar_verdicts(
    case_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    min_similarity: int = Query(default=70, ge=0, le=100),
) -> SimilarVerdictsResponse:
    verdicts = [v for v in MOCK_SIMILAR_VERDICTS if v.get("similarity", 0) >= min_similarity]
    verdicts = verdicts[:limit]
    return SimilarVerdictsResponse(
        case_id=case_id,
        count=len(verdicts),
        verdicts=verdicts,
    )


@router.post(
    "/api/case/{case_id}/verdicts/similar/",
    response_model=SimilarVerdictFilesResponse,
    tags=[TAG_SIMILAR],
    summary="Similar verdicts (vector search mock)",
    responses={400: {"model": ErrorResponse}},
)
def similar_verdicts_vector(
    case_id: str,
    payload: dict = Body(default_factory=dict),
) -> SimilarVerdictFilesResponse | JSONResponse:
    try:
        req = SimilarVerdictsSearchRequest(**payload)
    except Exception as exc:
        return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})

    if not _validate_erdr(req.erdr_number):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Неверный формат номера ЕРДР"},
        )
    if not req.case_vector:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "case_vector обязателен"},
        )
    if req.min_similarity is not None and not (0 <= req.min_similarity <= 1):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "min_similarity должен быть в диапазоне 0..1"},
        )
    if req.limit is not None and not (1 <= req.limit <= 50):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "limit должен быть в диапазоне 1..50"},
        )
    if req.limit_guilty is not None and req.limit_guilty < 0:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "limit_guilty должен быть >= 0"},
        )
    if req.limit_acquittal is not None and req.limit_acquittal < 0:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "limit_acquittal должен быть >= 0"},
        )

    min_similarity = req.min_similarity or 0.0
    limit = req.limit or 10
    verdicts = [v for v in MOCK_SIMILAR_VERDICT_FILES if v.get("similarity", 0) >= min_similarity]

    if req.decision:
        verdicts = [v for v in verdicts if v.get("decision") == req.decision]
    elif req.limit_guilty is not None or req.limit_acquittal is not None:
        guilty_limit = req.limit_guilty if req.limit_guilty is not None else 0
        acquittal_limit = req.limit_acquittal if req.limit_acquittal is not None else 0
        guilty = [v for v in verdicts if v.get("decision") == "guilty"]
        acquittal = [v for v in verdicts if v.get("decision") == "acquittal"]
        verdicts = guilty[:guilty_limit] + acquittal[:acquittal_limit]

    verdicts = verdicts[:limit]
    return SimilarVerdictFilesResponse(
        case_id=case_id,
        count=len(verdicts),
        verdicts=verdicts,
    )


@router.get(
    "/api/case/{case_id}/acquittals/",
    response_model=AcquittalsResponse,
    tags=[TAG_SIMILAR],
    summary="Acquittals/returns (mock)",
)
def acquittals(
    case_id: str,
    type: str = Query(default="all", pattern="^(acquittal|return|all)$"),
) -> AcquittalsResponse:
    items = MOCK_ACQUITTALS
    if type != "all":
        items = [a for a in items if a.get("type") == type]
    return AcquittalsResponse(
        case_id=case_id,
        count=len(items),
        acquittals=items,
    )


@router.get(
    "/api/case/{case_id}/norms/",
    response_model=NormsResponse,
    tags=[TAG_NORMS],
    summary="Normative decrees (mock)",
)
def norms(
    case_id: str,
    relevance: str = Query(default="all", pattern="^(high|medium|all)$"),
) -> NormsResponse:
    items = MOCK_NORMS
    if relevance != "all":
        items = [n for n in items if n.get("relevance") == relevance]
    return NormsResponse(
        case_id=case_id,
        count=len(items),
        norms=items,
    )


@router.post(
    "/api/case/{erdr}/norms/",
    response_model=NormsResponse,
    tags=[TAG_NORMS],
    summary="Norms by report (mock)",
    responses={400: {"model": ErrorResponse}},
)
def norms_by_report(erdr: str, payload: dict = Body(default_factory=dict)) -> NormsResponse | JSONResponse:
    if not _validate_erdr(erdr):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Неверный формат номера ЕРДР"},
        )
    try:
        req = NormsSearchRequest(**payload)
    except Exception as exc:
        return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})
    if not req.report_text:
        return JSONResponse(status_code=400, content={"success": False, "error": "report_text обязателен"})

    return NormsResponse(
        case_id=erdr,
        count=len(MOCK_NORMS),
        norms=MOCK_NORMS,
    )


@router.get(
    "/api/verdicts/{verdict_id}/",
    response_model=VerdictContentResponse,
    tags=[TAG_VERDICT_GET],
    summary="Verdict content (mock)",
)
def verdict_content(verdict_id: str) -> VerdictContentResponse:
    data = {**MOCK_VERDICT_CONTENT, "id": verdict_id}
    return VerdictContentResponse(verdict=data)


@router.get(
    "/api/case/{erdr}/verdict/",
    response_model=VerdictContentResponse,
    tags=[TAG_VERDICT_GET],
    summary="Latest verdict by ERDR (mock)",
    responses={400: {"model": ErrorResponse}},
)
def latest_verdict(erdr: str) -> VerdictContentResponse | JSONResponse:
    if not _validate_erdr(erdr):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Неверный формат номера ЕРДР"},
        )
    verdict = MOCK_VERDICT_LIST[0] if MOCK_VERDICT_LIST else MOCK_VERDICT_CONTENT
    return VerdictContentResponse(verdict=verdict)


@router.get(
    "/api/case/{erdr}/verdicts/",
    response_model=VerdictListResponse,
    tags=[TAG_VERDICT_GET],
    summary="Verdicts by ERDR (mock)",
    responses={400: {"model": ErrorResponse}},
)
def verdicts_by_case(erdr: str) -> VerdictListResponse | JSONResponse:
    if not _validate_erdr(erdr):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Неверный формат номера ЕРДР"},
        )
    verdicts = list(MOCK_VERDICT_LIST)
    return VerdictListResponse(
        erdr_number=erdr,
        count=len(verdicts),
        verdicts=verdicts,
    )


@router.post(
    "/api/case/{case_id}/appeal-grounds/",
    response_model=AppealGroundsResponse,
    tags=[TAG_VERDICT_ANALYSIS],
    summary="Appeal grounds (mock)",
)
def appeal_grounds(case_id: str) -> AppealGroundsResponse:
    verdict = get_verdict_response(case_id)
    return AppealGroundsResponse(
        case_id=case_id,
        appeal_grounds=verdict["verdict"]["appeal_grounds"],
        recommendation=verdict["verdict"]["recommendation"],
    )


# =============================================================================
# AI Analysis Endpoints
# =============================================================================


@router.get(
    "/api/case/{erdr}/report/latest/",
    response_model=ReportLatestResponse,
    tags=[TAG_MATERIALS],
    summary="Latest case report (materials analysis)",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def latest_report(erdr: str) -> ReportLatestResponse | JSONResponse:
    if not _validate_erdr(erdr):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Неверный формат номера ЕРДР"},
        )
    store = get_analysis_store()
    records = store.list_analyses(erdr, analysis_type="materials", status="completed", limit=1)
    if not records:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Справка не найдена"},
        )
    record = records[0]
    return ReportLatestResponse(
        erdr_number=erdr,
        analysis_id=record.id,
        created_at=record.created_at,
        result=record.result or {},
    )


@router.post(
    "/api/case/{case_id}/analyze-materials/upload/",
    response_model=AnalyzeMaterialsResponse,
    tags=[TAG_MATERIALS],
    summary="Analyze materials (upload text files)",
    responses={400: {"model": ErrorResponse}},
)
def analyze_materials_upload(
    case_id: str,
    files: list[UploadFile] = File(...),
    mode: str = Query(default="async"),
    background_tasks: BackgroundTasks = None,
) -> AnalyzeMaterialsResponse | JSONResponse:
    if background_tasks is None:
        background_tasks = BackgroundTasks()
    if not _validate_erdr(case_id):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Неверный формат номера ЕРДР"},
        )
    if not files:
        return JSONResponse(status_code=400, content={"success": False, "error": "Документы не переданы"})
    if len(files) > 100:
        return JSONResponse(status_code=400, content={"success": False, "error": "Слишком много документов"})

    documents = []
    for file in files:
        try:
            text = _ensure_text_file(file)
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})
        documents.append({"name": file.filename or "document.txt", "text": text})

    mode = (mode or "async").lower()
    if mode not in ("async", "sync", "both"):
        return JSONResponse(status_code=400, content={"success": False, "error": "Недопустимый режим mode"})

    data = {"erdr_number": case_id, "documents": documents, "mode": mode}
    analysis = start_analysis(case_id, "materials", input_params=data)

    if mode in ("sync", "both"):
        run_analysis(analysis.id)

    if mode == "async":
        background_tasks.add_task(run_analysis, analysis.id)
        return AnalyzeMaterialsResponse(
            erdr_number=case_id,
            analysis_id=analysis.id,
            task_id=analysis.task_id or "",
            status=analysis.status,
            poll_url=f"/api/analysis/{analysis.id}/status/",
        )

    updated = get_analysis_store().get_analysis(analysis.id)
    result = updated.result if updated else {}
    return AnalyzeMaterialsResponse(
        erdr_number=case_id,
        analysis_id=analysis.id,
        task_id=analysis.task_id or "",
        status="completed",
        poll_url=f"/api/analysis/{analysis.id}/status/",
        result=result,
    )
@router.post(
    "/api/case/{case_id}/analyze-materials/",
    response_model=AnalyzeMaterialsResponse,
    tags=[TAG_MATERIALS],
    summary="Analyze materials (async)",
    responses={400: {"model": ErrorResponse}},
)
def analyze_materials(
    case_id: str,
    payload: AnalyzeMaterialsRequest = Body(default_factory=AnalyzeMaterialsRequest),
    background_tasks: BackgroundTasks = None,
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
) -> AnalyzeMaterialsResponse | JSONResponse:
    _ = x_user_id
    if background_tasks is None:
        background_tasks = BackgroundTasks()
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    erdr_number = (data.get("erdr_number") or case_id or "").strip()
    if data.get("erdr_number") and erdr_number != case_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "ERDR в пути и в теле не совпадают"},
        )
    if not _validate_erdr(erdr_number):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Неверный формат номера ЕРДР"},
        )

    documents = data.get("documents") or []
    if not documents:
        return JSONResponse(status_code=400, content={"success": False, "error": "Документы не переданы"})
    if len(documents) > 100:
        return JSONResponse(status_code=400, content={"success": False, "error": "Слишком много документов"})
    for doc in documents:
        if not doc.get("text"):
            return JSONResponse(status_code=400, content={"success": False, "error": "Документ без текста"})

    mode = (data.get("mode") or "async").lower()
    if mode not in ("async", "sync", "both"):
        return JSONResponse(status_code=400, content={"success": False, "error": "Недопустимый режим mode"})

    data["erdr_number"] = erdr_number
    analysis = start_analysis(erdr_number, "materials", input_params=data)

    if mode in ("sync", "both"):
        run_analysis(analysis.id)

    if mode == "async":
        background_tasks.add_task(run_analysis, analysis.id)
        return AnalyzeMaterialsResponse(
            erdr_number=erdr_number,
            analysis_id=analysis.id,
            task_id=analysis.task_id or "",
            status=analysis.status,
            poll_url=f"/api/analysis/{analysis.id}/status/",
        )

    updated = get_analysis_store().get_analysis(analysis.id)
    result = updated.result if updated else {}
    return AnalyzeMaterialsResponse(
        erdr_number=erdr_number,
        analysis_id=analysis.id,
        task_id=analysis.task_id or "",
        status="completed",
        poll_url=f"/api/analysis/{analysis.id}/status/",
        result=result,
    )


@router.post(
    "/api/case/{case_id}/risks/analyze/",
    response_model=AnalyzeRisksResponse,
    tags=[TAG_RISKS],
    summary="Analyze risks (async)",
    responses={400: {"model": ErrorResponse}},
)
def analyze_risks(
    case_id: str,
    payload: AnalyzeRisksRequest = Body(default_factory=AnalyzeRisksRequest),
    background_tasks: BackgroundTasks = None,
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
) -> AnalyzeRisksResponse | JSONResponse:
    _ = x_user_id
    if background_tasks is None:
        background_tasks = BackgroundTasks()
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    erdr_number = (data.get("erdr_number") or case_id or "").strip()
    if data.get("erdr_number") and erdr_number != case_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "ERDR в пути и в теле не совпадают"},
        )
    if not _validate_erdr(erdr_number):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Неверный формат номера ЕРДР"},
        )

    if not data.get("report_text"):
        return JSONResponse(status_code=400, content={"success": False, "error": "report_text обязателен"})
    if not data.get("similar_verdicts_summary"):
        return JSONResponse(status_code=400, content={"success": False, "error": "similar_verdicts_summary обязателен"})
    if not data.get("norms_summary"):
        return JSONResponse(status_code=400, content={"success": False, "error": "norms_summary обязателен"})

    mode = (data.get("mode") or "async").lower()
    if mode not in ("async", "sync", "both"):
        return JSONResponse(status_code=400, content={"success": False, "error": "Недопустимый режим mode"})

    data["erdr_number"] = erdr_number
    analysis = start_analysis(erdr_number, "risk_analysis", input_params=data)

    if mode in ("sync", "both"):
        run_analysis(analysis.id)

    if mode == "async":
        background_tasks.add_task(run_analysis, analysis.id)
        return AnalyzeRisksResponse(
            erdr_number=erdr_number,
            analysis_id=analysis.id,
            task_id=analysis.task_id or "",
            status=analysis.status,
            poll_url=f"/api/analysis/{analysis.id}/status/",
        )

    updated = get_analysis_store().get_analysis(analysis.id)
    result = build_risk_analysis_response(updated) if updated else {}
    return AnalyzeRisksResponse(
        erdr_number=erdr_number,
        analysis_id=analysis.id,
        task_id=analysis.task_id or "",
        status="completed",
        poll_url=f"/api/analysis/{analysis.id}/status/",
        result=result,
    )


@router.post(
    "/api/case/{case_id}/verdicts/analyze/",
    response_model=SimilarVerdictsAnalyzeResponse,
    tags=[TAG_SIMILAR_ANALYSIS],
    summary="Analyze similar verdicts (async or sync)",
)
def analyze_verdicts(
    case_id: str,
    payload: dict = Body(default_factory=dict),
    background_tasks: BackgroundTasks = None,
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
) -> SimilarVerdictsAnalyzeResponse | JSONResponse:
    _ = x_user_id
    if background_tasks is None:
        background_tasks = BackgroundTasks()
    try:
        req = AnalyzeSimilarVerdictsRequest(**payload)
    except Exception as exc:
        return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})

    data = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    mode = (data.get("mode") or "async").lower()
    if mode not in ("async", "sync"):
        return JSONResponse(status_code=400, content={"success": False, "error": "mode должен быть async или sync"})

    analysis = start_analysis(case_id, "similar_verdicts", input_params=data)

    if mode == "sync":
        run_analysis(analysis.id)
        updated = get_analysis_store().get_analysis(analysis.id)
        return SimilarVerdictsAnalyzeResponse(
            analysis_id=analysis.id,
            case_id=case_id,
            analysis_type="similar_verdicts",
            status="completed",
            task_id=analysis.task_id or "",
            processing_time_ms=updated.processing_time_ms if updated else None,
            ai_model=updated.ai_model if updated else None,
            created_at=updated.created_at if updated else analysis.created_at,
            result=updated.result if updated else None,
        )

    background_tasks.add_task(run_analysis, analysis.id)
    return SimilarVerdictsAnalyzeResponse(
        analysis_id=analysis.id,
        case_id=case_id,
        analysis_type="similar_verdicts",
        status=analysis.status,
        task_id=analysis.task_id or "",
        poll_url=f"/api/analysis/{analysis.id}/status/",
        created_at=analysis.created_at,
    )


@router.post(
    "/api/case/{case_id}/verdict/analyze/",
    response_model=VerdictAnalyzeResponse,
    tags=[TAG_VERDICT_ANALYSIS],
    summary="Analyze verdict (async or sync)",
)
def analyze_verdict(
    case_id: str,
    payload: dict = Body(default_factory=dict),
    background_tasks: BackgroundTasks = None,
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
) -> VerdictAnalyzeResponse | JSONResponse:
    _ = x_user_id
    if background_tasks is None:
        background_tasks = BackgroundTasks()
    try:
        req = AnalyzeVerdictRequest(**payload)
    except Exception as exc:
        return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})

    data = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    original_request = data.get("original_request") or {}
    erdr_number = original_request.get("erdr_number")
    if erdr_number and erdr_number != case_id:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "ERDR в пути и в теле не совпадают"},
        )

    mode = (data.get("mode") or "async").lower()
    if mode not in ("async", "sync"):
        return JSONResponse(status_code=400, content={"success": False, "error": "mode должен быть async или sync"})

    analysis = start_analysis(case_id, "verdict_analysis", input_params=data)

    if mode == "sync":
        run_analysis(analysis.id)
        updated = get_analysis_store().get_analysis(analysis.id)
        return VerdictAnalyzeResponse(
            analysis_id=analysis.id,
            case_id=case_id,
            analysis_type="verdict_analysis",
            status="completed",
            task_id=analysis.task_id or "",
            processing_time_ms=updated.processing_time_ms if updated else None,
            ai_model=updated.ai_model if updated else None,
            created_at=updated.created_at if updated else analysis.created_at,
            result=updated.result if updated else None,
        )

    background_tasks.add_task(run_analysis, analysis.id)
    return VerdictAnalyzeResponse(
        analysis_id=analysis.id,
        case_id=case_id,
        analysis_type="verdict_analysis",
        status=analysis.status,
        task_id=analysis.task_id or "",
        poll_url=f"/api/analysis/{analysis.id}/status/",
        created_at=analysis.created_at,
    )


@router.get(
    "/api/analysis/{analysis_id}/status/",
    response_model=AnalysisStatusResponse,
    tags=[TAG_SERVICE],
    summary="Analysis status",
    responses={404: {"model": ErrorResponse}},
)
def analysis_status(analysis_id: str) -> AnalysisStatusResponse | JSONResponse:
    store = get_analysis_store()
    analysis = store.get_analysis(analysis_id)
    if not analysis:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Анализ не найден"},
        )

    if analysis.analysis_type == "risk_analysis" and analysis.status == "completed":
        risk_data = build_risk_analysis_response(analysis)
        return AnalysisStatusResponse(
            analysis_id=analysis.id,
            case_id=analysis.case_id,
            analysis_type=analysis.analysis_type,
            status="completed",
            processing_time_ms=analysis.processing_time_ms,
            ai_model=analysis.ai_model,
            created_at=analysis.created_at,
            result=risk_data,
        )

    response = AnalysisStatusResponse(
        analysis_id=analysis.id,
        case_id=analysis.case_id,
        analysis_type=analysis.analysis_type,
        status=analysis.status,
        processing_time_ms=analysis.processing_time_ms,
        ai_model=analysis.ai_model,
        created_at=analysis.created_at,
    )

    if analysis.status == "completed":
        response.result = analysis.result
    elif analysis.status == "failed":
        response.error_message = analysis.error_message

    return response


@router.get(
    "/api/case/{case_id}/analyses/",
    response_model=CaseAnalysesResponse,
    tags=[TAG_SERVICE],
    summary="List analyses by case",
)
def case_analyses(
    case_id: str,
    type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
) -> CaseAnalysesResponse:
    store = get_analysis_store()
    analyses = store.list_analyses(case_id, analysis_type=type, status=status, limit=50)

    items = []
    for item in analyses:
        entry = {
            "id": item.id,
            "analysis_type": item.analysis_type,
            "analysis_type_display": ANALYSIS_TYPE_DISPLAY.get(item.analysis_type, item.analysis_type),
            "status": item.status,
            "ai_model": item.ai_model,
            "processing_time_ms": item.processing_time_ms,
            "created_at": item.created_at,
        }
        if item.status == "completed":
            entry["has_result"] = bool(item.result)
        if item.status == "failed":
            entry["error_message"] = item.error_message
        items.append(entry)

    return CaseAnalysesResponse(
        case_id=case_id,
        count=len(items),
        analyses=items,
    )


@router.get(
    "/api/case/{case_id}/risks/",
    response_model=RiskAnalysisResponse,
    tags=[TAG_RISKS],
    summary="Latest risk analysis",
)
def case_risks(case_id: str) -> RiskAnalysisResponse | JSONResponse:
    store = get_analysis_store()
    latest = store.latest_completed_risk(case_id)
    if not latest:
        return JSONResponse(
            content={
                "success": True,
                "case_id": case_id,
                "analysis": None,
                "message": "Анализ рисков еще не проводился",
            }
        )

    return RiskAnalysisResponse(**build_risk_analysis_response(latest))


# Legacy aliases


@router.post(
    "/api/case/{case_id}/analyze-risks/",
    response_model=GenericAnalyzeResponse,
    tags=[TAG_RISKS],
    summary="Analyze risks (legacy alias)",
)
def analyze_risks_legacy(
    case_id: str,
    payload: dict = Body(default_factory=dict),
    background_tasks: BackgroundTasks = None,
) -> GenericAnalyzeResponse:
    try:
        req = AnalyzeRisksRequest(**payload)
    except Exception as exc:
        return JSONResponse(status_code=400, content={"success": False, "error": str(exc)})
    return analyze_risks(case_id, req, background_tasks)


@router.post(
    "/api/case/{case_id}/verdict/",
    response_model=GenericAnalyzeResponse,
    tags=[TAG_VERDICT_ANALYSIS],
    summary="Analyze verdict (legacy alias)",
)
def analyze_verdict_legacy(
    case_id: str,
    payload: dict = Body(default_factory=dict),
    background_tasks: BackgroundTasks = None,
) -> GenericAnalyzeResponse:
    return analyze_verdict(case_id, payload, background_tasks)


# =============================================================================
# Speech generation (mock async)
# =============================================================================


@router.post(
    "/api/generate/async/",
    response_model=GenerateSpeechResponse,
    tags=[TAG_SPEECH],
    summary="Generate speech (async or sync)",
)
def generate_async(
    payload: GenerateSpeechRequest,
    background_tasks: BackgroundTasks = None,
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
) -> GenerateSpeechResponse:
    if background_tasks is None:
        background_tasks = BackgroundTasks()
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    mode = str(data.get("mode") or "async").strip().lower()
    if mode not in ("async", "sync"):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "mode должен быть async или sync"},
        )

    case_id = data.get("erdr_number")
    speech_id = start_speech(case_id, data, created_by=x_user_id)

    if mode == "sync":
        run_speech(speech_id, data)
        store = get_speech_store()
        record = store.get_speech(speech_id)
        versions = record.versions if record else []
        content = versions[-1].get("content") if versions else None
        return GenerateSpeechResponse(
            speech_id=speech_id,
            status=record.status if record else "draft",
            version=len(versions),
            content=content,
        )

    background_tasks.add_task(run_speech, speech_id, data)
    return GenerateSpeechResponse(
        speech_id=speech_id,
        task_id=f"task-{speech_id}",
        status="pending",
        poll_url=f"/api/speech/{speech_id}/status/",
    )


@router.get(
    "/api/speech/{speech_id}/status/",
    response_model=SpeechStatusResponse,
    tags=[TAG_SPEECH],
    summary="Speech status",
    responses={404: {"model": ErrorResponse}},
)
def speech_status(speech_id: str) -> SpeechStatusResponse | JSONResponse:
    store = get_speech_store()
    record = store.get_speech(speech_id)
    if not record:
        return JSONResponse(status_code=404, content={"success": False, "error": "Речь не найдена"})

    versions = record.versions or []
    current_version = len(versions)
    content = None
    if record.status in ("draft", "review", "approved") and versions:
        content = versions[-1].get("content")

    return SpeechStatusResponse(
        speech_id=record.id,
        status=record.status,
        version=current_version,
        content=content,
    )


@router.get(
    "/api/speech/{speech_id}/versions/",
    response_model=SpeechVersionsResponse,
    tags=[TAG_SPEECH],
    summary="Speech versions",
    responses={404: {"model": ErrorResponse}},
)
def speech_versions(speech_id: str) -> SpeechVersionsResponse | JSONResponse:
    store = get_speech_store()
    record = store.get_speech(speech_id)
    if not record:
        return JSONResponse(status_code=404, content={"success": False, "error": "Речь не найдена"})

    versions = record.versions or []
    items = []
    for v in versions:
        items.append(
            {
                "id": v.get("id"),
                "version_number": v.get("version_number"),
                "created_at": v.get("created_at"),
                "created_by": v.get("created_by"),
                "ai_model": v.get("ai_model"),
                "generation_time_ms": v.get("generation_time_ms"),
            }
        )

    return SpeechVersionsResponse(
        speech_id=record.id,
        current_version=len(versions),
        versions=items,
    )


@router.get(
    "/api/speech/{speech_id}/versions/{version_number}/",
    response_model=SpeechVersionContentResponse,
    tags=[TAG_SPEECH],
    summary="Speech version content",
    responses={404: {"model": ErrorResponse}},
)
def speech_version_content(speech_id: str, version_number: int) -> SpeechVersionContentResponse | JSONResponse:
    store = get_speech_store()
    record = store.get_speech(speech_id)
    if not record:
        return JSONResponse(status_code=404, content={"success": False, "error": "Речь не найдена"})

    versions = record.versions or []
    version = next((v for v in versions if v.get("version_number") == version_number), None)
    if not version:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": f"Версия {version_number} не найдена"},
        )

    return SpeechVersionContentResponse(
        version={
            "id": version.get("id"),
            "version_number": version.get("version_number"),
            "content": version.get("content"),
            "created_at": version.get("created_at"),
            "created_by": version.get("created_by"),
            "ai_model": version.get("ai_model"),
            "generation_time_ms": version.get("generation_time_ms"),
        }
    )


# =============================================================================
# Workflow
# =============================================================================


@router.post(
    "/api/case/{case_id}/workflow/",
    response_model=WorkflowResponse,
    tags=[TAG_WORKFLOW],
    summary="Workflow: calculation + speech",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def workflow(
    case_id: str,
    payload: Dict[str, Any] = Body(default_factory=dict),
    background_tasks: BackgroundTasks = None,
):
    if background_tasks is None:
        background_tasks = BackgroundTasks()
    # 1. Calculate punishment
    aNakaz, structured = calculate_from_json(payload)

    imprisonment = aNakaz[5] if len(aNakaz) > 5 else [False, 0, 0, ""]
    calc_summary = {
        "min_months": imprisonment[1] if imprisonment else 0,
        "max_months": imprisonment[2] if imprisonment else 0,
        "formatted_range": imprisonment[3] if imprisonment else "",
        "calculation_steps": [],
    }

    store = get_calculation_store()
    calc = store.create_calculation(
        case_id=case_id,
        article_code=str(payload.get("crime", {}).get("article_code", "")),
        article_name=str(payload.get("crime", {}).get("article", "")),
        min_months=calc_summary["min_months"],
        max_months=calc_summary["max_months"],
        formatted_result=calc_summary["formatted_range"],
        payload=payload,
        result={"aNakaz": aNakaz, "structured": structured},
    )

    response = {
        "success": True,
        "calculation_id": calc.id,
        "calculation": calc_summary,
    }

    # 2. Optional speech generation
    if payload.get("auto_generate_speech"):
        speech_params = payload.get("speech_params") or {}
        speech_payload = {
            "case_id": case_id,
            **speech_params,
        }
        speech_id = start_speech(case_id, speech_payload)
        background_tasks.add_task(run_speech, speech_id, speech_payload)
        response.update(
            {
                "speech_id": speech_id,
                "task_id": f"task-{speech_id}",
                "speech_status": "pending",
                "poll_url": f"/api/speech/{speech_id}/status/",
            }
        )

    return response


# =============================================================================
# Calculations history
# =============================================================================


@router.get(
    "/api/calculations/",
    response_model=CalculationHistoryResponse,
    tags=[TAG_CALC],
    summary="Calculation history",
)
def calculation_history(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
) -> CalculationHistoryResponse:
    store = get_calculation_store()
    total, calculations = store.list_calculations(user_id=x_user_id, limit=limit, offset=offset)
    items = [
        {
            "id": c.id,
            "article_code": c.article_code,
            "article_name": c.article_name,
            "formatted_result": c.formatted_result,
            "created_at": c.created_at,
        }
        for c in calculations
    ]
    return CalculationHistoryResponse(
        count=total,
        limit=limit,
        offset=offset,
        calculations=items,
    )


@router.get(
    "/api/calculations/{calculation_id}/",
    response_model=CalculationDetailResponse,
    tags=[TAG_CALC],
    summary="Calculation detail",
    responses={404: {"model": ErrorResponse}},
)
def calculation_detail(calculation_id: str) -> CalculationDetailResponse | JSONResponse:
    store = get_calculation_store()
    calc = store.get_calculation(calculation_id)
    if not calc:
        return JSONResponse(status_code=404, content={"success": False, "error": "Расчёт не найден"})

    return CalculationDetailResponse(
        calculation={
            "id": calc.id,
            "case_id": calc.case_id,
            "article_code": calc.article_code,
            "article_name": calc.article_name,
            "min_months": calc.min_months,
            "max_months": calc.max_months,
            "formatted_result": calc.formatted_result,
            "calculation_log": calc.calculation_log,
            "modifiers_applied": calc.modifiers_applied,
            "warnings": calc.warnings,
            "created_at": calc.created_at,
            "created_by": calc.created_by,
            "raw_response": calc.result,
        }
    )
