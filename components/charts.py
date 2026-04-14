from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from models.cycle import get_phase_for_dates, PHASE_COLORS, PHASE_ORDER
from models.moon import get_key_moon_dates
from models.daily_log import SUPP_COLUMNS, SUPPLEMENTS, EXERCISES, EXERCISE_COLUMNS


def build_timeline_chart(
    df: pd.DataFrame, start_date: date, end_date: date
) -> go.Figure:
    """Build the timeline chart.

    Row 1 (main): HRV trend line with cycle phase colored bands + moon markers
    Row 2: Simple colored blocks — breath practice (yes/no)
    Row 3: Simple colored blocks — exercise (yes/no, color per type)
    """
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.15, 0.15],
        subplot_titles=("Sleep HRV", "Breath", "Exercise"),
    )

    # --- Cycle phase background bands (all rows) ---
    phase_dates = get_phase_for_dates(start_date, end_date)
    if phase_dates:
        current_phase = phase_dates[0][1]
        band_start = phase_dates[0][0]
        for i in range(1, len(phase_dates)):
            d, phase = phase_dates[i]
            if phase != current_phase or i == len(phase_dates) - 1:
                band_end = d if phase != current_phase else d
                if current_phase and current_phase in PHASE_COLORS:
                    for row in range(1, 4):
                        fig.add_vrect(
                            x0=band_start,
                            x1=band_end,
                            fillcolor=PHASE_COLORS[current_phase],
                            opacity=0.15,
                            line_width=0,
                            row=row,
                            col=1,
                        )
                current_phase = phase
                band_start = d

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
            height=450,
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

    # --- Layout ---
    fig.update_layout(
        height=500,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=30, l=50, r=30),
        hovermode="x unified",
        bargap=0,
    )
    fig.update_yaxes(title_text="ms", row=1, col=1)
    fig.update_yaxes(visible=False, fixedrange=True, row=2, col=1)
    fig.update_yaxes(visible=False, fixedrange=True, row=3, col=1)

    return fig
