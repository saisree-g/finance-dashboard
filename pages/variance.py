"""
pages/variance.py — Variance analysis page.
"""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html
import pandas as pd

from charts import variance_chart
from config import COLORS
from edgar import load_financials
from models import run_all_forecasts

dash.register_page(__name__, path="/variance", name="Variance", title="Variance — TMO FP&A")


layout = html.Div([
    html.Div([
        html.H1("Variance Analysis", className="page-title"),
        html.P("Actual vs Ensemble forecast · Quarters where variance exceeds ±5% are flagged", className="page-subtitle"),
    ], className="page-header"),

    html.Div(id="variance-flags", className="mb-3"),

    dbc.Row([
        dbc.Col(html.Div(dcc.Graph(id="variance-main-chart", config={"displayModeBar": False}), className="chart-card"), md=12),
    ], className="mb-3"),

    html.Div(id="variance-table", className="chart-card"),
])


@callback(
    Output("variance-flags",       "children"),
    Output("variance-main-chart",  "figure"),
    Output("variance-table",       "children"),
    Input("url", "pathname"),
)
def update_variance(_):
    df        = load_financials()
    series    = df["revenue"].dropna()
    forecasts = run_all_forecasts(series)

    fig = variance_chart(df, forecasts)

    # Variance flag summary
    if "Ensemble" in forecasts:
        fc     = forecasts["Ensemble"]["forecast"]
        n      = min(len(fc), len(df))
        actual = df["revenue"].iloc[-n:].values
        labels = df["quarter_label"].iloc[-n:].tolist()
        var_pct = (actual - fc[:n]) / fc[:n] * 100

        flags = [
            dbc.Badge(
                f"{lbl}: {v:+.1f}%",
                color="success" if v >= 0 else "danger",
                className="me-2 mb-2",
                style={"fontSize": "0.75rem"},
            )
            for lbl, v in zip(labels, var_pct)
            if abs(v) > 5
        ]
        flag_section = html.Div([
            html.Div("Quarters with >5% variance", style={"fontSize": "0.72rem", "fontWeight": "600", "color": COLORS["text_mid"], "marginBottom": "0.5rem"}),
            html.Div(flags if flags else "No quarters exceed ±5% threshold ✓"),
        ])
    else:
        flag_section = html.Div()

    # Variance table
    if "Ensemble" in forecasts:
        rows = []
        for lbl, act, fc_val, pct in zip(labels, actual, fc[:n], var_pct):
            rows.append({
                "Quarter":       lbl,
                "Actual ($M)":   f"${act:,.0f}",
                "Forecast ($M)": f"${fc_val:,.0f}",
                "Variance ($M)": f"${act - fc_val:+,.0f}",
                "Variance (%)":  f"{pct:+.1f}%",
                "Flag":          "⚠️" if abs(pct) > 5 else "✓",
            })
        tbl = dbc.Table.from_dataframe(
            pd.DataFrame(rows), striped=True, hover=True,
            bordered=False, size="sm", className="mb-0",
            style={"fontSize": "0.8rem"},
        )
        table_section = html.Div([
            html.Div("Quarter-by-Quarter Variance", style={"fontWeight": "600", "marginBottom": "0.6rem", "fontSize": "0.9rem"}),
            tbl,
        ])
    else:
        table_section = html.Div("Forecast not available.")

    return flag_section, fig, table_section
