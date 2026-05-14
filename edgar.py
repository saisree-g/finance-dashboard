"""
edgar.py — Fetch and cache Thermo Fisher financials from SEC EDGAR API.

load_financials()  → pd.DataFrame  (quarterly P&L, indexed by period-end date)
refresh()          → force re-fetch from EDGAR
"""

from pathlib import Path

import pandas as pd
import requests

from cache import cache
from config import (
    CIK, EDGAR_BASE, EDGAR_HEADERS,
    REVENUE_KEYS, GROSS_PROFIT_KEYS,
    OPERATING_INCOME_KEYS, NET_INCOME_KEYS,
    RD_KEYS, SGA_KEYS,
)

_DATA_DIR  = Path(__file__).parent / "data"
_CACHE     = _DATA_DIR / "financials.parquet"
_DATA_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# RAW FETCH
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_facts() -> dict:
    url  = f"{EDGAR_BASE}/CIK{CIK}.json"
    resp = requests.get(url, headers=EDGAR_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACTION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _extract_series(us_gaap: dict, keys: list[str]) -> pd.Series | None:
    """
    Try each key in order. Return a quarterly pd.Series (USD millions)
    indexed by period-end date, deduplicated to latest filing per period.
    """
    for key in keys:
        if key not in us_gaap:
            continue
        entries = us_gaap[key].get("units", {}).get("USD", [])
        if not entries:
            continue

        df = pd.DataFrame(entries)
        # Keep only 10-Q / 10-K filings with quarterly fiscal period
        df = df[df["form"].isin(["10-Q", "10-K"])]
        df = df[df["fp"].isin(["Q1", "Q2", "Q3", "Q4", "FY"])]
        if df.empty:
            continue

        df["date"] = pd.to_datetime(df["end"])
        # Deduplicate: keep latest filing per period-end date
        df = df.sort_values("filed").groupby("date").last()
        series = df["val"].sort_index() / 1e6   # → USD millions
        return series

    return None


# ─────────────────────────────────────────────────────────────────────────────
# BUILD DataFrame
# ─────────────────────────────────────────────────────────────────────────────

def _build_df(facts: dict) -> pd.DataFrame:
    gaap = facts.get("facts", {}).get("us-gaap", {})

    revenue           = _extract_series(gaap, REVENUE_KEYS)
    gross_profit      = _extract_series(gaap, GROSS_PROFIT_KEYS)
    operating_income  = _extract_series(gaap, OPERATING_INCOME_KEYS)
    net_income        = _extract_series(gaap, NET_INCOME_KEYS)
    rd_expense        = _extract_series(gaap, RD_KEYS)
    sga_expense       = _extract_series(gaap, SGA_KEYS)

    df = pd.DataFrame({
        "revenue":          revenue,
        "gross_profit":     gross_profit,
        "operating_income": operating_income,
        "net_income":       net_income,
        "rd_expense":       rd_expense,
        "sga_expense":      sga_expense,
    }).dropna(subset=["revenue"]).sort_index()

    # Derived margin metrics (%)
    df["gross_margin"]     = df["gross_profit"]     / df["revenue"] * 100
    df["operating_margin"] = df["operating_income"] / df["revenue"] * 100
    df["net_margin"]       = df["net_income"]       / df["revenue"] * 100

    # YoY growth (4-quarter lag = same quarter prior year)
    df["revenue_yoy"] = df["revenue"].pct_change(4) * 100

    # Quarter label for display
    df["quarter_label"] = (
        df.index.to_period("Q").strftime("Q%q %Y")
    )

    # Keep only post-2012 where data is dense
    df = df[df.index >= "2012-01-01"]

    return df


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

@cache.memoize(timeout=3600)
def load_financials() -> pd.DataFrame:
    """Load from Parquet cache; fetch from EDGAR if parquet is absent."""
    if _CACHE.exists():
        return pd.read_parquet(_CACHE)

    facts = _fetch_facts()
    df    = _build_df(facts)
    df.to_parquet(_CACHE)
    return df


def refresh() -> pd.DataFrame:
    """Force re-fetch from EDGAR: clears parquet + entire Flask cache."""
    if _CACHE.exists():
        _CACHE.unlink()
    cache.clear()          # also invalidates all memoized forecast results
    return load_financials()
