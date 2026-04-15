from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from models.cycle import PHASE_COLORS
from models.moon import get_key_moon_dates
from models.daily_log import SUPP_COLUMNS, SUPPLEMENTS, EXERCISES, EXERCISE_COLUMNS, DYSREG_COLUMNS, DYSREG_SYMPTOMS


def build_timeline_chart(
    df: pd.DataFrame, start_date: date, end_date: date
) -> go.Figure:
    """Build the timeline chart.

    Row 1 (main): HRV trend line + energy traces + moon markers
    Row 2: Simple colored blocks — breath practice (yes/no)
    Row 3: Simple colored blocks — exercise (yes/no, color per type)
    Row 4: Symptom count bars (0-4 dysregulation symptoms + discomfort)
    """
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.55, 0.15, 0.15, 0.15],
        subplot_titles=("Sleep HRV & Energy", "Breath", "Exercise", "Symptoms"),
    )

    # --- Moon markers (vertical lines on main chart only) ---
    moon_dates = get_key_moon_dates(start_date, end_date)
    for m in moon_dates:
        symbol = "\U0001F315" if m["type"] == "Full Moon" else "\U0001F311"
        line_color = "#FFC107" if m["type"] == "Full Moon" else "#9E9E9E"
        fig.add_vline(
            x=m["date"],
            line_dash="dot",
            line_color=line_color,
            line_width=1.5,
            row=1,
            col=1,
        )
        fig.add_annotation(
            x=m["date"],
            y=1.08,
            yref="y domain",
            text=symbol,
            showarrow=False,
            font=dict(size=16),
            row=1,
            col=1,
        )

    if df.empty:
        fig.update_layout(
            height=550,
            title_text="No data yet — start logging!",
            showlegend=False,
        )
        return fig

    # Ensure log_date is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["log_date"]):
        df["log_date"] = pd.to_datetime(df["log_date"])

    # --- Row 1: HRV trend line ---
    hrv_data = df.dropna(subset=["sleep_hrv"])
    if not hrv_data.empty:
        fig.add_trace(
            go.Scatter(
                x=hrv_data["log_date"],
                y=hrv_data["sleep_hrv"],
                mode="lines+markers",
                name="HRV",
                line=dict(color="#7E57C2", width=2.5),
                marker=dict(size=5),
                hovertemplate="%{x|%b %d}: %{y:.0f} ms<extra></extra>",
            ),
            row=1,
            col=1,
        )

    # --- Row 1 (cont): Energy traces on secondary y-axis ---
    if "energy_am" in df.columns:
        am_data = df[df["energy_am"] > 0]
        if not am_data.empty:
            fig.add_trace(
                go.Scatter(
                    x=am_data["log_date"],
                    y=am_data["energy_am"],
                    mode="lines+markers",
                    name="AM Energy",
                    line=dict(color="#FF8A65", width=1.5, dash="dot"),
                    marker=dict(size=4),
                    hovertemplate="%{x|%b %d}: AM %{y}/5<extra></extra>",
                    yaxis="y2",
                ),
                row=1,
                col=1,
            )
    if "energy_pm" in df.columns:
        pm_data = df[df["energy_pm"] > 0]
        if not pm_data.empty:
            fig.add_trace(
                go.Scatter(
                    x=pm_data["log_date"],
                    y=pm_data["energy_pm"],
                    mode="lines+markers",
                    name="PM Energy",
                    line=dict(color="#4DB6AC", width=1.5, dash="dot"),
                    marker=dict(size=4),
                    hovertemplate="%{x|%b %d}: PM %{y}/5<extra></extra>",
                    yaxis="y2",
                ),
                row=1,
                col=1,
            )

    # --- Row 2: Breath practice — simple colored blocks ---
    for _, row in df.iterrows():
        d = row["log_date"]
        did_breath = row.get("breath_practice", 0) == 1
        color = "#26A69A" if did_breath else "#E0E0E0"
        fig.add_trace(
            go.Bar(
                x=[d],
                y=[1],
                marker_color=color,
                width=86400000,  # 1 day in ms
                showlegend=False,
                hovertemplate="%{x|%b %d}: " + ("Yes" if did_breath else "No") + "<extra></extra>",
            ),
            row=2,
            col=1,
        )

    # --- Row 3: Exercise — colored blocks per type ---
    exercise_colors = {
        "exercise_zone2_run": "#42A5F5",
        "exercise_pt_weights": "#AB47BC",
        "exercise_home_gym": "#FF7043",
    }
    for _, row in df.iterrows():
        d = row["log_date"]
        done = [col for col in EXERCISE_COLUMNS if row.get(col, 0) == 1]
        if done:
            # Use color of first exercise type done that day
            color = exercise_colors.get(done[0], "#888")
            label = ", ".join(
                next(dn for cn, dn in EXERCISES if cn == c) for c in done
            )
        else:
            color = "#E0E0E0"
            label = "Rest"
        fig.add_trace(
            go.Bar(
                x=[d],
                y=[1],
                marker_color=color,
                width=86400000,
                showlegend=False,
                hovertemplate="%{x|%b %d}: " + label + "<extra></extra>",
            ),
            row=3,
            col=1,
        )

    # --- Row 4: Symptom count bars ---
    symptom_cols_in_df = [c for c in DYSREG_COLUMNS + ["discomfort"] if c in df.columns]
    if symptom_cols_in_df:
        for _, row in df.iterrows():
            d = row["log_date"]
            count = sum(1 for c in symptom_cols_in_df if row.get(c, 0) == 1)
            color = "#EF5350" if count > 0 else "#E0E0E0"
            # Build hover label
            if count > 0:
                active = []
                if row.get("discomfort", 0):
                    active.append("Discomfort")
                active += [dn for cn, dn in DYSREG_SYMPTOMS if row.get(cn, 0) == 1]
                label = ", ".join(active)
            else:
                label = "None"
            fig.add_trace(
                go.Bar(
                    x=[d],
                    y=[count],
                    marker_color=color,
                    width=86400000,
                    showlegend=False,
                    hovertemplate="%{x|%b %d}: " + label + "<extra></extra>",
                ),
                row=4,
                col=1,
            )

    # --- Layout ---
    fig.update_layout(
        height=600,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=30, l=50, r=30),
        hovermode="x unified",
        bargap=0,
    )
    fig.update_yaxes(title_text="ms", row=1, col=1)
    # Secondary y-axis for energy (1-5) overlaid on row 1
    fig.update_layout(
        yaxis2=dict(
            title="Energy",
            overlaying="y",
            side="right",
            range=[0.5, 5.5],
            showgrid=False,
        ),
    )
    fig.update_yaxes(visible=False, fixedrange=True, row=2, col=1)
    fig.update_yaxes(visible=False, fixedrange=True, row=3, col=1)
    fig.update_yaxes(title_text="count", fixedrange=True, row=4, col=1)

    return fig
