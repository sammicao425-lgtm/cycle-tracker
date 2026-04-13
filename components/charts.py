from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from models.cycle import get_phase_for_dates, PHASE_COLORS
from models.moon import get_key_moon_dates
from models.daily_log import SUPP_COLUMNS, SUPPLEMENTS, EXERCISES, EXERCISE_COLUMNS


def build_timeline_chart(
    df: pd.DataFrame, start_date: date, end_date: date
) -> go.Figure:
    """Build the main timeline overlay chart.

    Layers:
    - Background bands for cycle phases
    - HRV line
    - Breath practice markers
    - Supplement adherence (% of taken per day)
    - Moon markers (full + new moon vertical lines)
    """
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.4, 0.2, 0.2, 0.2],
        subplot_titles=("Sleep HRV", "Exercise", "Breath Practice", "Supplement Adherence"),
    )

    # --- Cycle phase background bands ---
    phase_dates = get_phase_for_dates(start_date, end_date)
    if phase_dates:
        current_phase = phase_dates[0][1]
        band_start = phase_dates[0][0]
        for i in range(1, len(phase_dates)):
            d, phase = phase_dates[i]
            if phase != current_phase or i == len(phase_dates) - 1:
                # Close the band
                band_end = d if phase != current_phase else d
                if current_phase and current_phase in PHASE_COLORS:
                    for row in range(1, 5):
                        fig.add_vrect(
                            x0=band_start,
                            x1=band_end,
                            fillcolor=PHASE_COLORS[current_phase],
                            opacity=0.12,
                            line_width=0,
                            row=row,
                            col=1,
                        )
                current_phase = phase
                band_start = d

    # --- Moon markers ---
    moon_dates = get_key_moon_dates(start_date, end_date)
    for m in moon_dates:
        symbol = "\U0001F315" if m["type"] == "Full Moon" else "\U0001F311"
        for row in range(1, 5):
            fig.add_vline(
                x=m["date"],
                line_dash="dot",
                line_color="#9E9E9E" if m["type"] == "New Moon" else "#FFC107",
                line_width=1,
                row=row,
                col=1,
            )
        # Add annotation only on top row
        fig.add_annotation(
            x=m["date"],
            y=1.05,
            yref="y domain",
            text=symbol,
            showarrow=False,
            font=dict(size=14),
            row=1,
            col=1,
        )

    if df.empty:
        fig.update_layout(
            height=500,
            title_text="No data yet — start logging!",
            showlegend=False,
        )
        return fig

    # Ensure log_date is datetime
    if not pd.api.types.is_datetime64_any_dtype(df["log_date"]):
        df["log_date"] = pd.to_datetime(df["log_date"])

    # --- Row 1: HRV line ---
    hrv_data = df.dropna(subset=["sleep_hrv"])
    if not hrv_data.empty:
        fig.add_trace(
            go.Scatter(
                x=hrv_data["log_date"],
                y=hrv_data["sleep_hrv"],
                mode="lines+markers",
                name="HRV",
                line=dict(color="#7E57C2", width=2),
                marker=dict(size=6),
                hovertemplate="%{x|%b %d}: %{y:.0f} ms<extra></extra>",
            ),
            row=1,
            col=1,
        )

    # --- Row 2: Exercise ---
    exercise_colors = {"exercise_zone2_run": "#42A5F5", "exercise_pt_weights": "#AB47BC"}
    for col_name, display_name in EXERCISES:
        if col_name in df.columns:
            ex_data = df[df[col_name] == 1].copy()
            if not ex_data.empty:
                durations = ex_data["exercise_duration_min"].fillna(0) if "exercise_duration_min" in ex_data.columns else [0] * len(ex_data)
                fig.add_trace(
                    go.Scatter(
                        x=ex_data["log_date"],
                        y=[1] * len(ex_data),
                        mode="markers",
                        name=display_name,
                        marker=dict(
                            size=12,
                            color=exercise_colors.get(col_name, "#888"),
                            symbol="triangle-up",
                        ),
                        hovertemplate="%{x|%b %d}: " + display_name + " %{customdata:.0f} min<extra></extra>",
                        customdata=durations,
                    ),
                    row=2,
                    col=1,
                )

    # --- Row 3: Breath practice ---
    breath_data = df[df["breath_practice"] == 1].copy()
    if not breath_data.empty:
        sizes = breath_data["breath_duration_min"].fillna(5).clip(lower=3)
        fig.add_trace(
            go.Scatter(
                x=breath_data["log_date"],
                y=[1] * len(breath_data),
                mode="markers",
                name="Breath",
                marker=dict(
                    size=sizes * 2,
                    color="#26A69A",
                    symbol="diamond",
                ),
                hovertemplate="%{x|%b %d}: %{customdata:.0f} min<extra></extra>",
                customdata=breath_data["breath_duration_min"].fillna(0),
            ),
            row=3,
            col=1,
        )
    # Mark no-practice days
    no_breath = df[df["breath_practice"] == 0]
    if not no_breath.empty:
        fig.add_trace(
            go.Scatter(
                x=no_breath["log_date"],
                y=[1] * len(no_breath),
                mode="markers",
                name="No practice",
                marker=dict(size=6, color="#E0E0E0", symbol="x"),
                hovertemplate="%{x|%b %d}: skipped<extra></extra>",
            ),
            row=3,
            col=1,
        )

    # --- Row 4: Supplement adherence ---
    if any(col in df.columns for col in SUPP_COLUMNS):
        available_cols = [c for c in SUPP_COLUMNS if c in df.columns]
        df["supp_pct"] = df[available_cols].sum(axis=1) / len(available_cols) * 100
        fig.add_trace(
            go.Bar(
                x=df["log_date"],
                y=df["supp_pct"],
                name="Supplements",
                marker_color="#FF8A65",
                opacity=0.8,
                hovertemplate="%{x|%b %d}: %{y:.0f}%<extra></extra>",
            ),
            row=4,
            col=1,
        )

    # --- Layout ---
    fig.update_layout(
        height=700,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=60, b=40, l=50, r=30),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="ms", row=1, col=1)
    fig.update_yaxes(visible=False, row=2, col=1)
    fig.update_yaxes(visible=False, row=3, col=1)
    fig.update_yaxes(title_text="%", range=[0, 105], row=4, col=1)

    return fig
