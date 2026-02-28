import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.punishment_api.app import app  # noqa: E402


def _client() -> TestClient:
    return TestClient(app)


def test_calculate_invalid_birth_date_format():
    client = _client()
    payload = {
        "lang": "ru",
        "person": {"birth_date": "24102001", "gender": "1", "citizenship": "1"},
        "crime": {"crime_date": "2025-09-12", "article_code": "0990001", "article_parts": "01"},
    }
    r = client.post("/calculate", json=payload)
    assert r.status_code == 422
    assert "Неверный формат даты" in r.text


def test_calculate_invalid_crime_date_format():
    client = _client()
    payload = {
        "lang": "ru",
        "person": {"birth_date": "2001-10-24", "gender": "1", "citizenship": "1"},
        "crime": {"crime_date": "12092025", "article_code": "0990001", "article_parts": "01"},
    }
    r = client.post("/calculate", json=payload)
    assert r.status_code == 422
    assert "Неверный формат даты" in r.text


def test_analyze_materials_invalid_erdr():
    client = _client()
    r = client.post(
        "/api/case/123/analyze-materials/",
        json={"erdr_number": "123", "documents": [{"name": "a.txt", "text": "text"}], "mode": "sync"},
    )
    assert r.status_code == 400
    assert r.json()["error"] == "Неверный формат номера ЕРДР"


def test_analyze_materials_missing_documents():
    client = _client()
    erdr = "012345678901234"
    r = client.post(f"/api/case/{erdr}/analyze-materials/", json={"erdr_number": erdr, "documents": []})
    assert r.status_code == 400
    assert r.json()["error"] == "Документы не переданы"


def test_analyze_materials_document_without_text():
    client = _client()
    erdr = "012345678901234"
    r = client.post(
        f"/api/case/{erdr}/analyze-materials/",
        json={"erdr_number": erdr, "documents": [{"name": "a.txt", "text": ""}], "mode": "sync"},
    )
    assert r.status_code == 400
    assert r.json()["error"] == "Документ без текста"


def test_analyze_materials_upload_non_text():
    client = _client()
    erdr = "012345678901234"
    files = [("files", ("doc.pdf", b"%PDF-1.4 fake", "application/pdf"))]
    r = client.post(f"/api/case/{erdr}/analyze-materials/upload/?mode=sync", files=files)
    assert r.status_code == 400
    assert r.json()["error"] == "Недопустимый формат документа, требуется текст"


def test_vectorize_missing_report_text():
    client = _client()
    r = client.post("/api/vectorize/", json={"report_text": ""})
    assert r.status_code == 400
    assert r.json()["error"] == "report_text обязателен"


def test_similar_verdicts_invalid_min_similarity():
    client = _client()
    payload = {"erdr_number": "012345678901234", "case_vector": [0.1, 0.2], "min_similarity": 1.5}
    r = client.post("/api/case/case-uuid/verdicts/similar/", json=payload)
    assert r.status_code == 400
    assert "min_similarity" in r.json()["error"]


def test_similar_verdicts_invalid_limit():
    client = _client()
    payload = {"erdr_number": "012345678901234", "case_vector": [0.1, 0.2], "limit": 0}
    r = client.post("/api/case/case-uuid/verdicts/similar/", json=payload)
    assert r.status_code == 400
    assert "limit" in r.json()["error"]


def test_similar_verdicts_invalid_erdr():
    client = _client()
    payload = {"erdr_number": "123", "case_vector": [0.1, 0.2]}
    r = client.post("/api/case/case-uuid/verdicts/similar/", json=payload)
    assert r.status_code == 400
    assert r.json()["error"] == "Неверный формат номера ЕРДР"


def test_norms_missing_report_text():
    client = _client()
    erdr = "012345678901234"
    r = client.post(f"/api/case/{erdr}/norms/", json={"report_text": ""})
    assert r.status_code == 400
    assert r.json()["error"] == "report_text обязателен"


def test_latest_verdict_invalid_erdr():
    client = _client()
    r = client.get("/api/case/123/verdict/")
    assert r.status_code == 400
    assert r.json()["error"] == "Неверный формат номера ЕРДР"


def test_verdicts_by_case_invalid_erdr():
    client = _client()
    r = client.get("/api/case/123/verdicts/")
    assert r.status_code == 400
    assert r.json()["error"] == "Неверный формат номера ЕРДР"


def test_analysis_status_not_found():
    client = _client()
    r = client.get("/api/analysis/not-found/status/")
    assert r.status_code == 404
    assert r.json()["error"] == "Анализ не найден"


def test_generate_speech_invalid_mode():
    client = _client()
    payload = {
        "erdr_number": "012345678901234",
        "article_code": "1880003",
        "fio": "Ахметов К.С.",
        "report_text": "Текст",
        "calculation_result": {"lang": "ru", "aNakaz": [], "structured": {}},
        "mode": "bad",
    }
    r = client.post("/api/generate/async/", json=payload)
    assert r.status_code == 400
    assert "mode" in r.json()["error"]


def test_verdict_analyze_invalid_mode():
    client = _client()
    payload = {
        "verdict_text": "text",
        "original_request": {"erdr_number": "012345678901234"},
        "mode": "bad",
    }
    r = client.post("/api/case/012345678901234/verdict/analyze/", json=payload)
    assert r.status_code == 400
    assert "mode" in r.json()["error"]


def test_verdict_analyze_erdr_mismatch():
    client = _client()
    payload = {
        "verdict_text": "text",
        "original_request": {"erdr_number": "012345678901235"},
        "mode": "sync",
    }
    r = client.post("/api/case/012345678901234/verdict/analyze/", json=payload)
    assert r.status_code == 400
    assert "ERDR в пути и в теле не совпадают" in r.json()["error"]


def test_report_latest_not_found():
    client = _client()
    r = client.get("/api/case/012345678901233/report/latest/")
    assert r.status_code == 404
    assert r.json()["error"] == "Справка не найдена"
