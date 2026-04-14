import streamlit as st
from datetime import date, timedelta

import pandas as pd

from models.daily_log import get_logs_range, SUPPLEMENTS, SUPP_COLUMNS, EXERCISES, EXERCISE_COLUMNS
from models.cycle import get_cycle_phase, PHASE_COLORS
from components.charts import build_timeline_chart

st.header("Timeline")

# --- Date range selector ---
range_options = {
    "Last 30 days": 30,
    "Last 60 days": 60,
    "Last 90 days": 90,
    "Last 6 months": 180,
    "All time": None,
}

col1, col2 = st.columns([1, 3])
with col1:
    selected_range = st.selectbox("Time range", list(range_options.keys()))

days = range_options[selected_range]
end_date = date.today()

if days:
    start_date = end_date - timedelta(days=days)
else:
    start_date = date(2020, 1, 1)

# Fetch data
df = get_logs_range(start_date, end_date)

# --- Build and display chart ---
fig = build_timeline_chart(df, start_date, end_date)
st.plotly_chart(fig, use_container_width=True)

# --- Legend ---
st.caption("**Cycle phases**")
phase_cols = st.columns(4)
for i, (phase, color) in enumerate(PHASE_COLORS.items()):
    with phase_cols[i]:
        st.markdown(
            f'<span style="background:{color};padding:2px 8px;border-radius:4px;'
            f'font-size:0.85em;color:#333">{phase.title()}</span>',
            unsafe_allow_html=True,
        )

exercise_colors = {
    "Zone 2 Run": "#42A5F5",
    "PT Weight Training": "#AB47BC",
    "Home Gym": "#FF7043",
}
st.caption("**Exercise** &nbsp; | &nbsp; **Breath**: green = yes, gray = rest")
ex_cols = st.columns(len(exercise_colors))
for i, (name, color) in enumerate(exercise_colors.items()):
    with ex_cols[i]:
        st.markdown(
            f'<span style="background:{color};padding:2px 8px;border-radius:4px;'
            f'font-size:0.85em;color:#fff">{name}</span>',
            unsafe_allow_html=True,
        )

# --- Summary stats ---
if not df.empty:
    st.divider()
    st.subheader("Summary")

    s1, s2, s3, s4 = st.columns(4)

    with s1:
        hrv_vals = df["sleep_hrv"].dropna()
        if not hrv_vals.empty:
            st.metric("Avg HRV", f"{hrv_vals.mean():.0f} ms")
        else:
            st.metric("Avg HRV", "—")

    with s2:
        breath_pct = df["breath_practice"].mean() * 100 if len(df) > 0 else 0
        st.metric("Breath Practice", f"{breath_pct:.0f}%")

    with s3:
        avail = [c for c in SUPP_COLUMNS if c in df.columns]
        if avail:
            supp_pct = df[avail].mean().mean() * 100
            st.metric("Supplement Adherence", f"{supp_pct:.0f}%")
        else:
            st.metric("Supplement Adherence", "—")

    with s4:
        st.metric("Days Logged", len(df))

    # --- Per-phase breakdown ---
    st.divider()
    st.subheader("By Cycle Phase")

    df_copy = df.copy()
    df_copy["phase"] = df_copy["log_date"].apply(
        lambda d: get_cycle_phase(d.date() if hasattr(d, "date") else d)
    )
    df_with_phase = df_copy.dropna(subset=["phase"])

    if not df_with_phase.empty:
        phase_stats = []
        for phase in ["menstrual", "follicular", "ovulation", "luteal"]:
            phase_df = df_with_phase[df_with_phase["phase"] == phase]
            if phase_df.empty:
                continue
            hrv_mean = phase_df["sleep_hrv"].dropna().mean()
            breath_rate = phase_df["breath_practice"].mean() * 100
            avail = [c for c in SUPP_COLUMNS if c in phase_df.columns]
            supp_rate = phase_df[avail].mean().mean() * 100 if avail else 0
            phase_stats.append({
                "Phase": phase.title(),
                "Days": len(phase_df),
                "Avg HRV (ms)": f"{hrv_mean:.0f}" if pd.notna(hrv_mean) else "—",
                "Breath %": f"{breath_rate:.0f}%",
                "Suppl %": f"{supp_rate:.0f}%",
            })

        if phase_stats:
            st.dataframe(
                pd.DataFrame(phase_stats),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("Mark period start dates in Daily Log to see phase breakdowns.")
else:
    st.info("No data yet. Head to Daily Log to start tracking!")
