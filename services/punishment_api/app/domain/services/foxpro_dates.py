from __future__ import annotations

from datetime import date, timedelta
from calendar import monthrange
from typing import Union


def gomonth(start_date: date, months: Union[int, float]) -> date:
    """
    FoxPro-compatible GOMONTH.

    FoxPro truncates non-integer month values. We emulate that behavior
    by converting to int (toward zero) before adding.
    """
    months_int = int(months)
    total_months = (start_date.year * 12 + (start_date.month - 1)) + months_int
    year = total_months // 12
    month = total_months % 12 + 1
    max_day = monthrange(year, month)[1]
    day = min(start_date.day, max_day)
    return date(year, month, day)


def ddtomy(ld_start: date, ld_stop: Union[date, int], ln_mdy: int) -> float:
    """
    FoxPro DDTOMY emulation.

    ln_mdy:
      1 - returns months+days/100 (ld_stop is date)
      2 - returns full years (ld_stop is date)
      3 - returns months+days/100 (ld_stop is days count)
      4 - returns full months (ld_stop is days count)
      5 - returns remaining days (ld_stop is days count)
    """
    if ln_mdy in (3, 4, 5):
        if not isinstance(ld_stop, int):
            raise TypeError("ln_mdy 3/4/5 expects ld_stop as days count (int)")
        ln_mes = 1
        # Find max full months within ld_stop days
        while (gomonth(ld_start, ln_mes) - ld_start).days <= ld_stop:
            ln_mes += 1
        ln_mes -= 1
        if ln_mdy == 3:
            return ln_mes + (ld_stop - (gomonth(ld_start, ln_mes) - ld_start).days) / 100
        if ln_mdy == 4:
            return float(ln_mes)
        return float(ld_stop - (gomonth(ld_start, ln_mes) - ld_start).days)

    if not isinstance(ld_stop, date):
        raise TypeError("ln_mdy 1/2 expects ld_stop as date")

    ln_mes = (
        12 - ld_start.month
        + ld_stop.month
        + (ld_stop.year - ld_start.year - 1) * 12
    )
    if gomonth(ld_start, ln_mes) > ld_stop:
        ln_mes -= 1

    if ln_mdy == 1:
        ln_day = (ld_stop - gomonth(ld_start, ln_mes)).days
        return ln_mes + ln_day / 100
    if ln_mdy == 2:
        return float(int(ln_mes / 12))

    return 0.0
