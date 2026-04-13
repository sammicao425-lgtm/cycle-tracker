import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_NAME = "Cycle Tracker Data"

# Worksheet names
WS_DAILY_LOG = "daily_log"
WS_PERIOD_START = "period_start"
WS_CYCLE_CONFIG = "cycle_config"


@st.cache_resource(ttl=300)
def get_client() -> gspread.Client:
    """Return an authenticated gspread client using Streamlit secrets."""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
    except KeyError:
        st.error("Missing [gcp_service_account] in Streamlit secrets. Check your secrets config.")
        st.stop()

    # Validate required fields are present
    required = ["type", "project_id", "private_key", "client_email", "token_uri"]
    missing = [k for k in required if k not in creds_dict]
    if missing:
        st.error(f"Missing fields in gcp_service_account: {missing}")
        st.stop()

    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def get_spreadsheet() -> gspread.Spreadsheet:
    """Get or create the main spreadsheet."""
    client = get_client()
    try:
        return client.open(SHEET_NAME)
    except gspread.SpreadsheetNotFound:
        try:
            spreadsheet = client.create(SHEET_NAME)
            if "owner_email" in st.secrets:
                spreadsheet.share(st.secrets["owner_email"], perm_type="user", role="writer")
            return spreadsheet
        except gspread.exceptions.APIError as e:
            st.error(f"Google API error: {e.response.text}")
            raise


def get_worksheet(name: str, headers: list[str]) -> gspread.Worksheet:
    """Get or create a worksheet with the given headers."""
    spreadsheet = get_spreadsheet()
    try:
        ws = spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=name, rows=1000, cols=len(headers))
        ws.append_row(headers)
    return ws
