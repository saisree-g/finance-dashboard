"""
pages/forecast.py — Forecast page.
"""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html
import pandas as pd

from charts import forecast_chart, mape_bar
from config import COLORS
from edgar import load_financials
from models import run_all_forecasts
from narrative import generate_commentary

dash.register_page(__name__, path="/forecast", name="Forecast", title="Forecast — TMO FP&A")


layout = html.Div([
    html.Div([
        html.H1("Revenue Forecast", className="page-title"),
        html.P("ARIMA · ETS · Prophet · XGBoost · Ensemble — 4-quarter forward view", className="page-subtitle"),
    ], className="page-header"),

    # Metric selector
    dbc.Row([
        dbc.Col(html.Div([
            html.Label("Metric", style={"fontSize": "0.75rem", "fontWeight": "600", "color": COLORS["text_mid"], "marginBottom": "4px"}),
            dcc.Dropdown(
                id="forecast-metric",
                options=[
                    {"label": "Revenue",          "value": "revenue"},
                    {"label": "Gross Profit",     "value": "gross_profit"},
                    {"label": "Operating Income", "value": "operating_income"},
                    {"label": "Net Income",       "value": "net_income"},
                ],
                value="revenue",
                clearable=False,
                style={"fontSize": "0.82rem"},
            ),
        ]), md=3),
    ], className="mb-3"),

    # GenAI narrative
    html.Div(id="forecast-narrative", className="narrative-card"),

    dbc.Row([
        dbc.Col(html.Div(dcc.Graph(id="forecast-main-chart", config={"displayModeBar": False}), className="chart-card"), md=8),
        dbc.Col(html.Div(dcc.Graph(id="mape-chart",          config={"displayModeBar": False}), className="chart-card"), md=4),
    ], className="g-3 mb-3"),

    # Forecast table
    html.Div(id="forecast-table", className="chart-card"),
])


@callback(
    Output("forecast-narrative",   "children"),
    Output("forecast-main-chart",  "figure"),
    Output("mape-chart",           "figure"),
    Output("forecast-table",       "children"),
    Input("forecast-metric",       "value"),
)
def update_forecast(metric):
    df        = load_financials()
    series    = df[metric].dropna()
    forecasts = run_all_forecasts(series)

    # Narrative
    commentary = generate_commentary(df, forecasts, metric)
    narrative  = [
        html.Div("AI Commentary", className="narrative-label"),
        html.Div(commentary),
    ]

    # Forecast table
    rows = []
    for model, res in forecasts.items():
        for i, (date, val) in enumerate(zip(res["dates"], res["forecast"])):
            rows.append({
                "Model":   model,
                "Quarter": date.to_period("Q").strftime("Q%q %Y"),
                "Forecast ($M)": f"${val:,.0f}",
                "MAPE (%)": f"{res['mape']:.1f}%",
            })

    tbl = dbc.Table.from_dataframe(
        pd.DataFrame(rows),
        striped=True, hover=True, bordered=False, size="sm",
        className="mb-0",
        style={"fontSize": "0.8rem"},
    )
    table_section = html.Div([
        html.Div("Forecast Table", style={"fontWeight": "600", "marginBottom": "0.6rem", "fontSize": "0.9rem"}),
        tbl,
    ])

    return narrative, forecast_chart(df, forecasts, metric), mape_bar(forecasts), table_section
