"""Daily log CRUD and column definitions."""
from datetime import date
from typing import Optional

import pandas as pd
import streamlit as st

from db.connection import get_worksheet, WS_DAILY_LOG
from db.schema import DAILY_LOG_HEADERS

# Supplement definitions: (db_column, display_name, tier)
SUPPLEMENTS = [
    ("supp_proomega", "ProOmega 2000", "standard"),
    ("supp_vitamin_d", "Vitamin D 2000IU", "standard"),
    ("supp_vitamin_b", "Vitamin B", "optional"),
    ("supp_magnesium", "Magnesium", "optional"),
    ("supp_tru_niagen", "Tru Niagen", "trial"),
    ("supp_mag_threonate", "Magnesium L-Threonate", "trial"),
    ("supp_creatine", "Creatine", "optional"),
    ("supp_whey_protein", "Whey Protein", "optional"),
]

SUPP_COLUMNS = [s[0] for s in SUPPLEMENTS]

# Exercise definitions: (db_column, display_name)
EXERCISES = [
    ("exercise_zone2_run", "Zone 2 Run"),
    ("exercise_pt_weights", "PT Weight Training"),
    ("exercise_home_gym", "Home Gym"),
]

EXERCISE_COLUMNS = [e[0] for e in EXERCISES]

# Dysregulation symptom definitions: (db_column, display_name)
DYSREG_SYMPTOMS = [
    ("symptom_headache", "Headache"),
    ("symptom_tight_face", "Tight Facial Muscles"),
    ("symptom_tight_throat", "Tight Throat"),
    ("symptom_shallow_breath", "Shallow Breathing"),
]

DYSREG_COLUMNS = [s[0] for s in DYSREG_SYMPTOMS]
ENERGY_COLUMNS = ["energy_am", "energy_pm"]


def _get_ws():
    return get_worksheet(WS_DAILY_LOG, DAILY_LOG_HEADERS)


@st.cache_data(ttl=120)
def _fetch_all_records() -> list[dict]:
    """Fetch all rows from the daily_log sheet once and cache."""
    ws = _get_ws()
    return ws.get_all_records()


@st.cache_data(ttl=600)
def _fetch_sheet_headers() -> list[str]:
    """Fetch the actual column order from the sheet header row."""
    ws = _get_ws()
    return ws.row_values(1)


def _invalidate_cache():
    """Clear cached data after a write."""
    _fetch_all_records.clear()
    _fetch_sheet_headers.clear()


def save_log(log_date: date, data: dict) -> None:
    """Upsert a daily log entry.

    Always builds the row using the ACTUAL sheet column order,
    not the hardcoded Python definition — prevents misalignment
    when columns were added/migrated in a different order.
    """
    ws = _get_ws()
    date_str = log_date.isoformat()

    # Use the real header order from the sheet
    sheet_headers = _fetch_sheet_headers()
    full_data = {"log_date": date_str, **data}

    row = []
    for col in sheet_headers:
        val = full_data.get(col, None)
        if val is None:
            row.append("")
        elif isinstance(val, bool):
            row.append(1 if val else 0)
        else:
            row.append(val)

    # Check if date already exists
    try:
        cell = ws.find(date_str, in_column=1)
    except Exception:
        cell = None

    if cell is not None:
        ws.update(f"A{cell.row}:{chr(64 + len(sheet_headers))}{cell.row}", [row])
    else:
        ws.append_row(row)

    _invalidate_cache()


def get_log(log_date: date) -> Optional[dict]:
    """Get a single day's log entry from cached data."""
    records = _fetch_all_records()
    date_str = log_date.isoformat()

    for r in records:
        if str(r.get("log_date", "")) == date_str:
            result = {}
            for col in DAILY_LOG_HEADERS:
                val = r.get(col, "")
                if col == "log_date":
                    result[col] = val
                elif col in ("supp_notes", "discomfort_notes"):
                    result[col] = str(val) if val else ""
                elif col in ("sleep_hrv", "breath_duration_min", "exercise_duration_min"):
                    result[col] = float(val) if val != "" and val is not None else None
                else:
                    try:
                        result[col] = int(val) if val != "" and val is not None else 0
                    except (ValueError, TypeError):
                        result[col] = 0
            return result
    return None


def _convert_df(df: pd.DataFrame) -> pd.DataFrame:
    """Convert column types in a log DataFrame."""
    for col in ["sleep_hrv", "breath_duration_min", "exercise_duration_min"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in SUPP_COLUMNS + EXERCISE_COLUMNS + ["breath_practice", "discomfort"] + DYSREG_COLUMNS + ENERGY_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df


def get_logs_range(start_date: date, end_date: date) -> pd.DataFrame:
    """Get all logs in a date range as a DataFrame from cached data."""
    records = _fetch_all_records()
    if not records:
        return pd.DataFrame(columns=DAILY_LOG_HEADERS)

    df = pd.DataFrame(records)
    df["log_date"] = pd.to_datetime(df["log_date"], errors="coerce")
    df = df.dropna(subset=["log_date"])

    mask = (df["log_date"] >= pd.Timestamp(start_date)) & (df["log_date"] <= pd.Timestamp(end_date))
    df = df[mask].sort_values("log_date").reset_index(drop=True)

    return _convert_df(df)


def get_all_logs() -> pd.DataFrame:
    """Get all logs as a DataFrame from cached data."""
    records = _fetch_all_records()
    if not records:
        return pd.DataFrame(columns=DAILY_LOG_HEADERS)

    df = pd.DataFrame(records)
    df["log_date"] = pd.to_datetime(df["log_date"], errors="coerce")
    df = df.dropna(subset=["log_date"])
    df = df.sort_values("log_date").reset_index(drop=True)

    return _convert_df(df)


