import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.punishment_api.app import app  # noqa: E402


def test_pipeline_chain_happy_path():
    client = TestClient(app)

    erdr = "012345678901234"
    case_id = "case-uuid-001"
    fio = "Ахметов К.С."
    article_code = "1880003"

    # 1) TXT -> СПРАВКА (materials analysis)
    materials_payload = {
        "erdr_number": erdr,
        "documents": [
            {"name": "doc1.txt", "text": "Протокол допроса. Текст документа."},
            {"name": "doc2.txt", "text": "Постановление. Текст документа."},
        ],
        "mode": "sync",
    }
    r = client.post(f"/api/case/{erdr}/analyze-materials/", json=materials_payload)
    assert r.status_code == 200
    materials = r.json()
    assert materials["status"] == "completed"
    report_text = materials["result"].get("summary") or "Справка по делу."

    # 2) СПРАВКА -> Vectorize
    r = client.post("/api/vectorize/", json={"report_text": report_text})
    assert r.status_code == 200
    vector_data = r.json()
    case_vector = vector_data["vector"]
    assert isinstance(case_vector, list) and len(case_vector) == 128

    # 3) СПРАВКА -> Похожие приговоры (vector search)
    similar_payload = {
        "erdr_number": erdr,
        "case_vector": case_vector,
        "vector_model": vector_data["vector_model"],
        "limit": 4,
        "min_similarity": 0.7,
        "limit_guilty": 2,
        "limit_acquittal": 2,
    }
    r = client.post(f"/api/case/{case_id}/verdicts/similar/", json=similar_payload)
    assert r.status_code == 200
    similar = r.json()
    assert similar["count"] > 0
    verdict_files = similar["verdicts"]
    assert all(v.get("text") for v in verdict_files)

    # 4) Анализ похожих приговоров
    verdicts_for_analysis = [
        {
            "id": v["id"],
            "text": v["text"],
            "file_name": v.get("file_name"),
            "mime": v.get("mime"),
            "similarity": v.get("similarity"),
        }
        for v in verdict_files
    ]
    r = client.post(
        f"/api/case/{case_id}/verdicts/analyze/",
        json={
            "verdicts": verdicts_for_analysis,
            "case_info": {"erdr_number": erdr, "article_code": article_code, "fio": fio},
            "mode": "sync",
        },
    )
    assert r.status_code == 200
    verdicts_analysis = r.json()
    assert verdicts_analysis["status"] == "completed"
    similar_summary = verdicts_analysis["result"].get("summary") or "Сводка по приговорам."

    # 5) СПРАВКА + приговоры -> НПА
    r = client.post(
        f"/api/case/{erdr}/norms/",
        json={"report_text": report_text, "similar_verdicts_summary": similar_summary},
    )
    assert r.status_code == 200
    norms = r.json()
    assert norms["count"] > 0
    norms_summary = norms["norms"][0].get("summary") or norms["norms"][0]["title"]

    # 6) Анализ рисков
    r = client.post(
        f"/api/case/{erdr}/risks/analyze/",
        json={
            "erdr_number": erdr,
            "report_text": report_text,
            "similar_verdicts_summary": similar_summary,
            "norms_summary": norms_summary,
            "mode": "sync",
        },
    )
    assert r.status_code == 200
    risks = r.json()
    assert risks["status"] == "completed"
    risks_result = risks.get("result") or {}

    # 7) Расчёт наказания
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
    calculation_result = r.json()

    # 8) Генерация речи
    r = client.post(
        "/api/generate/async/",
        json={
            "erdr_number": erdr,
            "article_code": article_code,
            "fio": fio,
            "report_text": report_text,
            "calculation_result": calculation_result,
            "similar_verdicts_summary": similar_summary,
            "norms_summary": norms_summary,
            "mode": "sync",
        },
    )
    assert r.status_code == 200
    speech = r.json()
    assert speech["status"] == "draft"
    speech_text = speech.get("content") or ""
    assert speech_text

    # 9) Получение приговора по ЕРДР
    r = client.get(f"/api/case/{erdr}/verdict/")
    assert r.status_code == 200
    verdict = r.json()["verdict"]
    verdict_text = verdict.get("content") or ""
    assert verdict_text

    # 10) Анализ приговора + проект документа
    r = client.post(
        f"/api/case/{erdr}/verdict/analyze/",
        json={
            "verdict_text": verdict_text,
            "original_request": {"erdr_number": erdr, "article_code": article_code, "fio": fio},
            "speech_text": speech_text,
            "risk_analysis_result": risks_result,
            "draft_type": "auto",
            "mode": "sync",
        },
    )
    assert r.status_code == 200
    verdict_analysis = r.json()
    assert verdict_analysis["status"] == "completed"
    assert verdict_analysis["result"]["draft_document"]["type"] in ("agreement", "appeal")

    # 11) Последняя справка
    r = client.get(f"/api/case/{erdr}/report/latest/")
    assert r.status_code == 200
    report_latest = r.json()
    assert report_latest["erdr_number"] == erdr
