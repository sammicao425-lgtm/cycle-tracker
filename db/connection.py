import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_NAME = "Cycle Tracker Data"
SHEET_ID = "1eRw-RtSpohg-ZF3A08SgW9V94X4Bup5cHroYBUR4GEA"

# Worksheet names
WS_DAILY_LOG = "daily_log"
WS_PERIOD_START = "period_start"
WS_CYCLE_CONFIG = "cycle_config"


@st.cache_resource(ttl=600)
def get_client() -> gspread.Client:
    """Return an authenticated gspread client using Streamlit secrets."""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
    except KeyError:
        st.error("Missing [gcp_service_account] in Streamlit secrets. Check your secrets config.")
        st.stop()

    required = ["type", "project_id", "private_key", "client_email", "token_uri"]
    missing = [k for k in required if k not in creds_dict]
    if missing:
        st.error(f"Missing fields in gcp_service_account: {missing}")
        st.stop()

    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_resource(ttl=600)
def _get_spreadsheet():
    """Cached spreadsheet object."""
    client = get_client()
    return client.open_by_key(SHEET_ID)


def get_spreadsheet() -> gspread.Spreadsheet:
    return _get_spreadsheet()


# Cache worksheet objects so we don't re-fetch them on every call
_ws_cache = {}


def get_worksheet(name: str, headers: list[str]) -> gspread.Worksheet:
    """Get or create a worksheet (cached per session)."""
    if name in _ws_cache:
        return _ws_cache[name]

    spreadsheet = get_spreadsheet()
    try:
        ws = spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=name, rows=1000, cols=len(headers))
        ws.append_row(headers)

    _ws_cache[name] = ws
    return ws
