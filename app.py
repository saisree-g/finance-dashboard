"""
app.py — Entry point for the Revenue & Expense Forecasting Dashboard.

Run with:
    python app.py

Module responsibilities:
    app.py       → Dash server, sidebar layout, page routing
    config.py    → constants (company, colors, model params)
    edgar.py     → SEC EDGAR API fetching + Parquet cache
    models.py    → ARIMA, ETS, Prophet, XGBoost, Ensemble
    charts.py    → reusable Plotly figure builders
    narrative.py → Claude API variance commentary
    pages/       → one file per dashboard tab
"""

import dash
import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, dcc, html
from pathlib import Path

from config import COMPANY_NAME, TICKER
from cache import cache

# ─────────────────────────────────────────────────────────────────────────────
# APP INIT
# ─────────────────────────────────────────────────────────────────────────────
app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server   # for Gunicorn / Render deployment

# ─────────────────────────────────────────────────────────────────────────────
# CACHE INIT  (filesystem — safe for multi-worker Gunicorn on Render)
# ─────────────────────────────────────────────────────────────────────────────
cache.init_app(server, config={
    "CACHE_TYPE":            "FileSystemCache",
    "CACHE_DIR":             str(Path(__file__).parent / ".flask_cache"),
    "CACHE_DEFAULT_TIMEOUT": 3600,   # 1 hour — financial data is quarterly
})


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

_nav_items = [
    ("/",          "bi-grid-1x2",    "Overview"),
    ("/forecast",  "bi-graph-up",    "Forecast"),
    ("/variance",  "bi-bar-chart",   "Variance"),
    ("/scenarios", "bi-sliders",     "Scenarios"),
    ("/data",      "bi-database",    "Data"),
]

def _nav_link(href, icon, label):
    return dcc.Link(
        html.Div([
            html.I(className=f"bi {icon} me-2"),
            html.Span(label),
        ], className="sidebar-link"),
        href=href,
        id=f"nav-{label.lower()}",
        className="sidebar-link-wrapper",
    )

sidebar = html.Div([
    # Logo / wordmark
    html.Div([
        html.Div(TICKER, className="sidebar-ticker"),
        html.Div("FP&A Intelligence", className="sidebar-tagline"),
    ], className="sidebar-brand"),

    html.Hr(style={"borderColor": "rgba(255,255,255,0.12)", "margin": "0.8rem 0"}),

    # Navigation
    html.Nav([_nav_link(h, ic, lb) for h, ic, lb in _nav_items], className="sidebar-nav"),

    html.Hr(style={"borderColor": "rgba(255,255,255,0.12)", "margin": "0.8rem 0"}),

    # Refresh button
    html.Div([
        html.Button(
            [html.I(className="bi bi-arrow-clockwise me-2"), "Refresh Data"],
            id="refresh-btn",
            className="sidebar-refresh-btn",
            n_clicks=0,
        ),
        html.Div(id="refresh-status", style={"fontSize": "0.7rem", "color": "rgba(255,255,255,0.5)", "marginTop": "0.4rem"}),
    ]),

    # Footer meta
    html.Div([
        html.Div("Data source", style={"color": "rgba(255,255,255,0.4)", "fontSize": "0.6rem", "textTransform": "uppercase", "letterSpacing": "0.08em"}),
        html.Div("SEC EDGAR · 10-Q / 10-K", style={"color": "rgba(255,255,255,0.6)", "fontSize": "0.7rem"}),
        html.Div(COMPANY_NAME, style={"color": "rgba(255,255,255,0.4)", "fontSize": "0.65rem", "marginTop": "0.5rem"}),
    ], className="sidebar-footer"),
], className="sidebar")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="financials-store"),   # serialised DataFrame JSON
    dcc.Store(id="forecasts-store"),    # serialised forecasts

    # Sidebar + page content
    sidebar,
    html.Div(dash.page_container, className="main-content"),
], id="root")


# ─────────────────────────────────────────────────────────────────────────────
# REFRESH CALLBACK
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("refresh-status", "children"),
    Input("refresh-btn", "n_clicks"),
    prevent_initial_call=True,
)
def refresh_data(n):
    if n:
        from edgar import refresh
        refresh()
        return "✓ Data refreshed"
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=False, port=8050)
