from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from ...core.i18n import dmytorus, format_number, setlang
from .foxpro_dates import ddtomy, gomonth
from ...infrastructure.loaders.reference_loader import ArticleRecord


@dataclass
class FoxProInput:
    crime_date: date
    article_code: str
    article_parts: str
    crime_stage: str
    mitigating: str
    aggravating: str
    special_condition: str
    birth_date: Optional[date]
    gender: str
    citizenship: str
    dependents: str
    additional_marks: str
    fs1r041p1: str
    fs1r042p1: str
    fs1r23p1: str
    fs1r26p1: str
    server_date: date


def calculate_count_srk(inp: FoxProInput, slvst: ArticleRecord, lang: str = "ru") -> List[List[Any]]:
    a_nakaz = _default_anakaz()

    # Initialize default "not предусмотрено" text for main punishments
    for idx in range(7):
        a_nakaz[idx][3] = setlang(5265, lang)

    ln_mnoj = ln_del = ln_mnoj_udp = ln_del_udp = ln_mnoj56 = ln_del56 = 1

    ln_fs1r14p1 = 0
    if inp.birth_date:
        ln_fs1r14p1 = int(ddtomy(inp.birth_date, inp.crime_date, 2))

    # Column 12 (index 11) for row 6
    a_nakaz[5][11] = 0

    # Stage coefficients (FS1R56P1)
    if inp.crime_stage == "1":
        ln_mnoj56 = 1
        ln_del56 = 2
        a_nakaz[5][11] = a_nakaz[5][11] + 2
    elif inp.crime_stage == "2":
        ln_mnoj56 = 3
        ln_del56 = 4
        a_nakaz[5][11] = a_nakaz[5][11] + 2

    # Plea agreement / special procedure
    if inp.fs1r041p1 == "1" or inp.fs1r042p1 == "1":
        ln_del_udp = 2
        a_nakaz[5][11] = a_nakaz[5][11] + 1
    else:
        if _has_value(inp.mitigating) and not _has_value(inp.aggravating):
            if slvst.hard in ("1", "2"):
                ln_mnoj, ln_del = 1, 2
            elif slvst.hard == "3":
                ln_mnoj, ln_del = 2, 3
            elif slvst.hard == "4":
                ln_mnoj, ln_del = 3, 4

    # ---------------- Fine (05) ----------------
    if (
        (_has_code(slvst.fs1r64, "05")
         and not (inp.article_code == "1890003" and not _has_code(inp.article_parts, "02"))
         and not (inp.article_code == "1900003" and not _has_code(inp.article_parts, "02"))
         and not (inp.article_code == "3070003" and not _has_code(inp.article_parts, "02")))
        or (_has_code(slvst.fs1r64_nn, "05") and inp.special_condition == "02")
    ):
        ln_fs1r64_05n = 0 if _has_code(inp.special_condition, "01") or _has_code(inp.special_condition, "04") else _evl(_val(slvst.fs1r64_05n), 20 if slvst.prest == "2" else 200)
        ln_fs1r64_05x = _evl(_val(slvst.fs1r64_05x), 200 if slvst.prest == "2" else 10000)

        if inp.fs1r041p1 == "3":
            ln_fs1r64_05n = min(ln_fs1r64_05n, 10 if slvst.prest == "2" else 50)
            ln_fs1r64_05x = min(ln_fs1r64_05x, 20 if slvst.prest == "2" else 200)

        if ln_fs1r14p1 < 18:
            if (_has_code(inp.additional_marks, "90") or _has_code(inp.additional_marks, "91") or _has_code(inp.additional_marks, "92")) and inp.fs1r23p1 != "082" and not _has_code(inp.additional_marks, "85") and not _has_code(inp.additional_marks, "86"):
                ln_fs1r64_05n = min(ln_fs1r64_05n, 5)
                ln_fs1r64_05x = min(ln_fs1r64_05x, 100)
            else:
                a_nakaz[0][3] = setlang(5267, lang)
                ln_fs1r64_05x = 0
                a_nakaz[0][10] = 6176

        ln_fs1r64_05x = _apply_modifiers(ln_fs1r64_05x, ln_del_udp, ln_mnoj_udp, ln_del56, ln_mnoj56, ln_del, ln_mnoj)
        ln_fs1r64_05x = _floor2(ln_fs1r64_05x)

        if ln_fs1r64_05x > 0:
            a_nakaz[0][0] = True
            a_nakaz[0][1] = min(ln_fs1r64_05x, ln_fs1r64_05n)
            a_nakaz[0][2] = ln_fs1r64_05x
            unit = setlang(5321, lang)
            if "xN" in (slvst.fs1r64_05x or ""):
                unit = setlang(5320, lang)
            elif "xK" in (slvst.fs1r64_05x or ""):
                unit = setlang(5436, lang)
            a_nakaz[0][3] = _format_range(a_nakaz[0][1], a_nakaz[0][2], unit)
    else:
        a_nakaz[0][10] = 6379

    # ---------------- Corrective work (06) ----------------
    if _has_code(slvst.fs1r64, "06") or (_has_code(slvst.fs1r64_nn, "06") and inp.special_condition == "02"):
        if inp.fs1r23p1 == "082" or _has_code(inp.additional_marks, "85") or _has_code(inp.additional_marks, "86") or _has_code(inp.additional_marks, "87") or _has_code(inp.additional_marks, "88"):
            a_nakaz[1][3] = setlang(5266, lang)
            a_nakaz[1][10] = 6177
        else:
            ln_fs1r64_06n = 0 if _has_code(inp.special_condition, "01") or _has_code(inp.special_condition, "04") else _evl(_val(slvst.fs1r64_06n), 20 if slvst.prest == "2" else 200)
            ln_fs1r64_06x = _evl(_val(slvst.fs1r64_06x), 200 if slvst.prest == "2" else 10000)

            if ln_fs1r14p1 < 18:
                if _has_code(inp.additional_marks, "90") or _has_code(inp.additional_marks, "91") or _has_code(inp.additional_marks, "92"):
                    ln_fs1r64_06n = min(ln_fs1r64_06n, 5)
                    ln_fs1r64_06x = min(ln_fs1r64_06x, 100)
                else:
                    a_nakaz[1][3] = setlang(5268, lang)
                    ln_fs1r64_06x = 0

            ln_fs1r64_06x = _apply_modifiers(ln_fs1r64_06x, ln_del_udp, ln_mnoj_udp, ln_del56, ln_mnoj56, ln_del, ln_mnoj)
            ln_fs1r64_06x = _floor2(ln_fs1r64_06x)

            if ln_fs1r64_06x > 0:
                a_nakaz[1][0] = True
                a_nakaz[1][1] = min(ln_fs1r64_06x, ln_fs1r64_06n)
                a_nakaz[1][2] = ln_fs1r64_06x
                unit = setlang(5321, lang)
                a_nakaz[1][3] = _format_range(a_nakaz[1][1], a_nakaz[1][2], unit)

    # ---------------- Mandatory work (09) ----------------
    if _has_code(slvst.fs1r64, "09"):
        restricted = (
            _has_code(inp.additional_marks, "83")
            or (inp.gender == "2" and (_has_code(inp.dependents, "02") or ln_fs1r14p1 > 57))
            or _has_code(inp.dependents, "04")
            or ln_fs1r14p1 > 62
            or _has_code(inp.additional_marks, "85")
            or _has_code(inp.additional_marks, "93")
            or (_has_code(inp.fs1r23p1, "024") or _has_code(inp.fs1r23p1, "025") or _has_code(inp.fs1r23p1, "026") or _has_code(inp.fs1r23p1, "027") or _has_code(inp.fs1r23p1, "028") or _has_code(inp.fs1r23p1, "029") or _has_code(inp.fs1r23p1, "030")) and _has_value(inp.fs1r26p1)
        )
        if restricted:
            a_nakaz[2][3] = setlang(5269, lang)
            if _has_code(inp.additional_marks, "83") or (inp.gender == "2" and (_has_code(inp.dependents, "02") or ln_fs1r14p1 > 57)) or _has_code(inp.dependents, "04") or ln_fs1r14p1 > 62:
                a_nakaz[2][10] = 6026
            else:
                a_nakaz[2][10] = 6030
        else:
            ln_fs1r64_09n = 0 if _has_code(inp.special_condition, "01") or _has_code(inp.special_condition, "04") else _evl(_val(slvst.fs1r64_09n), 20 if slvst.prest == "2" else 200)
            ln_fs1r64_09x = _evl(_val(slvst.fs1r64_09x), 200 if slvst.prest == "2" else 1200)

            if ln_fs1r14p1 < 18:
                ln_fs1r64_09n = min(10, ln_fs1r64_09n)
                ln_fs1r64_09x = min(75, ln_fs1r64_09x)

            ln_fs1r64_09x = _apply_modifiers(ln_fs1r64_09x, ln_del_udp, ln_mnoj_udp, ln_del56, ln_mnoj56, ln_del, ln_mnoj)
            ln_fs1r64_09x = int(ln_fs1r64_09x)

            a_nakaz[2][0] = True
            a_nakaz[2][1] = min(ln_fs1r64_09x, ln_fs1r64_09n)
            a_nakaz[2][2] = ln_fs1r64_09x
            a_nakaz[2][3] = _format_range(a_nakaz[2][1], a_nakaz[2][2], setlang(5322, lang))

    # ---------------- Arrest (12) ----------------
    if _has_code(slvst.fs1r64, "12"):
        if ln_fs1r14p1 < 18 or _has_code(inp.additional_marks, "85") or _has_code(inp.additional_marks, "83") or (inp.gender == "2" and (_has_code(inp.dependents, "02") or ln_fs1r14p1 > 57)) or _has_code(inp.dependents, "04") or ln_fs1r14p1 > 62:
            a_nakaz[4][3] = setlang(5270, lang)
            a_nakaz[4][10] = 6031 if ln_fs1r14p1 < 18 or _has_code(inp.additional_marks, "85") else 6027
        else:
            ln_fs1r64_12n = 0 if _has_code(inp.special_condition, "01") or _has_code(inp.special_condition, "04") else _evl(_val(slvst.fs1r64_12n), 10)
            ln_fs1r64_12x = _val(slvst.fs1r64_12x) or 0
            ln_fs1r64_12x = _apply_modifiers(ln_fs1r64_12x, ln_del_udp, ln_mnoj_udp, ln_del56, ln_mnoj56, ln_del, ln_mnoj)
            ln_fs1r64_12x = int(ln_fs1r64_12x)

            a_nakaz[4][0] = True
            a_nakaz[4][1] = min(ln_fs1r64_12x, ln_fs1r64_12n)
            a_nakaz[4][2] = ln_fs1r64_12x
            a_nakaz[4][3] = _format_range(a_nakaz[4][1], a_nakaz[4][2], "сут." + setlang(5323, lang))

    # ---------------- Death penalty (02) ----------------
    if _has_code(slvst.fs1r64, "02"):
        if ln_fs1r14p1 < 18 or inp.gender == "2" or ln_fs1r14p1 > 62:
            a_nakaz[6][3] = setlang(5276, lang)
            a_nakaz[6][10] = 6029
        else:
            if _has_value(inp.mitigating) and not _has_value(inp.aggravating):
                a_nakaz[6][3] = setlang(5278, lang)
                a_nakaz[6][10] = 6172
            elif inp.crime_stage in ("1", "2"):
                a_nakaz[6][3] = setlang(5280, lang)
                a_nakaz[6][10] = 6173
            else:
                a_nakaz[6][3] = setlang(5277, lang)
                a_nakaz[6][0] = True

    # ---------------- Restriction of freedom (11) ----------------
    if (
        (_has_code(slvst.fs1r64, "11")
         and not (inp.article_code == "1890003" and _has_code(inp.article_parts, "02"))
         and not (inp.article_code == "1900003" and _has_code(inp.article_parts, "02")))
        or (_has_code(slvst.fs1r64_nn, "11") and inp.special_condition == "02")
    ):
        if _has_code(inp.special_condition, "01") or _has_code(inp.special_condition, "04"):
            ln_fs1r64_11n = 0
        else:
            _v11n = _val(slvst.fs1r64_11n)
            ln_fs1r64_11n = _evl((_v11n * 12) if _v11n is not None else None, 6)
        ln_fs1r64_11x = _evl(_val(slvst.fs1r64_11x), 7) * 12

        if ln_fs1r14p1 < 18:
            ln_fs1r64_11n = 0
            ln_fs1r64_11x = min(ln_fs1r64_11x, 2 * 12)

        ld_date_start = inp.server_date
        months_adj = _apply_modifiers(ln_fs1r64_11x, ln_del_udp, ln_mnoj_udp, ln_del56, ln_mnoj56, ln_del, ln_mnoj)
        ln_fs1r64_11x_days = int((gomonth(ld_date_start, months_adj) - ld_date_start).days)

        ln_mes = int(ddtomy(ld_date_start, ln_fs1r64_11x_days, 4))
        ln_day = int(ddtomy(ld_date_start, ln_fs1r64_11x_days, 5))
        ln_year = 0
        ln_fs1r64_11x = ln_mes + ln_day / 10
        if ln_mes > 11:
            ln_year = int(ln_mes / 12)
            ln_mes = ln_mes - ln_year * 12

        a_nakaz[3][7] = ln_year
        a_nakaz[3][8] = ln_mes
        a_nakaz[3][9] = ln_day

        lc_padeg = "I" if ln_fs1r64_11n >= ln_fs1r64_11x else "D"
        lc_max_srok = _format_term(ln_year, ln_mes, ln_day, lc_padeg)

        ln_mes = int(ln_fs1r64_11n)
        ln_year = 0
        if ln_mes > 11:
            ln_year = int(ln_mes / 12)
            ln_mes = ln_mes - ln_year * 12
        a_nakaz[3][4] = ln_year
        a_nakaz[3][5] = ln_mes
        a_nakaz[3][6] = ln_day

        lc_min_srok = _format_term(ln_year, ln_mes, 0, "D")

        if ln_fs1r64_11n >= ln_fs1r64_11x:
            a_nakaz[3][4] = a_nakaz[3][7]
            a_nakaz[3][5] = a_nakaz[3][8]
            a_nakaz[3][6] = a_nakaz[3][9]
            ln_fs1r64_11n = ln_fs1r64_11x

        a_nakaz[3][0] = True
        a_nakaz[3][1] = ln_fs1r64_11n
        a_nakaz[3][2] = ln_fs1r64_11x
        a_nakaz[3][3] = _format_range_term(lc_min_srok, lc_max_srok, a_nakaz[3][1], a_nakaz[3][2])
    else:
        a_nakaz[3][10] = 6380

    # ---------------- Imprisonment (01) ----------------
    if _has_code(slvst.fs1r64, "01"):
        lc_fs1r64_02x = setlang(5279, lang) if (_has_code(slvst.fs1r64, "03") or (inp.article_code == "4370003" and _has_value(inp.aggravating))) else ""

        if inp.fs1r041p1 == "1" or inp.fs1r042p1 == "1":
            lc_fs1r64_02x = ""
            a_nakaz[5][12] = 6174
        else:
            if _has_value(inp.mitigating) and not _has_value(inp.aggravating):
                lc_fs1r64_02x = ""
                a_nakaz[5][12] = 6175

        if ln_fs1r14p1 < 18 or inp.gender == "2" or ln_fs1r14p1 > 62:
            lc_fs1r64_02x = ""
            a_nakaz[5][12] = 6028
        if inp.crime_stage in ("1", "2"):
            lc_fs1r64_02x = ""
            a_nakaz[5][12] = 6173

        if (
            (_has_code(slvst.fs1r64, "05") or _has_code(slvst.fs1r64, "06") or _has_code(slvst.fs1r64, "11"))
            and _has_code(inp.mitigating, "06")
            and (slvst.hard in ("1", "2") or (_between(inp.article_code[:5], "21400", "24700") and inp.article_code[:5] != "21800"))
        ):
            a_nakaz[5][3] = setlang(5272, lang)
            a_nakaz[5][10] = 6170
            a_nakaz[5][12] = 6170
        else:
            if ln_fs1r14p1 < 18 and slvst.hard not in ("3", "4") and (slvst.fl1u or "") != "ALL" and (not (slvst.fl1u or "") or not _has_code(inp.article_parts, (slvst.fl1u or "").strip())):
                a_nakaz[5][3] = setlang(5271, lang)
                a_nakaz[5][10] = 6171
                a_nakaz[5][12] = 6171
            else:
                ln_fs1r64_01n = (_val(slvst.fs1r64_01n) or 0) * 12
                ln_fs1r64_01x = (_val(slvst.fs1r64_01x) or 0) * 12

                if inp.article_code == "4370003" and _has_value(inp.aggravating):
                    ln_fs1r64_01n = 10 * 12
                    ln_fs1r64_01x = 20 * 12

                ln_fs1r64_01n = 6 if (_has_code(inp.special_condition, "01") or _has_code(inp.special_condition, "04")) else _evl(ln_fs1r64_01n, 6)

                if ln_fs1r14p1 < 18:
                    if (inp.article_code.startswith("09900") and _has_value(inp.aggravating)) or inp.article_code.startswith("25500") or inp.article_code == "0990002":
                        ln_fs1r64_01x = 12 * 12
                    else:
                        ln_fs1r64_01x = 10 * 12
                    ln_fs1r64_01n = min(ln_fs1r64_01n, ln_fs1r64_01x)

                if ln_fs1r64_01x:
                    ld_date_start = inp.server_date
                    months_adj = _apply_modifiers(ln_fs1r64_01x, ln_del_udp, ln_mnoj_udp, ln_del56, ln_mnoj56, ln_del, ln_mnoj)
                    ln_fs1r64_01x_days = int((gomonth(ld_date_start, months_adj) - ld_date_start).days)

                    ln_mes = int(ddtomy(ld_date_start, ln_fs1r64_01x_days, 4))
                    ln_day = int(ddtomy(ld_date_start, ln_fs1r64_01x_days, 5))
                    ln_year = 0
                    ln_fs1r64_01x = ln_mes + ln_day / 10
                    if ln_mes > 11:
                        ln_year = int(ln_mes / 12)
                        ln_mes = ln_mes - ln_year * 12
                    a_nakaz[5][7] = ln_year
                    a_nakaz[5][8] = ln_mes
                    a_nakaz[5][9] = ln_day

                    lc_padeg = "I" if ln_fs1r64_01n >= ln_fs1r64_01x else "D"
                    lc_max_srok = _format_term(ln_year, ln_mes, ln_day, lc_padeg)

                    ln_mes = int(ln_fs1r64_01n)
                    ln_year = 0
                    if ln_mes > 11:
                        ln_year = int(ln_mes / 12)
                        ln_mes = ln_mes - ln_year * 12
                    a_nakaz[5][4] = ln_year
                    a_nakaz[5][5] = ln_mes
                    a_nakaz[5][6] = ln_day

                    lc_min_srok = _format_term(ln_year, ln_mes, 0, "D")

                    if ln_fs1r64_01n >= ln_fs1r64_01x:
                        a_nakaz[5][4] = a_nakaz[5][7]
                        a_nakaz[5][5] = a_nakaz[5][8]
                        a_nakaz[5][6] = a_nakaz[5][9]
                        ln_fs1r64_01n = ln_fs1r64_01x

                    a_nakaz[5][0] = True
                    a_nakaz[5][1] = ln_fs1r64_01n
                    a_nakaz[5][2] = ln_fs1r64_01x
                    a_nakaz[5][3] = ("" if ln_fs1r64_01n >= ln_fs1r64_01x else f"от {lc_min_srok} до ") + lc_max_srok + (" " + lc_fs1r64_02x if lc_fs1r64_02x else "")

    # ---------------- Additional punishments ----------------
    ll_fs1r65o_01 = (
        (inp.article_code == "3620004" and _has_code(inp.article_parts, "03"))
        or (inp.article_code == "4510002" and _has_code(inp.article_parts, "02"))
    )

    if _has_code(slvst.fs1r65_o, "01") or _has_code(slvst.fs1r65_n, "01") or ll_fs1r65o_01:
        if ln_fs1r14p1 < 18:
            a_nakaz[7][3] = setlang(5283, lang)
        else:
            a_nakaz[7][0] = True
            a_nakaz[7][1] = (_has_code(slvst.fs1r65_o, "01") or ll_fs1r65o_01) and inp.special_condition != "03"
            a_nakaz[7][3] = setlang(5281, lang) if (_has_code(slvst.fs1r65_o, "01") or ll_fs1r65o_01) else setlang(5282, lang)

    if _has_code(slvst.fs1r65_o, "04") or _has_code(slvst.fs1r65_n, "04"):
        if ln_fs1r14p1 < 18:
            a_nakaz[8][3] = setlang(5286, lang)
        else:
            a_nakaz[8][0] = True
            a_nakaz[8][1] = _has_code(slvst.fs1r65_o, "04") and inp.special_condition != "03"
            if inp.citizenship not in ("2", "3", "4"):
                a_nakaz[8][3] = setlang(5287, lang) if _has_code(slvst.fs1r65_o, "04") else setlang(5285, lang)
            else:
                a_nakaz[8][3] = setlang(5284, lang) if _has_code(slvst.fs1r65_o, "04") else setlang(5285, lang)

    ll_fs1r65_o = (
        (inp.article_code == "1200003" and _has_code(inp.article_parts, "05"))
        or (inp.article_code == "1210003" and _has_code(inp.article_parts, "05"))
        or (inp.article_code == "1340004" and _has_code(inp.article_parts, "02"))
        or (inp.article_code == "1890003" and _has_code(inp.article_parts, "02"))
        or (inp.article_code == "1900003" and _has_code(inp.article_parts, "02"))
        or (inp.article_code == "2150002" and _has_code(inp.article_parts, "03"))
        or (inp.article_code == "2160002" and _has_code(inp.article_parts, "04"))
        or (inp.article_code == "2170003" and _has_code(inp.article_parts, "03"))
        or (inp.article_code == "2180003" and _has_code(inp.article_parts, "01"))
        or (inp.article_code == "2340003" and _has_code(inp.article_parts, "01"))
        or (inp.article_code == "2490003" and _has_code(inp.article_parts, "02"))
        or (inp.article_code == "3070003" and _has_code(inp.article_parts, "03"))
        or (inp.article_code == "3120003" and (_has_code(inp.article_parts, "01") or _has_code(inp.article_parts, "02")))
        or (inp.article_code == "3620004" and _has_code(inp.article_parts, "03"))
        or (inp.article_code == "4510002" and _has_code(inp.article_parts, "02"))
    )

    if _has_code(slvst.fs1r65_o, "22") or _has_code(slvst.fs1r65_n, "22") or ll_fs1r65_o:
        if ln_fs1r14p1 < 18:
            a_nakaz[9][3] = setlang(5290, lang)
        else:
            a_nakaz[9][0] = True
            a_nakaz[9][1] = _has_code(slvst.fs1r65_o, "22") and inp.special_condition != "03"
            a_nakaz[9][3] = setlang(5288, lang) if (_has_code(slvst.fs1r65_o, "22") or ll_fs1r65_o) else setlang(5289, lang)

    if (_has_code(slvst.fs1r65_o, "02") or _has_code(slvst.fs1r65_n, "02") or inp.special_condition == "05") and not ll_fs1r65_o:
        ln_fs1r65_02n = 1 if inp.special_condition == "05" else _evl(_val(slvst.fs1r65_02n), 1)
        ln_fs1r65_02x = _evl(_val(slvst.fs1r65_02x), 10)
        if ln_fs1r14p1 < 18:
            ln_fs1r65_02x = max(min(ln_fs1r65_02x, 2), 2)
            ln_fs1r65_02n = min(ln_fs1r65_02n, 2)

        a_nakaz[10][0] = True
        a_nakaz[10][1] = _has_code(slvst.fs1r65_o, "02") and inp.special_condition != "03"
        a_nakaz[10][4] = ln_fs1r65_02n
        if (not ln_fs1r65_02x) and ln_fs1r14p1 > 17:
            a_nakaz[10][2] = True
            a_nakaz[10][5] = 999
            a_nakaz[10][3] = setlang(5291, lang) if _has_code(slvst.fs1r65_o, "02") else setlang(5292, lang)
            a_nakaz[10][3] = (
                a_nakaz[10][3]
                + f" от {int(ln_fs1r65_02n)} "
                + dmytorus(int(ln_fs1r65_02n), 3, "D")
                + " "
                + setlang(5324, lang)
            )
        else:
            a_nakaz[10][5] = ln_fs1r65_02x
            a_nakaz[10][4] = ln_fs1r65_02x if ln_fs1r65_02n >= ln_fs1r65_02x else ln_fs1r65_02n
            lc_padeg = "I" if ln_fs1r65_02n >= ln_fs1r65_02x else "D"
            prefix = setlang(5291, lang) if _has_code(slvst.fs1r65_o, "02") else setlang(5292, lang)
            if ln_fs1r65_02n >= ln_fs1r65_02x:
                a_nakaz[10][3] = prefix + " на " + str(int(ln_fs1r65_02x)) + " " + dmytorus(int(ln_fs1r65_02x), 3, lc_padeg)
            else:
                a_nakaz[10][3] = (
                    prefix
                    + " от "
                    + str(int(ln_fs1r65_02n))
                    + " "
                    + dmytorus(int(ln_fs1r65_02n), 3, "D")
                    + " до "
                    + str(int(ln_fs1r65_02x))
                    + " "
                    + dmytorus(int(ln_fs1r65_02x), 3, lc_padeg)
                )

    if _has_code(slvst.fs1r65_o, "05") or _has_code(slvst.fs1r65_n, "05"):
        if ln_fs1r14p1 < 18:
            a_nakaz[11][3] = setlang(5421, lang)
        else:
            a_nakaz[11][0] = True
            a_nakaz[11][1] = _has_code(slvst.fs1r65_o, "05") and inp.special_condition != "03"
            if inp.citizenship != "1":
                a_nakaz[11][3] = setlang(5422, lang) if _has_code(slvst.fs1r65_o, "05") else setlang(5424, lang)
            else:
                a_nakaz[11][3] = setlang(5423, lang) if _has_code(slvst.fs1r65_o, "04") else setlang(5424, lang)

    # ---------------- Meta row (15) ----------------
    a_nakaz[14][0] = slvst.prest == "2"

    if inp.article_code[:5] not in ("17000", "17100", "17300", "17700", "17800", "18400", "25500", "25600", "25700", "25800", "25900", "26000", "26100", "26900", "27000"):
        if inp.crime_stage == "1" and slvst.hard not in ("3", "4"):
            a_nakaz[14][1] = True
            a_nakaz[14][3] = setlang(5295, lang)
        if inp.crime_stage == "2" and slvst.hard not in ("2", "3", "4"):
            a_nakaz[14][1] = True
            a_nakaz[14][3] = setlang(5296, lang)

    if ln_fs1r14p1 < 14:
        a_nakaz[14][1] = True
        a_nakaz[14][3] = setlang(5293, lang)
    elif ln_fs1r14p1 < 16 and (
        inp.article_code[:5] not in (
            "09900", "10600", "12000", "12100", "12500", "17300", "17400", "17700", "17800", "18400", "19200", "25500", "25600", "25800", "26100", "26900", "27300", "29100", "29400", "29800", "35000"
        )
        and inp.article_code not in (
            "1070002", "1880002", "1880003", "1880004", "1910002", "1910003", "1910004",
            "1940002", "1940003", "1940004", "2000002", "2000003", "2000004", "2020002",
            "2020003", "2570001", "2570002", "2930002", "2930003", "3140002"
        )
    ):
        a_nakaz[14][1] = True
        a_nakaz[14][3] = setlang(5294, lang)

    return a_nakaz


def _default_anakaz() -> List[List[Any]]:
    return [[False, 0, 0, "", 0, 0, 0, 0, 0, 0, 0, 0, 0] for _ in range(15)]


def _has_value(value: Optional[str]) -> bool:
    if value is None:
        return False
    return bool(str(value).replace(",", "").strip())


def _has_code(haystack: Optional[str], code: str) -> bool:
    if not haystack:
        return False
    return code in str(haystack)


def _val(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    num = ""
    for ch in s:
        if ch.isdigit() or ch in ".-+":
            num += ch
        elif ch == ",":
            num += "."
        else:
            break
    try:
        return float(num) if num not in ("", "+", "-", ".") else None
    except ValueError:
        return None


def _evl(value: Optional[float], default: float) -> float:
    return default if value is None else value


def _apply_modifiers(value: float, ln_del_udp: float, ln_mnoj_udp: float, ln_del56: float, ln_mnoj56: float, ln_del: float, ln_mnoj: float) -> float:
    return value / ln_del_udp * ln_mnoj_udp / ln_del56 * ln_mnoj56 / ln_del * ln_mnoj


def _floor2(value: float) -> float:
    return int(value * 100) / 100


def _format_range(min_val: float, max_val: float, unit: str) -> str:
    if min_val != max_val:
        prefix = f"от {format_number(min_val)} " if min_val > 0 else ""
        return f"{prefix}до {format_number(max_val)} {unit}".strip()
    return f"{format_number(max_val)} {unit}".strip()


def _format_term(years: int, months: int, days: int, padezh: str) -> str:
    parts = []
    if years > 0:
        parts.append(f"{years} {dmytorus(years, 3, padezh)}")
    if months > 0:
        parts.append(f"{months} {dmytorus(months, 2, padezh)}")
    if days > 0:
        parts.append(f"{days} {dmytorus(days, 1, padezh)}")
    return " ".join(parts)


def _format_range_term(lc_min: str, lc_max: str, min_val: float, max_val: float) -> str:
    if min_val != max_val:
        return f"от {lc_min} до {lc_max}".strip()
    return lc_max


def _between(value: str, low: str, high: str) -> bool:
    return low <= value <= high
