import streamlit as st
from datetime import date

from models.daily_log import (
    save_log, get_log, SUPPLEMENTS, EXERCISES, DYSREG_SYMPTOMS,
)
from models.cycle import (
    get_cycle_day, get_cycle_phase, is_period_start,
    add_period_start, delete_period_start, PHASE_COLORS,
)
from models.moon import get_moon_info

st.header("Daily Log")

# --- Date picker ---
log_date = st.date_input("Date", value=date.today())

# --- Auto-computed status ---
cycle_day = get_cycle_day(log_date)
phase = get_cycle_phase(log_date)
moon = get_moon_info(log_date)

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Cycle Day", cycle_day if cycle_day else "—")
with c2:
    if phase:
        color = PHASE_COLORS.get(phase, "#888")
        st.markdown(
            f'<span style="background:{color};padding:4px 12px;border-radius:8px;'
            f'font-weight:600;color:#333">{phase.title()}</span>',
            unsafe_allow_html=True,
        )
    else:
        st.metric("Phase", "—")
with c3:
    st.metric("Moon", f"{moon['phase_name']}")

st.divider()

# --- Load existing data for this date ---
existing = get_log(log_date)

# --- Period start toggle ---
period_on = st.toggle(
    "\U0001FA78 Mark as period start date",
    value=is_period_start(log_date),
    key="period_toggle",
)

st.divider()

# --- Supplements ---
st.subheader("Supplements")

standard = [s for s in SUPPLEMENTS if s[2] == "standard"]
optional = [s for s in SUPPLEMENTS if s[2] == "optional"]
trial = [s for s in SUPPLEMENTS if s[2] == "trial"]

supp_values = {}

col_std, col_opt = st.columns(2)
with col_std:
    st.caption("**Standard (daily)**")
    for col_name, display_name, _ in standard:
        default = bool(existing.get(col_name, 0)) if existing else False
        supp_values[col_name] = st.checkbox(display_name, value=default, key=col_name)

with col_opt:
    st.caption("**Optional**")
    for col_name, display_name, _ in optional:
        default = bool(existing.get(col_name, 0)) if existing else False
        supp_values[col_name] = st.checkbox(display_name, value=default, key=col_name)

# Trial supplements with notes
if trial:
    st.caption("**Trial**")
    for col_name, display_name, _ in trial:
        default = bool(existing.get(col_name, 0)) if existing else False
        supp_values[col_name] = st.checkbox(display_name, value=default, key=col_name)

notes_default = str(existing.get("supp_notes", "")) if existing else ""
supp_notes = st.text_input("Supplement notes", value=notes_default, placeholder="e.g. Tru Niagen day 14, feeling more energy")

st.divider()

# --- Sleep HRV ---
st.subheader("Sleep HRV")
st.caption("Last night's sleep HRV (recorded the next day)")
hrv_default = float(existing["sleep_hrv"]) if existing and existing.get("sleep_hrv") else 0.0
sleep_hrv = st.number_input(
    "HRV (ms)", min_value=0.0, max_value=300.0, value=hrv_default, step=1.0
)

st.divider()

# --- Exercise ---
st.subheader("Exercise")
exercise_values = {}
ex_cols = st.columns(len(EXERCISES))
for i, (col_name, display_name) in enumerate(EXERCISES):
    with ex_cols[i]:
        default = bool(existing.get(col_name, 0)) if existing else False
        exercise_values[col_name] = st.checkbox(display_name, value=default, key=col_name)

any_exercise = any(exercise_values.values())
exercise_dur = 0.0
if any_exercise:
    dur_default = float(existing["exercise_duration_min"]) if existing and existing.get("exercise_duration_min") else 0.0
    exercise_dur = st.number_input(
        "Exercise duration (minutes)", min_value=0.0, max_value=300.0, value=dur_default, step=5.0
    )

st.divider()

# --- Breath practice ---
st.subheader("Slow Breath Practice")
breath_default = bool(existing.get("breath_practice", 0)) if existing else False
breath_on = st.toggle("Practiced today", value=breath_default)

breath_dur = 0.0
if breath_on:
    dur_default = float(existing["breath_duration_min"]) if existing and existing.get("breath_duration_min") else 0.0
    breath_dur = st.number_input(
        "Duration (minutes)", min_value=0.0, max_value=120.0, value=dur_default, step=1.0
    )

st.divider()

# --- Discomfort ---
st.subheader("Discomfort")
discomfort_default = bool(existing.get("discomfort", 0)) if existing else False
discomfort_on = st.toggle("Had discomfort today", value=discomfort_default)

discomfort_notes = ""
if discomfort_on:
    notes_default = str(existing.get("discomfort_notes", "")) if existing else ""
    discomfort_notes = st.text_input(
        "What happened?", value=notes_default,
        placeholder="e.g. 拉肚子, stomach pain...",
        key="discomfort_notes",
    )

st.divider()

# --- Energy & Nervous System ---
st.subheader("Energy & Nervous System")

ENERGY_LABELS = ["—", "1 Very Low", "2 Low", "3 OK", "4 Good", "5 Great"]

e_col1, e_col2 = st.columns(2)
with e_col1:
    am_default_idx = int(existing.get("energy_am", 0)) if existing else 0
    energy_am = st.select_slider(
        "AM Energy", options=ENERGY_LABELS,
        value=ENERGY_LABELS[am_default_idx],
        key="energy_am",
    )
with e_col2:
    pm_default_idx = int(existing.get("energy_pm", 0)) if existing else 0
    energy_pm = st.select_slider(
        "PM Energy", options=ENERGY_LABELS,
        value=ENERGY_LABELS[pm_default_idx],
        key="energy_pm",
    )

energy_am_val = ENERGY_LABELS.index(energy_am)
energy_pm_val = ENERGY_LABELS.index(energy_pm)

st.caption("**Dysregulation symptoms**")
symptom_values = {}
s_col1, s_col2 = st.columns(2)
half = len(DYSREG_SYMPTOMS) // 2
with s_col1:
    for col_name, display_name in DYSREG_SYMPTOMS[:half]:
        default = bool(existing.get(col_name, 0)) if existing else False
        symptom_values[col_name] = st.checkbox(display_name, value=default, key=col_name)
with s_col2:
    for col_name, display_name in DYSREG_SYMPTOMS[half:]:
        default = bool(existing.get(col_name, 0)) if existing else False
        symptom_values[col_name] = st.checkbox(display_name, value=default, key=col_name)

st.divider()

# --- Save ---
if st.button("Save", type="primary", use_container_width=True):
    # Handle period start
    if period_on:
        add_period_start(log_date)
    else:
        delete_period_start(log_date)

    # Build data dict
    data = {
        **supp_values,
        "supp_notes": supp_notes if supp_notes else None,
        "sleep_hrv": sleep_hrv if sleep_hrv > 0 else None,
        **exercise_values,
        "exercise_duration_min": exercise_dur if any_exercise else None,
        "breath_practice": int(breath_on),
        "breath_duration_min": breath_dur if breath_on else None,
        "discomfort": int(discomfort_on),
        "discomfort_notes": discomfort_notes if discomfort_on and discomfort_notes else None,
        "energy_am": energy_am_val if energy_am_val > 0 else None,
        "energy_pm": energy_pm_val if energy_pm_val > 0 else None,
        **symptom_values,
    }

    save_log(log_date, data)
    st.success(f"Saved log for {log_date.strftime('%b %d, %Y')}")
    st.rerun()
