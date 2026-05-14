"""
config.py — All constants for the Finance Dashboard.
"""

# ── COMPANY ───────────────────────────────────────────────────────────────────
COMPANY_NAME = "Thermo Fisher Scientific Inc."
TICKER       = "TMO"
CIK          = "0000097476"

# ── SEC EDGAR ─────────────────────────────────────────────────────────────────
EDGAR_BASE    = "https://data.sec.gov/api/xbrl/companyfacts"
EDGAR_HEADERS = {"User-Agent": "finance-dashboard research@example.com"}

# XBRL metric keys — tried in order, first match wins
REVENUE_KEYS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
]
GROSS_PROFIT_KEYS = ["GrossProfit"]
OPERATING_INCOME_KEYS = ["OperatingIncomeLoss"]
NET_INCOME_KEYS = ["NetIncomeLoss"]
RD_KEYS = ["ResearchAndDevelopmentExpense"]
SGA_KEYS = ["SellingGeneralAndAdministrativeExpense"]

# ── FORECAST ──────────────────────────────────────────────────────────────────
FORECAST_HORIZON = 4   # quarters forward
VALIDATION_WINDOW = 4  # quarters held out for MAPE calculation

SCENARIO_ADJUSTMENTS = {
    "Optimistic":  0.08,   # +8 % on ensemble forecast
    "Base":        0.00,
    "Pessimistic": -0.08,  # -8 %
}

# ── STYLE ─────────────────────────────────────────────────────────────────────
COLORS = {
    "primary":   "#1e3a5f",   # sidebar / header navy
    "accent":    "#2563eb",   # interactive blue
    "positive":  "#10b981",   # green  (favourable variance)
    "negative":  "#ef4444",   # red    (unfavourable variance)
    "neutral":   "#6b7280",   # grey
    "bg":        "#f1f5f9",   # page background
    "surface":   "#ffffff",   # card background
    "border":    "#e2e8f0",
    "text":      "#1e293b",
    "text_mid":  "#475569",
    "forecast":  "#7c3aed",   # purple for forecast line
}

MODEL_COLORS = {
    "Actual":   "#1e3a5f",
    "ARIMA":    "#f59e0b",
    "ETS":      "#06b6d4",
    "Prophet":  "#10b981",
    "XGBoost":  "#f97316",
    "Ensemble": "#7c3aed",
}
