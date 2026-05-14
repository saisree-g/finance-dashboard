"""
narrative.py — GenAI variance commentary via Claude API.

generate_commentary(df, forecasts, metric) → str
"""

import os
import pandas as pd


def generate_commentary(
    df: pd.DataFrame,
    forecasts: dict,
    metric: str = "revenue",
) -> str:
    """
    Generate a concise FP&A variance narrative for the most recent quarter.
    Falls back to a rule-based summary if the API key is not set.
    """
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

        actual       = df[metric].iloc[-1]
        quarter_lbl  = df["quarter_label"].iloc[-1]
        ensemble_fc  = forecasts.get("Ensemble", {}).get("forecast")
        forecast_val = float(ensemble_fc[0]) if ensemble_fc is not None else None
        yoy          = df["revenue_yoy"].iloc[-1] if "revenue_yoy" in df.columns else None

        # Context block
        lines = [
            f"Quarter: {quarter_lbl}",
            f"Actual {metric}: ${actual:,.0f}M",
        ]
        if forecast_val:
            var    = actual - forecast_val
            var_pct = var / forecast_val * 100
            lines += [
                f"Ensemble forecast: ${forecast_val:,.0f}M",
                f"Variance: ${var:+,.0f}M ({var_pct:+.1f}%)",
            ]
        if yoy is not None and not pd.isna(yoy):
            lines.append(f"Year-over-year growth: {yoy:+.1f}%")

        margin = df["gross_margin"].iloc[-1] if "gross_margin" in df.columns else None
        if margin is not None and not pd.isna(margin):
            lines.append(f"Gross margin: {margin:.1f}%")

        context = "\n".join(lines)

        prompt = f"""You are a senior FP&A analyst writing variance commentary for an executive P&L report.

{context}

Company: Thermo Fisher Scientific (TMO) — global life sciences & laboratory equipment leader.

Write 2–3 sentences of concise, professional variance commentary. Be specific and quantitative.
Reference plausible business drivers (e.g. Life Sciences instruments, diagnostics, pharma services).
Do not mention being an AI. Do not start with "I"."""

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=220,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

    except Exception:
        # Rule-based fallback when API key is absent
        return _rule_based_commentary(df, forecasts, metric)


def _rule_based_commentary(df: pd.DataFrame, forecasts: dict, metric: str) -> str:
    actual      = df[metric].iloc[-1]
    quarter_lbl = df["quarter_label"].iloc[-1]
    yoy         = df["revenue_yoy"].iloc[-1] if "revenue_yoy" in df.columns else None
    ensemble_fc = forecasts.get("Ensemble", {}).get("forecast")

    parts = [f"{quarter_lbl} {metric} of ${actual:,.0f}M"]

    if ensemble_fc is not None:
        fc  = float(ensemble_fc[0])
        var = actual - fc
        pct = var / fc * 100
        direction = "exceeded" if var >= 0 else "missed"
        parts.append(f"{direction} the ensemble forecast by {abs(pct):.1f}% (${abs(var):,.0f}M)")

    if yoy is not None and not pd.isna(yoy):
        trend = "grew" if yoy >= 0 else "declined"
        parts.append(f"representing {abs(yoy):.1f}% year-over-year {'growth' if yoy >= 0 else 'decline'}")

    return ". ".join(parts) + "."
