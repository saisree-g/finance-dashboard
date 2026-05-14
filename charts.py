"""
charts.py — Reusable Plotly figure builders for the finance dashboard.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import COLORS, MODEL_COLORS, SCENARIO_ADJUSTMENTS


# ─────────────────────────────────────────────────────────────────────────────
# SHARED THEME
# ─────────────────────────────────────────────────────────────────────────────

def _base_layout(**kwargs) -> dict:
    base = dict(
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font=dict(family="Inter, system-ui, sans-serif", color=COLORS["text"], size=12),
        margin=dict(t=80, b=50, l=60, r=20),
        title=dict(
            font=dict(size=14, color=COLORS["text"]),
            x=0, xanchor="left",
            y=0.98, yanchor="top",
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)", bordercolor=COLORS["border"],
            borderwidth=0, orientation="h",
            yanchor="top", y=-0.12,
            xanchor="left", x=0,
            font=dict(size=11),
        ),
        xaxis=dict(gridcolor=COLORS["border"], linecolor=COLORS["border"]),
        yaxis=dict(gridcolor=COLORS["border"], linecolor=COLORS["border"]),
    )
    base.update(kwargs)
    return base


# ─────────────────────────────────────────────────────────────────────────────
# REVENUE HISTORY
# ─────────────────────────────────────────────────────────────────────────────

def revenue_history(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["quarter_label"], y=df["revenue"],
        name="Revenue ($M)", marker_color=COLORS["primary"],
        hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.0f}M<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["quarter_label"], y=df["gross_margin"],
        name="Gross Margin (%)", yaxis="y2",
        line=dict(color=COLORS["positive"], width=2),
        hovertemplate="%{y:.1f}%<extra>Gross Margin</extra>",
    ))
    fig.update_layout(
        **_base_layout(
            title="Quarterly Revenue & Gross Margin",
            yaxis=dict(title="Revenue ($M)", gridcolor=COLORS["border"]),
            yaxis2=dict(
                title="Gross Margin (%)", overlaying="y", side="right",
                range=[0, 100], gridcolor="rgba(0,0,0,0)",
            ),
            barmode="group",
        )
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# P&L WATERFALL
# ─────────────────────────────────────────────────────────────────────────────

def pnl_waterfall(df: pd.DataFrame) -> go.Figure:
    latest = df.iloc[-1]
    cogs   = latest["revenue"] - latest["gross_profit"]
    opex   = latest["gross_profit"] - latest["operating_income"]

    labels  = ["Revenue", "COGS", "Gross Profit", "OpEx", "Operating Income"]
    values  = [latest["revenue"], -cogs, latest["gross_profit"], -opex, latest["operating_income"]]
    measure = ["absolute", "relative", "total", "relative", "total"]
    colors  = [
        COLORS["primary"], COLORS["negative"],
        COLORS["positive"], COLORS["negative"],
        COLORS["accent"],
    ]

    fig = go.Figure(go.Waterfall(
        name="P&L", measure=measure,
        x=labels, y=values,
        connector=dict(line=dict(color=COLORS["border"], width=1)),
        decreasing=dict(marker_color=COLORS["negative"]),
        increasing=dict(marker_color=COLORS["positive"]),
        totals=dict(marker_color=COLORS["accent"]),
        hovertemplate="<b>%{x}</b><br>$%{y:,.0f}M<extra></extra>",
        text=[f"${v:,.0f}M" for v in values],
        textposition="outside",
    ))
    fig.update_layout(
        **_base_layout(title=f"P&L Waterfall — {df['quarter_label'].iloc[-1]}")
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# FORECAST CHART
# ─────────────────────────────────────────────────────────────────────────────

def forecast_chart(df: pd.DataFrame, forecasts: dict, metric: str = "revenue") -> go.Figure:
    fig = go.Figure()

    # Historical actuals
    fig.add_trace(go.Scatter(
        x=df["quarter_label"], y=df[metric],
        name="Actual", mode="lines+markers",
        line=dict(color=MODEL_COLORS["Actual"], width=2),
        marker=dict(size=5),
        hovertemplate="<b>%{x}</b><br>Actual: $%{y:,.0f}M<extra></extra>",
    ))

    # Model forecasts
    for model_name, result in forecasts.items():
        fc     = result["forecast"]
        dates  = result["dates"]
        labels = dates.to_period("Q").strftime("Q%q %Y")
        color  = MODEL_COLORS.get(model_name, COLORS["neutral"])

        # Confidence interval (Ensemble / Prophet)
        if result.get("lower") is not None and result.get("upper") is not None:
            fig.add_trace(go.Scatter(
                x=list(labels) + list(labels[::-1]),
                y=list(result["upper"]) + list(result["lower"][::-1]),
                fill="toself", fillcolor=f"rgba(124,58,237,0.12)",
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=False, hoverinfo="skip",
                name=f"{model_name} CI",
            ))

        fig.add_trace(go.Scatter(
            x=labels, y=fc,
            name=f"{model_name} (MAPE: {result['mape']:.1f}%)",
            mode="lines+markers",
            line=dict(color=color, width=2, dash="dash"),
            marker=dict(size=6, symbol="diamond"),
            hovertemplate=f"<b>%{{x}}</b><br>{model_name}: $%{{y:,.0f}}M<extra></extra>",
        ))

    fig.update_layout(**_base_layout(
        title=f"{metric.replace('_', ' ').title()} Forecast — Next {len(list(forecasts.values())[0]['dates'])} Quarters",
        yaxis_title=f"{metric.replace('_', ' ').title()} ($M)",
    ))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MAPE COMPARISON
# ─────────────────────────────────────────────────────────────────────────────

def mape_bar(forecasts: dict) -> go.Figure:
    models = list(forecasts.keys())
    mapes  = [forecasts[m]["mape"] for m in models]
    colors = [
        COLORS["positive"] if m < 5 else COLORS["accent"] if m < 10 else COLORS["negative"]
        for m in mapes
    ]
    fig = go.Figure(go.Bar(
        x=models, y=mapes, marker_color=colors,
        text=[f"{m:.1f}%" for m in mapes], textposition="outside",
        hovertemplate="<b>%{x}</b><br>MAPE: %{y:.1f}%<extra></extra>",
    ))
    fig.add_hline(y=5, line_dash="dash", line_color=COLORS["positive"],
                  annotation_text="5% target", annotation_position="right")
    fig.update_layout(**_base_layout(
        title="Model Accuracy — Validation MAPE",
        yaxis_title="MAPE (%)", xaxis_title="Model",
    ))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# VARIANCE CHART
# ─────────────────────────────────────────────────────────────────────────────

def variance_chart(df: pd.DataFrame, forecasts: dict, metric: str = "revenue") -> go.Figure:
    if "Ensemble" not in forecasts:
        return go.Figure()

    # Align forecast with validation window
    fc_vals = forecasts["Ensemble"]["forecast"]
    n       = min(len(fc_vals), len(df))
    actual  = df[metric].iloc[-n:].values
    labels  = df["quarter_label"].iloc[-n:].tolist()

    variance     = actual - fc_vals[:n]
    variance_pct = variance / fc_vals[:n] * 100
    colors       = [COLORS["positive"] if v >= 0 else COLORS["negative"] for v in variance]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
        subplot_titles=["Actual vs Forecast ($M)", "Variance (%)"],
        row_heights=[0.6, 0.4],
    )
    fig.add_trace(go.Bar(
        x=labels, y=actual, name="Actual",
        marker_color=COLORS["primary"],
        hovertemplate="<b>%{x}</b><br>Actual: $%{y:,.0f}M<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=labels, y=fc_vals[:n], name="Forecast",
        line=dict(color=COLORS["forecast"], width=2, dash="dash"),
        hovertemplate="<b>%{x}</b><br>Forecast: $%{y:,.0f}M<extra></extra>",
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=labels, y=variance_pct, name="Variance %",
        marker_color=colors,
        hovertemplate="<b>%{x}</b><br>Variance: %{y:+.1f}%<extra></extra>",
        showlegend=False,
    ), row=2, col=1)
    fig.add_hline(y=5,  line_dash="dot", line_color=COLORS["positive"], row=2, col=1)
    fig.add_hline(y=-5, line_dash="dot", line_color=COLORS["negative"], row=2, col=1)

    fig.update_layout(**_base_layout(title="Actual vs Forecast Variance Analysis"))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO CHART
# ─────────────────────────────────────────────────────────────────────────────

def scenario_chart(df: pd.DataFrame, forecasts: dict, metric: str = "revenue") -> go.Figure:
    if "Ensemble" not in forecasts:
        return go.Figure()

    base_fc = forecasts["Ensemble"]["forecast"]
    dates   = forecasts["Ensemble"]["dates"]
    labels  = dates.to_period("Q").strftime("Q%q %Y")

    fig = go.Figure()
    # Historical
    fig.add_trace(go.Scatter(
        x=df["quarter_label"], y=df[metric],
        name="Historical", mode="lines",
        line=dict(color=COLORS["primary"], width=2),
    ))

    scenario_colors = {
        "Optimistic":  COLORS["positive"],
        "Base":        COLORS["forecast"],
        "Pessimistic": COLORS["negative"],
    }
    for scenario, adj in SCENARIO_ADJUSTMENTS.items():
        sc_fc = base_fc * (1 + adj)
        fig.add_trace(go.Scatter(
            x=labels, y=sc_fc,
            name=f"{scenario} ({adj*100:+.0f}%)",
            mode="lines+markers",
            line=dict(color=scenario_colors[scenario], width=2,
                      dash="solid" if scenario == "Base" else "dash"),
            marker=dict(size=7),
            hovertemplate=f"<b>%{{x}}</b><br>{scenario}: $%{{y:,.0f}}M<extra></extra>",
        ))

    # Shaded range between pessimistic and optimistic
    opt  = base_fc * (1 + 0.08)
    pess = base_fc * (1 - 0.08)
    fig.add_trace(go.Scatter(
        x=list(labels) + list(labels[::-1]),
        y=list(opt) + list(pess[::-1]),
        fill="toself", fillcolor="rgba(37,99,235,0.08)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False, hoverinfo="skip",
    ))

    fig.update_layout(**_base_layout(
        title="Scenario Planning — Base / Optimistic / Pessimistic",
        yaxis_title=f"{metric.replace('_',' ').title()} ($M)",
    ))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MARGIN TREND
# ─────────────────────────────────────────────────────────────────────────────

def margin_trend(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for col, name, color in [
        ("gross_margin",     "Gross Margin",     COLORS["positive"]),
        ("operating_margin", "Operating Margin", COLORS["accent"]),
        ("net_margin",       "Net Margin",       COLORS["forecast"]),
    ]:
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df["quarter_label"], y=df[col],
                name=name, mode="lines",
                line=dict(color=color, width=2),
                hovertemplate=f"<b>%{{x}}</b><br>{name}: %{{y:.1f}}%<extra></extra>",
            ))
    fig.update_layout(**_base_layout(
        title="Margin Trends", yaxis_title="Margin (%)",
    ))
    return fig
