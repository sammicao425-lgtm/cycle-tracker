from datetime import date, timedelta
from statistics import median
from typing import Optional

import streamlit as st

from db.connection import get_worksheet, WS_PERIOD_START, WS_CYCLE_CONFIG
from db.schema import PERIOD_START_HEADERS, CYCLE_CONFIG_HEADERS


@st.cache_data(ttl=300)
def _get_config(key: str) -> str:
    ws = get_worksheet(WS_CYCLE_CONFIG, CYCLE_CONFIG_HEADERS)
    records = ws.get_all_records()
    for r in records:
        if r["key"] == key:
            return str(r["value"])
    return None


def set_config(key: str, value: str) -> None:
    ws = get_worksheet(WS_CYCLE_CONFIG, CYCLE_CONFIG_HEADERS)
    try:
        cell = ws.find(key, in_column=1)
        ws.update_cell(cell.row, 2, value)
    except Exception:
        ws.append_row([key, value])


def get_default_cycle_length() -> int:
    return int(_get_config("default_cycle_length") or "41")


def get_default_period_length() -> int:
    return int(_get_config("default_period_length") or "7")


# --- Period start CRUD ---


def _clear_period_cache():
    get_period_starts.clear()


def add_period_start(d: date) -> None:
    ws = get_worksheet(WS_PERIOD_START, PERIOD_START_HEADERS)
    date_str = d.isoformat()
    try:
        ws.find(date_str, in_column=1)
    except Exception:
        ws.append_row([date_str])
    _clear_period_cache()


def delete_period_start(d: date) -> None:
    ws = get_worksheet(WS_PERIOD_START, PERIOD_START_HEADERS)
    date_str = d.isoformat()
    try:
        cell = ws.find(date_str, in_column=1)
        ws.delete_rows(cell.row)
    except Exception:
        pass
    _clear_period_cache()


def is_period_start(d: date) -> bool:
    return d in get_period_starts()


@st.cache_data(ttl=60)
def get_period_starts() -> list[date]:
    ws = get_worksheet(WS_PERIOD_START, PERIOD_START_HEADERS)
    records = ws.get_all_records()
    dates = []
    for r in records:
        try:
            dates.append(date.fromisoformat(str(r["start_date"])))
        except (ValueError, KeyError):
            continue
    dates.sort()
    return dates


# --- Cycle analysis ---


def get_average_cycle_length() -> int:
    starts = get_period_starts()
    if len(starts) < 2:
        return get_default_cycle_length()
    gaps = [(starts[i + 1] - starts[i]).days for i in range(len(starts) - 1)]
    return round(median(gaps))


def get_cycle_day(d: date) -> Optional[int]:
    """Return the cycle day (1-based) for a given date, or None if unknown."""
    starts = get_period_starts()
    if not starts:
        return None

    recent = None
    for s in starts:
        if s <= d:
            recent = s
        else:
            break

    if recent is None:
        return None

    return (d - recent).days + 1


def get_cycle_phase(d: date) -> Optional[str]:
    """Return the cycle phase for a given date."""
    cycle_day = get_cycle_day(d)
    if cycle_day is None:
        return None

    avg_length = get_average_cycle_length()
    period_length = get_default_period_length()
    ovulation_day = avg_length - 14

    if cycle_day <= period_length:
        return "menstrual"
    elif cycle_day < ovulation_day - 1:
        return "follicular"
    elif cycle_day <= ovulation_day + 1:
        return "ovulation"
    else:
        return "luteal"


PHASE_COLORS = {
    "menstrual": "#E57373",
    "follicular": "#81C784",
    "ovulation": "#64B5F6",
    "luteal": "#FFD54F",
}

PHASE_ORDER = ["menstrual", "follicular", "ovulation", "luteal"]


def get_phase_for_dates(start_date: date, end_date: date) -> list[tuple[date, str]]:
    """Return a list of (date, phase) tuples for a date range."""
    result = []
    d = start_date
    while d <= end_date:
        phase = get_cycle_phase(d)
        result.append((d, phase))
        d += timedelta(days=1)
    return result
