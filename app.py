import streamlit as st
from db.schema import init_db
from models.cycle import get_cycle_day, get_cycle_phase, PHASE_COLORS
from models.moon import get_moon_info
from datetime import date

st.set_page_config(
    page_title="Cycle Tracker",
    layout="wide",
    page_icon="\U0001F319",
)

init_db()

# --- Navigation ---
pages = [
    st.Page("pages/daily_log.py", title="Daily Log", icon="\U0001F4DD", default=True),
    st.Page("pages/timeline.py", title="Timeline", icon="\U0001F4C8"),
    st.Page("pages/history.py", title="History", icon="\U0001F4C5"),
]
nav = st.navigation(pages)

# --- Sidebar: today's status ---
with st.sidebar:
    st.markdown("### Today's Status")
    today = date.today()

    cycle_day = get_cycle_day(today)
    phase = get_cycle_phase(today)
    moon = get_moon_info(today)

    col1, col2 = st.columns(2)
    with col1:
        if cycle_day:
            st.metric("Cycle Day", cycle_day)
        else:
            st.metric("Cycle Day", "—")
    with col2:
        if phase:
            color = PHASE_COLORS.get(phase, "#888")
            st.markdown(
                f'<span style="background:{color};padding:4px 10px;border-radius:8px;'
                f'font-weight:600;color:#333">{phase.title()}</span>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("No cycle data yet")

    st.caption(f"\U0001F311 {moon['phase_name']} ({moon['illumination']:.0%})")
    st.divider()

nav.run()
