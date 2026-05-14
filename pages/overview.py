"""
pages/overview.py — P&L Overview page.
"""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html
import pandas as pd

from charts import margin_trend, pnl_waterfall, revenue_history
from config import COLORS
from edgar import load_financials

dash.register_page(__name__, path="/", name="Overview", title="Overview — TMO FP&A")


# ─────────────────────────────────────────────────────────────────────────────
# KPI CARD HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _kpi(label: str, value: str, delta: str | None = None, positive: bool = True) -> html.Div:
    delta_el = html.Div(delta, className=f"kpi-delta {'delta-pos' if positive else 'delta-neg'}") if delta else None
    return html.Div([
        html.Div(value, className="kpi-value"),
        html.Div(label, className="kpi-label"),
        delta_el,
    ], className="kpi-card")


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

layout = html.Div([
    html.Div([
        html.H1("P&L Overview", className="page-title"),
        html.P("Quarterly actuals · Thermo Fisher Scientific (TMO) · Source: SEC EDGAR 10-Q/10-K", className="page-subtitle"),
    ], className="page-header"),

    html.Div(id="overview-kpis"),

    dbc.Row([
        dbc.Col(html.Div(dcc.Graph(id="revenue-hist-chart", config={"displayModeBar": False}), className="chart-card"), md=8),
        dbc.Col(html.Div(dcc.Graph(id="waterfall-chart",    config={"displayModeBar": False}), className="chart-card"), md=4),
    ], className="g-3 mb-3"),

    dbc.Row([
        dbc.Col(html.Div(dcc.Graph(id="margin-trend-chart", config={"displayModeBar": False}), className="chart-card"), md=12),
    ]),
])


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACKS
# ─────────────────────────────────────────────────────────────────────────────

@callback(
    Output("overview-kpis",       "children"),
    Output("revenue-hist-chart",  "figure"),
    Output("waterfall-chart",     "figure"),
    Output("margin-trend-chart",  "figure"),
    Input("url", "pathname"),
)
def update_overview(_):
    df  = load_financials()
    row = df.iloc[-1]
    prev = df.iloc[-5] if len(df) >= 5 else df.iloc[0]

    def _delta(curr, prev_val, fmt=".1f", suffix="%"):
        d = curr - prev_val
        sign = "▲" if d >= 0 else "▼"
        return f"{sign} {abs(d):{fmt}}{suffix} YoY", d >= 0

    rev_d,  rev_pos  = _delta(row["revenue"],          prev["revenue"],          fmt=",.0f", suffix="M")
    gm_d,   gm_pos   = _delta(row["gross_margin"],      prev["gross_margin"],      fmt=".1f",  suffix=" pp")
    oi_d,   oi_pos   = _delta(row["operating_income"],  prev["operating_income"],  fmt=",.0f", suffix="M")
    ni_d,   ni_pos   = _delta(row["net_income"],        prev["net_income"],        fmt=",.0f", suffix="M")

    kpis = dbc.Row([
        dbc.Col(_kpi("Revenue",           f"${row['revenue']:,.0f}M",          rev_d, rev_pos), md=3),
        dbc.Col(_kpi("Gross Margin",      f"{row['gross_margin']:.1f}%",       gm_d,  gm_pos),  md=3),
        dbc.Col(_kpi("Operating Income",  f"${row['operating_income']:,.0f}M", oi_d,  oi_pos),  md=3),
        dbc.Col(_kpi("Net Income",        f"${row['net_income']:,.0f}M",       ni_d,  ni_pos),  md=3),
    ], className="g-3 mb-3")

    return kpis, revenue_history(df), pnl_waterfall(df), margin_trend(df)
