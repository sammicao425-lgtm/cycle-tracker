import streamlit as st
from datetime import date, timedelta
import calendar

import pandas as pd
import plotly.graph_objects as go

from models.daily_log import get_logs_range, SUPPLEMENTS, SUPP_COLUMNS, EXERCISES, EXERCISE_COLUMNS
from models.cycle import get_cycle_phase, PHASE_COLORS
from models.moon import get_key_moon_dates

st.header("History")

# --- Month selector ---
today = date.today()
col1, col2 = st.columns(2)
with col1:
    sel_year = st.selectbox("Year", range(today.year, today.year - 3, -1))
with col2:
    sel_month = st.selectbox(
        "Month",
        range(1, 13),
        index=today.month - 1,
        format_func=lambda m: calendar.month_name[m],
    )

# Date range for selected month
first_day = date(sel_year, sel_month, 1)
last_day = date(sel_year, sel_month, calendar.monthrange(sel_year, sel_month)[1])

# Fetch data
df = get_logs_range(first_day, last_day)
log_dict = {}
if not df.empty:
    for _, row in df.iterrows():
        d = row["log_date"]
        if hasattr(d, "date"):
            d = d.date()
        log_dict[d] = row

# --- Build calendar heatmap ---
# Build a 6x7 grid (weeks x days)
cal = calendar.Calendar(firstweekday=0)  # Monday start
month_days = list(cal.itermonthdates(sel_year, sel_month))

# Group into weeks
weeks = []
week = []
for d in month_days:
    week.append(d)
    if len(week) == 7:
        weeks.append(week)
        week = []

# Get moon dates for this month
moon_dates = {m["date"]: m["type"] for m in get_key_moon_dates(first_day, last_day)}

# Build grid data
z_values = []  # color values (phase index)
hover_texts = []
day_labels = []

phase_to_num = {"menstrual": 1, "follicular": 2, "ovulation": 3, "luteal": 4}

for week in weeks:
    z_row = []
    hover_row = []
    label_row = []
    for d in week:
        if d.month != sel_month:
            z_row.append(0)
            hover_row.append("")
            label_row.append("")
            continue

        phase = get_cycle_phase(d)
        z_row.append(phase_to_num.get(phase, 0) if phase else 0)

        # Build hover text
        parts = [f"<b>{d.strftime('%b %d')}</b>"]
        if phase:
            parts.append(f"Phase: {phase.title()}")
        if d in moon_dates:
            parts.append(f"Moon: {moon_dates[d]}")
        if d in log_dict:
            row = log_dict[d]
            hrv = row.get("sleep_hrv")
            if hrv and pd.notna(hrv):
                parts.append(f"HRV: {hrv:.0f} ms")
            # Exercise
            ex_done = [dn for cn, dn in EXERCISES if row.get(cn)]
            if ex_done:
                ex_dur = row.get("exercise_duration_min")
                ex_str = ", ".join(ex_done)
                parts.append(f"Exercise: {ex_str}" + (f" ({ex_dur:.0f} min)" if ex_dur else ""))
            if row.get("breath_practice"):
                dur = row.get("breath_duration_min")
                parts.append(f"Breath: {dur:.0f} min" if dur else "Breath: yes")
            taken = sum(1 for c in SUPP_COLUMNS if row.get(c))
            parts.append(f"Supplements: {taken}/{len(SUPP_COLUMNS)}")
        else:
            parts.append("<i>No log</i>")

        hover_row.append("<br>".join(parts))

        # Day label
        moon_icon = ""
        if d in moon_dates:
            moon_icon = "\U0001F315" if moon_dates[d] == "Full Moon" else "\U0001F311"
        label_row.append(f"{d.day}{moon_icon}")

    z_values.append(z_row)
    hover_texts.append(hover_row)
    day_labels.append(label_row)

# Custom colorscale: 0=gray (not this month/no phase), 1-4 = phase colors
colorscale = [
    [0.0, "#F5F5F5"],   # empty/no phase
    [0.25, "#E57373"],  # menstrual
    [0.5, "#81C784"],   # follicular
    [0.75, "#64B5F6"],  # ovulation
    [1.0, "#FFD54F"],   # luteal
]

fig = go.Figure(
    data=go.Heatmap(
        z=z_values,
        text=day_labels,
        texttemplate="%{text}",
        textfont=dict(size=13),
        hovertext=hover_texts,
        hoverinfo="text",
        colorscale=colorscale,
        zmin=0,
        zmax=4,
        showscale=False,
        xgap=3,
        ygap=3,
    )
)

fig.update_layout(
    height=280,
    margin=dict(t=30, b=10, l=10, r=10),
    xaxis=dict(
        tickmode="array",
        tickvals=list(range(7)),
        ticktext=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        side="top",
    ),
    yaxis=dict(autorange="reversed", showticklabels=False),
)

st.plotly_chart(fig, use_container_width=True)

# Phase legend
legend_cols = st.columns(4)
for i, (phase, color) in enumerate(PHASE_COLORS.items()):
    with legend_cols[i]:
        st.markdown(
            f'<span style="background:{color};padding:2px 8px;border-radius:4px;'
            f'font-size:0.85em;color:#333">{phase.title()}</span>',
            unsafe_allow_html=True,
        )

st.divider()

# --- Detailed table ---
st.subheader("Daily Details")

if not df.empty:
    display_df = df.copy()
    if pd.api.types.is_datetime64_any_dtype(display_df["log_date"]):
        display_df["log_date"] = display_df["log_date"].dt.strftime("%b %d")

    # Rename columns for display
    rename_map = {"log_date": "Date", "sleep_hrv": "HRV (ms)", "breath_practice": "Breath", "breath_duration_min": "Breath min", "exercise_duration_min": "Exercise min"}
    for col, name, _ in SUPPLEMENTS:
        rename_map[col] = name
    for col, name in EXERCISES:
        rename_map[col] = name

    cols_to_show = ["log_date", "sleep_hrv"] + EXERCISE_COLUMNS + ["exercise_duration_min", "breath_practice", "breath_duration_min"] + SUPP_COLUMNS
    cols_to_show = [c for c in cols_to_show if c in display_df.columns]
    display_df = display_df[cols_to_show].rename(columns=rename_map)

    # Convert booleans to checkmarks
    bool_cols = ["Breath"] + [e[1] for e in EXERCISES if e[1] in display_df.columns] + [s[1] for s in SUPPLEMENTS if s[1] in display_df.columns]
    for bc in bool_cols:
        if bc in display_df.columns:
            display_df[bc] = display_df[bc].apply(lambda x: "\u2705" if x else "")

    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("No logs for this month yet.")
