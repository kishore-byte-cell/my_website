from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

try:
    # pyrefly: ignore [missing-import]
    import plotly.graph_objects as go
except Exception:  # pragma: no cover - optional dependency
    go = None

# Distinct Color Standard Specified by User
# 🔵 Past Original Rate: BLUE (#38BDF8)
# 🔴 Expected Past Rate: RED (#EF4444)
# 🟠 Future Expected Rate: ORANGE (#F97316)
COLOR_PAST_ORIGINAL = "#38BDF8"      # Electric Blue
COLOR_PAST_ORIGINAL_GLOW = "#7DD3FC" # Soft Blue Glow
COLOR_PAST_FILL = "rgba(56, 189, 248, 0.08)"

COLOR_EXPECTED_PAST = "#EF4444"      # Vibrant Red
COLOR_EXPECTED_PAST_GLOW = "#F87171" # Soft Red Glow

COLOR_FUTURE_EXPECTED = "#F97316"    # Vibrant Orange
COLOR_FUTURE_EXPECTED_GLOW = "#FB923C" # Soft Orange Glow
COLOR_FUTURE_CORRIDOR_FILL = "rgba(249, 115, 22, 0.20)"


def prepare_native_fallback_dataframe(
    history_df: pd.DataFrame,
    expected_past_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
) -> pd.DataFrame:
    """Create a clean 3-series DataFrame for Streamlit native chart fallback."""
    rows: Dict[str, Dict[str, Any]] = {}

    if history_df is not None and not history_df.empty:
        for _, row in history_df.iterrows():
            m_str = row["Month"].strftime("%Y-%m") if hasattr(row["Month"], "strftime") else str(row["Month"])
            if m_str not in rows:
                rows[m_str] = {}
            rows[m_str]["Past Original Rate (Blue)"] = float(row.get("Official Price", 0))

    if expected_past_df is not None and not expected_past_df.empty:
        for _, row in expected_past_df.iterrows():
            m_str = row["Month"].strftime("%Y-%m") if hasattr(row["Month"], "strftime") else str(row["Month"])
            if m_str not in rows:
                rows[m_str] = {}
            rows[m_str]["Expected Past Rate (Red)"] = float(row.get("Expected Price", 0))

    if forecast_df is not None and not forecast_df.empty:
        for _, row in forecast_df.iterrows():
            m_str = row["Month"].strftime("%Y-%m") if hasattr(row["Month"], "strftime") else str(row["Month"])
            if m_str not in rows:
                rows[m_str] = {}
            rows[m_str]["Future Expected Rate (Orange)"] = float(row.get("Expected Mid", 0))

    frame = pd.DataFrame.from_dict(rows, orient="index")
    frame.index.name = "Month"
    return frame.sort_index()


def build_vibrant_market_figure(
    selected_market: str,
    history_df: pd.DataFrame,
    expected_past_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    selected_source: str = "All Sources (Consensus)",
) -> Any:
    """Build a modern, vibrant Plotly chart with Blue (Past Original), Red (Expected Past), and Orange (Future Expected)."""
    if go is None:
        return None

    fig = go.Figure()

    # 1. 🔵 Past Original Rate (Official Spot History) - BLUE
    if history_df is not None and not history_df.empty:
        df_hist = history_df.sort_values("Month").reset_index(drop=True)
        fig.add_trace(
            go.Scatter(
                x=df_hist["Month"],
                y=df_hist["Official Price"],
                mode="lines+markers",
                name="Past Original Rate (Live Spot)",
                line=dict(color=COLOR_PAST_ORIGINAL, width=4, shape="spline", smoothing=1.3),
                marker=dict(
                    size=7,
                    color=COLOR_PAST_ORIGINAL_GLOW,
                    line=dict(color="#FFFFFF", width=1.5),
                ),
                fill="tozeroy",
                fillcolor=COLOR_PAST_FILL,
                hovertemplate="<b>🔵 Past Original Rate</b><br>Date: %{x|%b %Y}<br>Spot Rate: <b>$%{y:,.2f}</b><extra></extra>",
            )
        )

    # 2. 🔴 Expected Past Rate (Historical Institutional Forecast) - RED
    if expected_past_df is not None and not expected_past_df.empty:
        df_exp_past = expected_past_df.sort_values("Month").reset_index(drop=True)
        fig.add_trace(
            go.Scatter(
                x=df_exp_past["Month"],
                y=df_exp_past["Expected Price"],
                mode="lines+markers",
                name="Expected Past Rate (Historical Target)",
                line=dict(color=COLOR_EXPECTED_PAST, width=3, dash="dot", shape="spline", smoothing=1.3),
                marker=dict(
                    size=6,
                    color=COLOR_EXPECTED_PAST_GLOW,
                    line=dict(color="#FFFFFF", width=1.2),
                ),
                hovertemplate="<b>🔴 Expected Past Rate</b><br>Date: %{x|%b %Y}<br>Forecast: <b>$%{y:,.2f}</b><extra></extra>",
            )
        )

    # 3. 🟠 Future Expected Rate (Forward Institutional Corridor) - ORANGE
    if forecast_df is not None and not forecast_df.empty:
        df_fc = forecast_df.sort_values("Month").reset_index(drop=True)

        # Expected Mid Line
        fig.add_trace(
            go.Scatter(
                x=df_fc["Month"],
                y=df_fc["Expected Mid"],
                mode="lines+markers",
                name="Future Expected Rate (Target)",
                line=dict(color=COLOR_FUTURE_EXPECTED, width=4, shape="spline", smoothing=1.3),
                marker=dict(
                    size=7,
                    color=COLOR_FUTURE_EXPECTED_GLOW,
                    line=dict(color="#FFFFFF", width=1.5),
                ),
                hovertemplate="<b>🟠 Future Expected Rate</b><br>Date: %{x|%b %Y}<br>Target Mid: <b>$%{y:,.2f}</b><extra></extra>",
            )
        )

        # Translucent Corridor Area Fill
        fig.add_trace(
            go.Scatter(
                x=list(df_fc["Month"]) + list(df_fc["Month"])[::-1],
                y=list(df_fc["Range High"]) + list(df_fc["Range Low"])[::-1],
                fill="toself",
                mode="lines",
                name="Expected Range Corridor",
                line=dict(color=COLOR_FUTURE_EXPECTED, width=0),
                fillcolor=COLOR_FUTURE_CORRIDOR_FILL,
                showlegend=True,
                hoverinfo="skip",
            )
        )

    # Dark Glassmorphism Theme Layout Setup
    fig.update_layout(
        title=dict(
            text=f"<b>{selected_market}</b> — Multi-Source Rate Analysis ({selected_source})",
            font=dict(size=18, color="#F8FAFC", family="Inter, sans-serif"),
            x=0.01,
            y=0.95,
        ),
        paper_bgcolor="rgba(15, 23, 42, 0.0)",
        plot_bgcolor="rgba(11, 15, 25, 0.90)",
        font=dict(color="#94A3B8", family="Inter, sans-serif"),
        xaxis=dict(
            title=dict(text="Timeline (Past vs Future)", font=dict(color="#CBD5E1", size=13)),
            showgrid=True,
            gridcolor="rgba(51, 65, 85, 0.5)",
            gridwidth=1,
            zeroline=False,
            showline=True,
            linecolor="#334155",
            tickfont=dict(color="#CBD5E1"),
        ),
        yaxis=dict(
            title=dict(text="Rate / Price (USD or Local)", font=dict(color="#CBD5E1", size=13)),
            showgrid=True,
            gridcolor="rgba(51, 65, 85, 0.5)",
            gridwidth=1,
            zeroline=False,
            showline=True,
            linecolor="#334155",
            tickfont=dict(color="#CBD5E1"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            bgcolor="rgba(30, 41, 59, 0.85)",
            bordercolor="rgba(51, 65, 85, 0.8)",
            borderwidth=1,
            font=dict(color="#F1F5F9", size=12),
        ),
        margin=dict(l=30, r=30, t=75, b=40),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#1E293B",
            font_size=13,
            font_family="Inter, sans-serif",
            font_color="#F8FAFC",
            bordercolor=COLOR_PAST_ORIGINAL,
        ),
    )

    return fig


def render_market_chart(
    selected_market: str,
    history_df: pd.DataFrame,
    expected_past_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    selected_source: str = "All Sources (Consensus)",
) -> None:
    """Render the vibrant market chart with Plotly (or native 3-series fallback if Plotly is missing)."""
    try:
        fig = build_vibrant_market_figure(
            selected_market,
            history_df,
            expected_past_df,
            forecast_df,
            selected_source,
        )
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        else:
            fallback_df = prepare_native_fallback_dataframe(history_df, expected_past_df, forecast_df)
            st.line_chart(fallback_df, color=["#38BDF8", "#EF4444", "#F97316"])
    except Exception:
        fallback_df = prepare_native_fallback_dataframe(history_df, expected_past_df, forecast_df)
        st.line_chart(fallback_df, color=["#38BDF8", "#EF4444", "#F97316"])
