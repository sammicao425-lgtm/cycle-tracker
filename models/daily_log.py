from datetime import date
from typing import Optional

import pandas as pd

from db.connection import get_worksheet, WS_DAILY_LOG
from db.schema import DAILY_LOG_HEADERS

# Supplement definitions: (db_column, display_name, tier)
SUPPLEMENTS = [
    ("supp_proomega", "ProOmega 2000", "standard"),
    ("supp_vitamin_d", "Vitamin D 2000IU", "standard"),
    ("supp_vitamin_b", "Vitamin B", "optional"),
    ("supp_magnesium", "Magnesium", "optional"),
    ("supp_tru_niagen", "Tru Niagen", "optional"),
    ("supp_creatine", "Creatine", "optional"),
]

SUPP_COLUMNS = [s[0] for s in SUPPLEMENTS]

# Exercise definitions: (db_column, display_name)
EXERCISES = [
    ("exercise_zone2_run", "Zone 2 Run"),
    ("exercise_pt_weights", "PT Weight Training"),
]

EXERCISE_COLUMNS = [e[0] for e in EXERCISES]


def _get_ws():
    return get_worksheet(WS_DAILY_LOG, DAILY_LOG_HEADERS)


def save_log(log_date: date, data: dict) -> None:
    """Upsert a daily log entry."""
    ws = _get_ws()
    date_str = log_date.isoformat()

    # Build the row in header order
    row = []
    for col in DAILY_LOG_HEADERS:
        if col == "log_date":
            row.append(date_str)
        elif col in data:
            val = data[col]
            if val is None:
                row.append("")
            elif isinstance(val, bool):
                row.append(1 if val else 0)
            else:
                row.append(val)
        else:
            row.append("")

    # Check if date already exists
    try:
        cell = ws.find(date_str, in_column=1)
        # Update existing row
        ws.update(f"A{cell.row}:{chr(64 + len(DAILY_LOG_HEADERS))}{cell.row}", [row])
    except Exception:
        # Append new row
        ws.append_row(row)


def get_log(log_date: date) -> Optional[dict]:
    """Get a single day's log entry."""
    ws = _get_ws()
    date_str = log_date.isoformat()
    try:
        cell = ws.find(date_str, in_column=1)
    except Exception:
        return None

    row_values = ws.row_values(cell.row)
    result = {}
    for i, col in enumerate(DAILY_LOG_HEADERS):
        if i < len(row_values):
            val = row_values[i]
            if col == "log_date":
                result[col] = val
            elif col in ("sleep_hrv", "breath_duration_min", "exercise_duration_min"):
                result[col] = float(val) if val else None
            else:
                result[col] = int(val) if val else 0
        else:
            result[col] = None
    return result


def get_logs_range(start_date: date, end_date: date) -> pd.DataFrame:
    """Get all logs in a date range as a DataFrame."""
    ws = _get_ws()
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=DAILY_LOG_HEADERS)

    df = pd.DataFrame(records)
    df["log_date"] = pd.to_datetime(df["log_date"])

    mask = (df["log_date"] >= pd.Timestamp(start_date)) & (df["log_date"] <= pd.Timestamp(end_date))
    df = df[mask].sort_values("log_date").reset_index(drop=True)

    # Convert numeric columns
    for col in ["sleep_hrv", "breath_duration_min", "exercise_duration_min"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in SUPP_COLUMNS + EXERCISE_COLUMNS + ["breath_practice"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df


def get_all_logs() -> pd.DataFrame:
    """Get all logs as a DataFrame."""
    ws = _get_ws()
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=DAILY_LOG_HEADERS)

    df = pd.DataFrame(records)
    df["log_date"] = pd.to_datetime(df["log_date"])
    df = df.sort_values("log_date").reset_index(drop=True)

    for col in ["sleep_hrv", "breath_duration_min", "exercise_duration_min"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in SUPP_COLUMNS + EXERCISE_COLUMNS + ["breath_practice"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    return df
