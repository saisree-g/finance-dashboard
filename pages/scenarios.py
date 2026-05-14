"""
pages/scenarios.py — Scenario planning page.
"""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html
import pandas as pd

from charts import scenario_chart
from config import COLORS, SCENARIO_ADJUSTMENTS
from edgar import load_financials
from models import run_all_forecasts

dash.register_page(__name__, path="/scenarios", name="Scenarios", title="Scenarios — TMO FP&A")


layout = html.Div([
    html.Div([
        html.H1("Scenario Planning", className="page-title"),
        html.P("Base · Optimistic (+8%) · Pessimistic (-8%) applied to Ensemble forecast", className="page-subtitle"),
    ], className="page-header"),

    dbc.Row([
        dbc.Col(html.Div(dcc.Graph(id="scenario-chart", config={"displayModeBar": False}), className="chart-card"), md=8),
        dbc.Col(html.Div(id="scenario-summary"), md=4),
    ], className="g-3 mb-3"),

    html.Div(id="scenario-table", className="chart-card"),
])


@callback(
    Output("scenario-chart",   "figure"),
    Output("scenario-summary", "children"),
    Output("scenario-table",   "children"),
    Input("url", "pathname"),
)
def update_scenarios(_):
    df        = load_financials()
    series    = df["revenue"].dropna()
    forecasts = run_all_forecasts(series)

    fig = scenario_chart(df, forecasts)

    if "Ensemble" not in forecasts:
        return fig, html.Div("Forecast not available."), html.Div()

    base_fc = forecasts["Ensemble"]["forecast"]
    dates   = forecasts["Ensemble"]["dates"]

    # Summary cards
    summary_cards = html.Div([
        html.Div("4-Quarter Total Projection", style={"fontWeight": "600", "fontSize": "0.85rem", "marginBottom": "0.8rem", "color": COLORS["text_mid"]}),
        *[
            html.Div([
                html.Div(name, className="kpi-label"),
                html.Div(f"${sum(base_fc) * (1 + adj):,.0f}M", className="kpi-value",
                         style={"fontSize": "1.3rem",
                                "color": COLORS["positive"] if adj > 0 else COLORS["negative"] if adj < 0 else COLORS["accent"]}),
                html.Div(f"{adj*100:+.0f}% on base", style={"fontSize": "0.7rem", "color": COLORS["text_mid"]}),
            ], className="kpi-card mb-3")
            for name, adj in SCENARIO_ADJUSTMENTS.items()
        ],
    ])

    # Table
    rows = []
    for i, (date, base) in enumerate(zip(dates, base_fc)):
        quarter = date.to_period("Q").strftime("Q%q %Y")
        rows.append({
            "Quarter":         quarter,
            "Pessimistic ($M)": f"${base * 0.92:,.0f}",
            "Base ($M)":        f"${base:,.0f}",
            "Optimistic ($M)":  f"${base * 1.08:,.0f}",
        })
    tbl = dbc.Table.from_dataframe(
        pd.DataFrame(rows), striped=True, hover=True,
        bordered=False, size="sm", className="mb-0",
        style={"fontSize": "0.82rem"},
    )
    table_section = html.Div([
        html.Div("Quarter-by-Quarter Scenario Table", style={"fontWeight": "600", "marginBottom": "0.6rem", "fontSize": "0.9rem"}),
        tbl,
    ])

    return fig, summary_cards, table_section
