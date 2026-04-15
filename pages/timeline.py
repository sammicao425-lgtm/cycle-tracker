import streamlit as st
from datetime import date, timedelta

import pandas as pd

from models.daily_log import get_logs_range, SUPPLEMENTS, SUPP_COLUMNS, EXERCISES, EXERCISE_COLUMNS, DYSREG_COLUMNS, ENERGY_COLUMNS
from models.cycle import get_cycle_phase
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
exercise_colors = {
    "Zone 2 Run": "#42A5F5",
    "PT Weight Training": "#AB47BC",
    "Home Gym": "#FF7043",
}
st.caption("**Exercise** &nbsp; | &nbsp; **Breath**: green = yes, gray = rest &nbsp; | &nbsp; **Symptoms**: red = present, gray = none")
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

    # Energy & symptom stats
    e1, e2, e3 = st.columns(3)
    with e1:
        if "energy_am" in df.columns:
            am_vals = df["energy_am"][df["energy_am"] > 0]
            st.metric("Avg AM Energy", f"{am_vals.mean():.1f}/5" if not am_vals.empty else "—")
        else:
            st.metric("Avg AM Energy", "—")
    with e2:
        if "energy_pm" in df.columns:
            pm_vals = df["energy_pm"][df["energy_pm"] > 0]
            st.metric("Avg PM Energy", f"{pm_vals.mean():.1f}/5" if not pm_vals.empty else "—")
        else:
            st.metric("Avg PM Energy", "—")
    with e3:
        symptom_cols = [c for c in DYSREG_COLUMNS + ["discomfort"] if c in df.columns]
        if symptom_cols and len(df) > 0:
            symptom_days = (df[symptom_cols].sum(axis=1) > 0).mean() * 100
            st.metric("Symptom Days", f"{symptom_days:.0f}%")
        else:
            st.metric("Symptom Days", "—")

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
            am_vals = phase_df["energy_am"][phase_df["energy_am"] > 0] if "energy_am" in phase_df.columns else pd.Series(dtype=float)
            pm_vals = phase_df["energy_pm"][phase_df["energy_pm"] > 0] if "energy_pm" in phase_df.columns else pd.Series(dtype=float)
            symptom_cols = [c for c in DYSREG_COLUMNS + ["discomfort"] if c in phase_df.columns]
            sym_pct = (phase_df[symptom_cols].sum(axis=1) > 0).mean() * 100 if symptom_cols else 0
            phase_stats.append({
                "Phase": phase.title(),
                "Days": len(phase_df),
                "Avg HRV (ms)": f"{hrv_mean:.0f}" if pd.notna(hrv_mean) else "—",
                "AM Energy": f"{am_vals.mean():.1f}" if not am_vals.empty else "—",
                "PM Energy": f"{pm_vals.mean():.1f}" if not pm_vals.empty else "—",
                "Symptom %": f"{sym_pct:.0f}%",
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
