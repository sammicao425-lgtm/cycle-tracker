from datetime import date, timedelta
from statistics import median
from typing import Optional

import streamlit as st

from db.connection import get_worksheet, WS_PERIOD_START, WS_CYCLE_CONFIG
from db.schema import PERIOD_START_HEADERS, CYCLE_CONFIG_HEADERS


# --- Cached data fetchers (one API call each, cached for 2 min) ---


@st.cache_data(ttl=120)
def _fetch_config_records() -> list[dict]:
    ws = get_worksheet(WS_CYCLE_CONFIG, CYCLE_CONFIG_HEADERS)
    return ws.get_all_records()


@st.cache_data(ttl=120)
def _fetch_period_records() -> list[dict]:
    ws = get_worksheet(WS_PERIOD_START, PERIOD_START_HEADERS)
    return ws.get_all_records()


def _invalidate_period_cache():
    _fetch_period_records.clear()


def _invalidate_config_cache():
    _fetch_config_records.clear()


# --- Config ---


def _get_config(key: str) -> str:
    records = _fetch_config_records()
    for r in records:
        if str(r.get("key", "")) == key:
            return str(r["value"])
    return None


def set_config(key: str, value: str) -> None:
    ws = get_worksheet(WS_CYCLE_CONFIG, CYCLE_CONFIG_HEADERS)
    try:
        cell = ws.find(key, in_column=1)
    except Exception:
        cell = None
    if cell is not None:
        ws.update_cell(cell.row, 2, value)
    else:
        ws.append_row([key, value])
    _invalidate_config_cache()


def get_default_cycle_length() -> int:
    return int(_get_config("default_cycle_length") or "41")


def get_default_period_length() -> int:
    return int(_get_config("default_period_length") or "7")


# --- Period start CRUD ---


def add_period_start(d: date) -> None:
    ws = get_worksheet(WS_PERIOD_START, PERIOD_START_HEADERS)
    date_str = d.isoformat()
    try:
        cell = ws.find(date_str, in_column=1)
    except Exception:
        cell = None
    if cell is None:
        ws.append_row([date_str])
    _invalidate_period_cache()


def delete_period_start(d: date) -> None:
    ws = get_worksheet(WS_PERIOD_START, PERIOD_START_HEADERS)
    date_str = d.isoformat()
    try:
        cell = ws.find(date_str, in_column=1)
    except Exception:
        cell = None
    if cell is not None:
        ws.delete_rows(cell.row)
    _invalidate_period_cache()


def is_period_start(d: date) -> bool:
    return d in get_period_starts()


def get_period_starts() -> list[date]:
    records = _fetch_period_records()
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
    # All data is fetched once from cache, then computed locally
    result = []
    d = start_date
    while d <= end_date:
        phase = get_cycle_phase(d)
        result.append((d, phase))
        d += timedelta(days=1)
    return result
