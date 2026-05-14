"""
pages/data.py — Data catalogue: source, field definitions, quality, raw table.
"""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dash_table, dcc, html
import pandas as pd
from pathlib import Path

from config import (
    CIK, COMPANY_NAME, EDGAR_BASE, TICKER,
    REVENUE_KEYS, GROSS_PROFIT_KEYS,
    OPERATING_INCOME_KEYS, NET_INCOME_KEYS,
    RD_KEYS, SGA_KEYS,
)
from edgar import load_financials, _CACHE

dash.register_page(__name__, path="/data", name="Data", title="Data — TMO FP&A")


# ─────────────────────────────────────────────────────────────────────────────
# STATIC CONTENT — field dictionary and XBRL key map (never changes at runtime)
# ─────────────────────────────────────────────────────────────────────────────

_FIELD_DEFS = [
    {"Field": "revenue",          "Label": "Revenue ($M)",          "Type": "Raw",     "Description": "Total net revenue from contracts with customers. Primary top-line metric."},
    {"Field": "gross_profit",     "Label": "Gross Profit ($M)",     "Type": "Raw",     "Description": "Revenue minus cost of goods sold. Measures production/service efficiency."},
    {"Field": "operating_income", "Label": "Operating Income ($M)", "Type": "Raw",     "Description": "Gross profit minus R&D and SG&A. Earnings from core operations before interest and tax."},
    {"Field": "net_income",       "Label": "Net Income ($M)",       "Type": "Raw",     "Description": "Bottom-line profit after all expenses, interest, and taxes."},
    {"Field": "rd_expense",       "Label": "R&D Expense ($M)",      "Type": "Raw",     "Description": "Research & Development spend. Key investment signal for life-science companies."},
    {"Field": "sga_expense",      "Label": "SG&A Expense ($M)",     "Type": "Raw",     "Description": "Selling, General & Administrative costs. Proxy for operational leverage."},
    {"Field": "gross_margin",     "Label": "Gross Margin (%)",      "Type": "Derived", "Description": "gross_profit / revenue × 100. Measures pricing power and COGS management."},
    {"Field": "operating_margin", "Label": "Operating Margin (%)",  "Type": "Derived", "Description": "operating_income / revenue × 100. Core profitability after all operating costs."},
    {"Field": "net_margin",       "Label": "Net Margin (%)",        "Type": "Derived", "Description": "net_income / revenue × 100. Overall profit efficiency after all deductions."},
    {"Field": "revenue_yoy",      "Label": "Revenue YoY (%)",       "Type": "Derived", "Description": "Quarter-over-same-quarter-prior-year growth. 4-period % change removes seasonality."},
    {"Field": "quarter_label",    "Label": "Quarter Label",         "Type": "Display", "Description": "Human-readable period label, e.g. Q3 2023. Derived from the period-end date index."},
]

_XBRL_MAP = [
    {"Metric": "Revenue",          "XBRL Keys Tried (in order)": " → ".join(REVENUE_KEYS)},
    {"Metric": "Gross Profit",     "XBRL Keys Tried (in order)": " → ".join(GROSS_PROFIT_KEYS)},
    {"Metric": "Operating Income", "XBRL Keys Tried (in order)": " → ".join(OPERATING_INCOME_KEYS)},
    {"Metric": "Net Income",       "XBRL Keys Tried (in order)": " → ".join(NET_INCOME_KEYS)},
    {"Metric": "R&D Expense",      "XBRL Keys Tried (in order)": " → ".join(RD_KEYS)},
    {"Metric": "SG&A Expense",     "XBRL Keys Tried (in order)": " → ".join(SGA_KEYS)},
]

_SOURCE_URL = f"{EDGAR_BASE}/CIK{CIK}.json"


def _info_card(title: str, value: str, sub: str = "", color: str = "#2563eb"):
    return html.Div([
        html.Div(title, className="kpi-label"),
        html.Div(value, style={"fontSize": "1.4rem", "fontWeight": "700", "color": "#1e293b", "margin": "4px 0"}),
        html.Div(sub,   style={"fontSize": "0.72rem", "color": "#64748b"}),
    ], className="kpi-card", style={"borderTopColor": color})


def _section_header(title: str, description: str):
    return html.Div([
        html.H2(title, style={"fontSize": "1rem", "fontWeight": "700", "color": "#1e293b", "margin": "0 0 4px"}),
        html.P(description, style={"fontSize": "0.82rem", "color": "#475569", "margin": 0}),
    ], style={"marginBottom": "1rem"})


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

layout = html.Div([
    html.Div([
        html.H1("Data Catalogue", className="page-title"),
        html.P(
            "Source provenance, field definitions, XBRL key mapping, quality diagnostics, and raw data — "
            "everything needed to understand what feeds the models.",
            className="page-subtitle",
        ),
    ], className="page-header"),

    dcc.Loading(
        html.Div([

            # ── Summary KPI row ───────────────────────────────────────────────
            html.Div(id="data-summary-kpis", className="mb-4"),

            # ── 1. Data Source ────────────────────────────────────────────────
            html.Div([
                _section_header(
                    "1. Data Source",
                    "All financial data is fetched from the SEC EDGAR XBRL API — a free, authoritative source "
                    "with no API key required. Data covers 10-Q and 10-K filings only.",
                ),
                dbc.Row([
                    dbc.Col(html.Div([
                        html.Div("Company", style={"fontSize": "0.7rem", "fontWeight": "600", "color": "#475569", "textTransform": "uppercase", "marginBottom": "2px"}),
                        html.Div(COMPANY_NAME, style={"fontWeight": "600", "color": "#1e293b"}),
                        html.Div(f"Ticker: {TICKER}  ·  CIK: {CIK}", style={"fontSize": "0.78rem", "color": "#64748b", "marginTop": "2px"}),
                    ], className="chart-card"), md=4),
                    dbc.Col(html.Div([
                        html.Div("API Endpoint", style={"fontSize": "0.7rem", "fontWeight": "600", "color": "#475569", "textTransform": "uppercase", "marginBottom": "2px"}),
                        html.Code(_SOURCE_URL, style={"fontSize": "0.72rem", "wordBreak": "break-all", "color": "#2563eb"}),
                        html.Div("No authentication required · Rate limit: 10 req/s", style={"fontSize": "0.72rem", "color": "#64748b", "marginTop": "4px"}),
                    ], className="chart-card"), md=5),
                    dbc.Col(html.Div([
                        html.Div("Filing Types Used", style={"fontSize": "0.7rem", "fontWeight": "600", "color": "#475569", "textTransform": "uppercase", "marginBottom": "2px"}),
                        html.Div("10-Q  (quarterly)", style={"fontWeight": "600", "color": "#1e293b"}),
                        html.Div("10-K  (annual — Q4 proxy)", style={"fontWeight": "600", "color": "#1e293b", "marginTop": "2px"}),
                        html.Div("FY / Q1–Q4 fiscal periods only", style={"fontSize": "0.72rem", "color": "#64748b", "marginTop": "4px"}),
                    ], className="chart-card"), md=3),
                ], className="g-3"),
            ], className="mb-4"),

            # ── 2. XBRL Key Mapping ───────────────────────────────────────────
            html.Div([
                _section_header(
                    "2. XBRL Key Mapping",
                    "EDGAR reports values under US-GAAP taxonomy keys. Companies may use different keys for "
                    "the same concept. The pipeline tries each key in order and uses the first match.",
                ),
                html.Div(
                    dbc.Table.from_dataframe(
                        pd.DataFrame(_XBRL_MAP),
                        striped=True, hover=False, bordered=False, size="sm",
                        className="mb-0",
                        style={"fontSize": "0.8rem"},
                    ),
                    className="chart-card",
                ),
            ], className="mb-4"),

            # ── 3. Field Dictionary ───────────────────────────────────────────
            html.Div([
                _section_header(
                    "3. Field Dictionary",
                    "Every column in the working DataFrame — its label, whether it comes directly from EDGAR "
                    "(Raw) or is computed (Derived), and what it measures.",
                ),
                html.Div(
                    dbc.Table.from_dataframe(
                        pd.DataFrame(_FIELD_DEFS),
                        striped=True, hover=False, bordered=False, size="sm",
                        className="mb-0",
                        style={"fontSize": "0.8rem"},
                    ),
                    className="chart-card",
                ),
            ], className="mb-4"),

            # ── 4. Data Quality ───────────────────────────────────────────────
            html.Div(id="data-quality-section", className="mb-4"),

            # ── 5. Raw Data Table ─────────────────────────────────────────────
            html.Div([
                _section_header(
                    "5. Raw Data",
                    "The full working DataFrame as loaded from cache. Sorted newest-first. "
                    "All monetary values in USD millions.",
                ),
                html.Div(id="data-raw-table", className="chart-card"),
            ]),

        ]),
        type="circle",
        color="#2563eb",
        style={"minHeight": "200px"},
    ),
])


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK
# ─────────────────────────────────────────────────────────────────────────────

@callback(
    Output("data-summary-kpis",     "children"),
    Output("data-quality-section",  "children"),
    Output("data-raw-table",        "children"),
    Input("url", "pathname"),
)
def update_data(_):
    df = load_financials()

    # ── Summary KPIs ──────────────────────────────────────────────────────────
    n_quarters  = len(df)
    date_start  = df.index.min().strftime("%b %Y")
    date_end    = df.index.max().strftime("%b %Y")
    last_cached = (
        pd.Timestamp(_CACHE.stat().st_mtime, unit="s").strftime("%d %b %Y %H:%M")
        if _CACHE.exists() else "—"
    )
    n_missing   = int(df[["revenue","gross_profit","operating_income","net_income","rd_expense","sga_expense"]].isna().sum().sum())

    summary_kpis = dbc.Row([
        dbc.Col(_info_card("Quarters in Dataset",  str(n_quarters),       f"{date_start} → {date_end}",   "#2563eb"), md=3),
        dbc.Col(_info_card("Fields per Quarter",   str(len(df.columns)),  "6 raw · 4 derived · 1 label",  "#7c3aed"), md=3),
        dbc.Col(_info_card("Missing Raw Values",   str(n_missing),        "across all 6 EDGAR metrics",   "#10b981" if n_missing == 0 else "#f59e0b"), md=3),
        dbc.Col(_info_card("Cache Last Updated",   last_cached,           "Parquet · data/financials.parquet", "#64748b"), md=3),
    ], className="g-3")

    # ── Data Quality table ────────────────────────────────────────────────────
    raw_cols = ["revenue","gross_profit","operating_income","net_income","rd_expense","sga_expense"]
    quality_rows = []
    for col in raw_cols:
        s = df[col]
        nulls = int(s.isna().sum())
        quality_rows.append({
            "Field":          col,
            "Non-null":       int(s.notna().sum()),
            "Null":           nulls,
            "Coverage":       f"{s.notna().mean()*100:.1f}%",
            "Min ($M)":       f"{s.min():,.0f}" if s.notna().any() else "—",
            "Max ($M)":       f"{s.max():,.0f}" if s.notna().any() else "—",
            "Mean ($M)":      f"{s.mean():,.0f}" if s.notna().any() else "—",
            "Latest ($M)":    f"{s.dropna().iloc[-1]:,.0f}" if s.notna().any() else "—",
        })

    quality_section = html.Div([
        _section_header(
            "4. Data Quality & Coverage",
            "Per-field completeness and summary statistics across all quarters in the dataset.",
        ),
        html.Div(
            dbc.Table.from_dataframe(
                pd.DataFrame(quality_rows),
                striped=True, hover=False, bordered=False, size="sm",
                className="mb-0",
                style={"fontSize": "0.8rem"},
            ),
            className="chart-card",
        ),
    ])

    # ── Raw data table ────────────────────────────────────────────────────────
    display_df = df.copy().sort_index(ascending=False).reset_index()
    display_df.rename(columns={"date": "Period End"}, inplace=True)
    display_df["Period End"] = display_df["Period End"].dt.strftime("%Y-%m-%d")

    fmt_m = lambda x: f"${x:,.0f}" if pd.notna(x) else "—"
    fmt_p = lambda x: f"{x:.1f}%"  if pd.notna(x) else "—"

    for col in ["revenue","gross_profit","operating_income","net_income","rd_expense","sga_expense"]:
        display_df[col] = display_df[col].map(fmt_m)
    for col in ["gross_margin","operating_margin","net_margin","revenue_yoy"]:
        display_df[col] = display_df[col].map(fmt_p)

    display_df.columns = [c.replace("_", " ").title() for c in display_df.columns]

    raw_table = dash_table.DataTable(
        data=display_df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in display_df.columns],
        page_size=16,
        style_table={"overflowX": "auto"},
        style_header={
            "backgroundColor": "#f8fafc",
            "fontWeight": "600",
            "fontSize": "0.72rem",
            "color": "#475569",
            "textTransform": "uppercase",
            "letterSpacing": "0.04em",
            "border": "none",
            "borderBottom": "2px solid #e2e8f0",
        },
        style_cell={
            "fontSize": "0.8rem",
            "padding": "8px 10px",
            "border": "none",
            "borderBottom": "1px solid #f1f5f9",
            "fontFamily": "Inter, system-ui, sans-serif",
            "color": "#1e293b",
            "whiteSpace": "nowrap",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f8fafc"},
        ],
    )

    return summary_kpis, quality_section, raw_table
