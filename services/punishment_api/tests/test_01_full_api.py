import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.punishment_api.app import app  # noqa: E402


def _client() -> TestClient:
    return TestClient(app)


def _create_materials_report(client: TestClient, erdr: str) -> dict:
    payload = {
        "erdr_number": erdr,
        "documents": [
            {"name": "doc1.txt", "text": "Қазақша мәтін: ӘәІіҢңӨөҰұҮүҚқҒғ"},
            {"name": "doc2.txt", "text": "Протокол допроса. Текст документа."},
        ],
        "mode": "sync",
    }
    r = client.post(f"/api/case/{erdr}/analyze-materials/", json=payload)
    assert r.status_code == 200
    return r.json()


def test_health_and_reference():
    client = _client()
    r = client.get("/health")
    assert r.status_code == 200
    r = client.get("/api/health/")
    assert r.status_code == 200

    r = client.get("/reference/status")
    assert r.status_code == 200
    data = r.json()
    assert "count" in data

    r = client.post("/reference/reload")
    assert r.status_code == 200


def test_article_and_calculate_and_history():
    client = _client()

    r = client.get("/api/article/?q=ст. 99 ч.1")
    assert r.status_code == 200
    article = r.json()["article"]
    assert article["code"]

    calc_payload = {
        "lang": "ru",
        "person": {"birth_date": "24102001", "gender": "1", "citizenship": "1"},
        "crime": {
            "crime_date": "12092025",
            "article_code": "0990001",
            "article_parts": "01",
            "crime_stage": "3",
            "mitigating": "01",
            "aggravating": "",
            "special_condition": "",
        },
    }
    r = client.post("/calculate", json=calc_payload)
    assert r.status_code == 200
    calc_result = r.json()
    assert "aNakaz" in calc_result

    r = client.get("/api/calculations/?limit=10&offset=0")
    assert r.status_code == 200
    history = r.json()
    assert history["count"] >= 1
    calc_id = history["calculations"][0]["id"]

    r = client.get(f"/api/calculations/{calc_id}/")
    assert r.status_code == 200
    detail = r.json()["calculation"]
    assert detail["id"] == calc_id


def test_case_and_norms_and_verdicts():
    client = _client()
    erdr = "012345678901234"
    case_id = "case-uuid-002"

    r = client.get(f"/api/case/{erdr}/")
    assert r.status_code == 200
    case_data = r.json()
    assert case_data["case"]["erdr_number"] == erdr

    r = client.get(f"/api/case/{case_id}/acquittals/?type=acquittal")
    assert r.status_code == 200

    r = client.get(f"/api/case/{case_id}/norms/?relevance=high")
    assert r.status_code == 200

    r = client.post(
        f"/api/case/{erdr}/norms/",
        json={"report_text": "Справка по делу", "similar_verdicts_summary": "Сводка"},
    )
    assert r.status_code == 200
    norms = r.json()["norms"]
    assert norms and "summary" in norms[0]

    r = client.get("/api/verdicts/aa1e8400-e29b-41d4-a716-446655440000/")
    assert r.status_code == 200

    r = client.get(f"/api/case/{erdr}/verdict/")
    assert r.status_code == 200

    r = client.get(f"/api/case/{erdr}/verdicts/")
    assert r.status_code == 200

    r = client.post(f"/api/case/{case_id}/appeal-grounds/")
    assert r.status_code == 200


def test_vectorize_and_similar_verdicts_flow():
    client = _client()
    erdr = "012345678901234"
    case_id = "case-uuid-003"

    r = client.post("/api/vectorize/", json={"report_text": "Справка по делу"})
    assert r.status_code == 200
    vector = r.json()["vector"]

    r = client.post(
        f"/api/case/{case_id}/verdicts/similar/",
        json={
            "erdr_number": erdr,
            "case_vector": vector,
            "limit": 4,
            "min_similarity": 0.7,
            "limit_guilty": 1,
            "limit_acquittal": 1,
        },
    )
    assert r.status_code == 200
    verdicts = r.json()["verdicts"]
    assert verdicts

    # GET list (mock list without vector)
    r = client.get(f"/api/case/{case_id}/verdicts/similar/?limit=2&min_similarity=80")
    assert r.status_code == 200

    r = client.post(
        f"/api/case/{case_id}/verdicts/analyze/",
        json={"verdicts": verdicts, "case_info": {"erdr_number": erdr}, "mode": "sync"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "completed"


def test_analyses_reports_and_risks():
    client = _client()
    erdr = "012345678901234"
    case_id = erdr

    materials = _create_materials_report(client, erdr)
    report_text = materials["result"].get("summary") or "Справка по делу."

    # Risks
    r = client.post(
        f"/api/case/{erdr}/risks/analyze/",
        json={
            "erdr_number": erdr,
            "report_text": report_text,
            "similar_verdicts_summary": "Сводка",
            "norms_summary": "НПА",
            "mode": "sync",
        },
    )
    assert r.status_code == 200
    risks = r.json()
    assert risks["status"] == "completed"

    # Legacy alias
    r = client.post(
        f"/api/case/{erdr}/analyze-risks/",
        json={
            "erdr_number": erdr,
            "report_text": report_text,
            "similar_verdicts_summary": "Сводка",
            "norms_summary": "НПА",
            "mode": "sync",
        },
    )
    assert r.status_code == 200

    # Latest risks
    r = client.get(f"/api/case/{case_id}/risks/")
    assert r.status_code == 200

    # Analyses list
    r = client.get(f"/api/case/{case_id}/analyses/")
    assert r.status_code == 200
    assert r.json()["count"] >= 1

    # Analysis status
    analysis_id = materials["analysis_id"]
    r = client.get(f"/api/analysis/{analysis_id}/status/")
    assert r.status_code == 200

    # Latest report
    r = client.get(f"/api/case/{erdr}/report/latest/")
    assert r.status_code == 200


def test_speech_and_verdict_analysis():
    client = _client()
    erdr = "012345678901234"
    case_id = erdr
    report_text = "Қазақша мәтін: ӘәІіҢңӨөҰұҮүҚқҒғ"

    # Calculate (for speech input)
    calc_payload = {
        "lang": "ru",
        "person": {"birth_date": "24102001", "gender": "1", "citizenship": "1"},
        "crime": {
            "crime_date": "12092025",
            "article_code": "0990001",
            "article_parts": "01",
            "crime_stage": "3",
            "mitigating": "01",
        },
    }
    calc = client.post("/calculate", json=calc_payload).json()

    # Speech sync
    r = client.post(
        "/api/generate/async/",
        json={
            "erdr_number": erdr,
            "article_code": "1880003",
            "fio": "Ахметов К.С.",
            "report_text": report_text,
            "calculation_result": calc,
            "similar_verdicts_summary": "Сводка",
            "norms_summary": "НПА",
            "mode": "sync",
        },
    )
    assert r.status_code == 200
    speech = r.json()
    assert speech["status"] == "draft"
    assert report_text in speech["content"]
    speech_id = speech["speech_id"]

    # Speech status/versions
    r = client.get(f"/api/speech/{speech_id}/status/")
    assert r.status_code == 200
    r = client.get(f"/api/speech/{speech_id}/versions/")
    assert r.status_code == 200
    version_num = r.json()["current_version"]
    r = client.get(f"/api/speech/{speech_id}/versions/{version_num}/")
    assert r.status_code == 200

    # Verdict analysis
    verdict_text = "Текст приговора."
    r = client.post(
        f"/api/case/{case_id}/verdict/analyze/",
        json={
            "verdict_text": verdict_text,
            "original_request": {"erdr_number": erdr, "article_code": "1880003", "fio": "Ахметов К.С."},
            "speech_text": speech["content"],
            "risk_analysis_result": {"risks": []},
            "draft_type": "auto",
            "mode": "sync",
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "completed"

    # Legacy verdict alias
    r = client.post(
        f"/api/case/{case_id}/verdict/",
        json={"verdict_text": verdict_text, "original_request": {"erdr_number": erdr}},
    )
    assert r.status_code == 200


def test_workflow():
    client = _client()
    case_id = "case-uuid-004"
    payload = {
        "crime": {"article_code": "0990001", "article_parts": "01", "crime_stage": "3"},
        "person": {"birth_date": "24102001", "gender": "1", "citizenship": "1"},
        "auto_generate_speech": True,
        "speech_params": {
            "erdr_number": "012345678901234",
            "article_code": "1880003",
            "fio": "Ахметов К.С.",
            "report_text": "Справка по делу",
            "calculation_result": {"lang": "ru", "aNakaz": [], "structured": {}},
            "mode": "async",
        },
    }
    r = client.post(f"/api/case/{case_id}/workflow/", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
