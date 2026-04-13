from db.connection import get_worksheet, get_spreadsheet, WS_DAILY_LOG, WS_PERIOD_START, WS_CYCLE_CONFIG

# Column headers for each worksheet
DAILY_LOG_HEADERS = [
    "log_date",
    "supp_proomega", "supp_vitamin_d", "supp_vitamin_b",
    "supp_magnesium", "supp_tru_niagen", "supp_creatine",
    "sleep_hrv",
    "exercise_zone2_run", "exercise_pt_weights", "exercise_duration_min",
    "breath_practice", "breath_duration_min",
]

PERIOD_START_HEADERS = ["start_date"]

CYCLE_CONFIG_HEADERS = ["key", "value"]

_DEFAULTS = [
    ("default_cycle_length", "41"),
    ("default_period_length", "7"),
]


def init_db():
    """Ensure all worksheets exist with correct headers and defaults."""
    get_worksheet(WS_DAILY_LOG, DAILY_LOG_HEADERS)
    get_worksheet(WS_PERIOD_START, PERIOD_START_HEADERS)

    ws = get_worksheet(WS_CYCLE_CONFIG, CYCLE_CONFIG_HEADERS)
    existing = ws.get_all_records()
    existing_keys = {r["key"] for r in existing}
    for key, value in _DEFAULTS:
        if key not in existing_keys:
            ws.append_row([key, value])
