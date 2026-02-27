from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from ...core.i18n import normalize_lang, setlang
from ..engines.foxpro_engine import FoxProInput, calculate_count_srk
from ...infrastructure.loaders.reference_loader import get_reference_service


def _parse_gender(value: Optional[str]) -> str:
    if not value:
        return "1"
    v = str(value).strip().lower()
    if v in ("2", "female", "f", "жен", "женщина"):
        return "2"
    return "1"


def _parse_stage(value: Optional[str]) -> str:
    if not value:
        return "3"
    v = str(value).strip().lower()
    if v in ("1", "preparation", "prep"):
        return "1"
    if v in ("2", "attempt"):
        return "2"
    return "3"


def _build_code(article: str, part: Optional[str], paragraph: Optional[str]) -> str:
    art = str(article).strip()
    if not art:
        return ""
    import re

    m = re.match(r"^(\d+)(?:-(\d+))?$", art)
    if m:
        art_num = m.group(1)
        sub_art = m.group(2) or "0"
    else:
        art_num = art
        sub_art = "0"

    pt = str(part).strip() if part else "01"
    return f"{art_num.zfill(3)}{sub_art.zfill(2)}{pt.zfill(2)}"


def _resolve_article_code(
    article_code: Optional[str],
    article: Optional[str],
    part: Optional[str],
    paragraph: Optional[str],
) -> str:
    if article_code:
        code = str(article_code).strip()
        if code.isdigit():
            if len(code) in (5, 7):
                return code
            return code.zfill(7)
    if article and part:
        return _build_code(article, part, paragraph)
    return ""


def _parse_date(value: Any) -> Optional[date]:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        raw = value.strip()
        if len(raw) == 8 and raw.isdigit():
            day = int(raw[:2])
            month = int(raw[2:4])
            year = int(raw[4:])
            return date(year, month, day)
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None
    return None


def calculate_from_json(payload: Dict[str, Any]) -> Tuple[List[List[Any]], Dict[str, Any]]:
    lang = normalize_lang(payload.get("lang", "ru"))
    person = payload.get("person", {}) or {}
    crime = payload.get("crime", {}) or {}

    crime_date = _parse_date(crime.get("crime_date")) or date.today()
    calc_date = _parse_date(payload.get("calc_date")) or date.today()

    article_code = _resolve_article_code(
        crime.get("article_code"),
        crime.get("article"),
        crime.get("part"),
        crime.get("paragraph"),
    )

    article_parts = (crime.get("article_parts") or "").strip()
    if not article_parts and crime.get("paragraph"):
        article_parts = str(crime.get("paragraph")).zfill(2)

    mitigating = crime.get("mitigating") or crime.get("fs1r571p1")
    if mitigating is None and crime.get("has_mitigating"):
        mitigating = "1"

    aggravating = crime.get("aggravating") or crime.get("fs1r572p1")
    if aggravating is None and crime.get("has_aggravating"):
        aggravating = "1"

    special_condition = crime.get("special_condition") or crime.get("fs1r573p1") or ""

    inp = FoxProInput(
        crime_date=crime_date,
        article_code=article_code,
        article_parts=article_parts,
        crime_stage=_parse_stage(crime.get("crime_stage") or crime.get("fs1r56p1")),
        mitigating=str(mitigating or ""),
        aggravating=str(aggravating or ""),
        special_condition=str(special_condition or ""),
        birth_date=_parse_date(person.get("birth_date")),
        gender=_parse_gender(person.get("gender")),
        citizenship=str(person.get("citizenship") or ""),
        dependents=str(person.get("dependents") or person.get("fs1r21p1") or ""),
        additional_marks=str(person.get("additional_marks") or person.get("fs1r231p1") or ""),
        fs1r041p1=str(crime.get("fs1r041p1") or person.get("fs1r041p1") or ""),
        fs1r042p1=str(crime.get("fs1r042p1") or person.get("fs1r042p1") or ""),
        fs1r23p1=str(crime.get("fs1r23p1") or person.get("fs1r23p1") or ""),
        fs1r26p1=str(crime.get("fs1r26p1") or person.get("fs1r26p1") or ""),
        server_date=calc_date,
    )

    ref = get_reference_service()
    article = ref.get_by_code(inp.article_code, inp.crime_date) if inp.article_code else None
    if not article:
        a_nakaz = [[False, 0, 0, "", 0, 0, 0, 0, 0, 0, 0, 0, 0] for _ in range(15)]
        for idx in range(7):
            a_nakaz[idx][3] = setlang(5265, lang)
        structured = {
            "punishments": {},
            "additional_punishments": {},
            "meta": {
                "reference_found": False,
                "reason": "article_not_found",
            },
        }
        return a_nakaz, structured

    a_nakaz = calculate_count_srk(inp, article, lang=lang)
    structured = _build_structured(a_nakaz)
    structured["meta"] = {
        "reference_found": True,
        "is_misdemeanor": bool(a_nakaz[14][0]),
        "no_criminal_liability": bool(a_nakaz[14][1]),
        "reason": a_nakaz[14][3] if a_nakaz[14][1] else "",
    }
    return a_nakaz, structured


def _build_structured(a_nakaz: List[List[Any]]) -> Dict[str, Any]:
    def item(row: int) -> Dict[str, Any]:
        r = a_nakaz[row]
        data = {
            "is_applicable": bool(r[0]),
            "min_value": r[1],
            "max_value": r[2],
            "formatted_text": r[3],
        }
        if row in (3, 5):
            data.update(
                {
                    "min_years": r[4],
                    "min_months": r[5],
                    "min_days": r[6],
                    "max_years": r[7],
                    "max_months": r[8],
                    "max_days": r[9],
                }
            )
        return data

    def add_item(row: int) -> Dict[str, Any]:
        r = a_nakaz[row]
        data = {
            "is_applicable": bool(r[0]),
            "is_mandatory": bool(r[1]),
            "formatted_text": r[3],
        }
        if row == 10:
            data.update({"min_years": r[4], "max_years": r[5]})
        return data

    punishments = {
        "fine": item(0),
        "corrective_work": item(1),
        "mandatory_work": item(2),
        "restriction_of_freedom": item(3),
        "arrest": item(4),
        "imprisonment": item(5),
    }
    additional = {
        "confiscation": add_item(7),
        "deportation": add_item(8),
        "lifetime_prohibition": add_item(9),
        "prohibition_term": add_item(10),
        "deprivation_of_citizenship": add_item(11),
    }
    return {"punishments": punishments, "additional_punishments": additional}
