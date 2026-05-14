"""
models.py — Forecasting models for quarterly financial time series.

run_all_forecasts(series, horizon) → dict of model results
Each result contains: forecast array, optional CI, in-sample MAPE
"""

from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_percentage_error

from config import FORECAST_HORIZON, VALIDATION_WINDOW


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _future_dates(series: pd.Series, horizon: int) -> pd.DatetimeIndex:
    return pd.date_range(
        start=series.index[-1] + pd.offsets.QuarterEnd(),
        periods=horizon,
        freq="QE",
    )


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    mask = actual != 0
    return float(mean_absolute_percentage_error(actual[mask], predicted[mask]) * 100)


def _lag_features(series: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"y": series.values}, index=series.index)
    for lag in [1, 2, 4, 8]:
        df[f"lag_{lag}"] = series.shift(lag).values
    df["quarter"] = series.index.quarter
    df["trend"]   = np.arange(len(series))
    return df.dropna()


# ─────────────────────────────────────────────────────────────────────────────
# ARIMA
# ─────────────────────────────────────────────────────────────────────────────

def _forecast_arima(series: pd.Series, horizon: int) -> tuple[np.ndarray, None, None]:
    from statsmodels.tsa.arima.model import ARIMA
    result = ARIMA(series, order=(2, 1, 1), seasonal_order=(1, 1, 0, 4)).fit()
    return result.forecast(steps=horizon).values, None, None


# ─────────────────────────────────────────────────────────────────────────────
# ETS (Exponential Smoothing)
# ─────────────────────────────────────────────────────────────────────────────

def _forecast_ets(series: pd.Series, horizon: int) -> tuple[np.ndarray, None, None]:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    model  = ExponentialSmoothing(series, trend="add", seasonal="add", seasonal_periods=4)
    result = model.fit(optimized=True)
    return result.forecast(horizon).values, None, None


# ─────────────────────────────────────────────────────────────────────────────
# PROPHET
# ─────────────────────────────────────────────────────────────────────────────

def _forecast_prophet(series: pd.Series, horizon: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    from prophet import Prophet
    df = pd.DataFrame({"ds": series.index, "y": series.values})
    m  = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_mode="multiplicative",
    )
    m.fit(df)
    future   = m.make_future_dataframe(periods=horizon, freq="QE")
    forecast = m.predict(future).tail(horizon)
    return (
        forecast["yhat"].values,
        forecast["yhat_lower"].values,
        forecast["yhat_upper"].values,
    )


# ─────────────────────────────────────────────────────────────────────────────
# XGBOOST
# ─────────────────────────────────────────────────────────────────────────────

def _forecast_xgboost(series: pd.Series, horizon: int) -> tuple[np.ndarray, None, None]:
    import xgboost as xgb

    feat_df = _lag_features(series)
    X, y    = feat_df.drop("y", axis=1), feat_df["y"]

    model = xgb.XGBRegressor(
        n_estimators=300, max_depth=3,
        learning_rate=0.05, subsample=0.8,
        random_state=42, verbosity=0,
    )
    model.fit(X, y)

    # Recursive multi-step forecast
    history = series.values.tolist()
    preds   = []
    for i in range(horizon):
        row = {
            "lag_1": history[-1],
            "lag_2": history[-2],
            "lag_4": history[-4],
            "lag_8": history[-8] if len(history) >= 8 else history[0],
            "quarter": ((series.index[-1].quarter - 1 + i) % 4) + 1,
            "trend":   len(series) + i,
        }
        pred = float(model.predict(pd.DataFrame([row]))[0])
        preds.append(pred)
        history.append(pred)

    return np.array(preds), None, None


# ─────────────────────────────────────────────────────────────────────────────
# ENSEMBLE
# ─────────────────────────────────────────────────────────────────────────────

def _ensemble(results: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    available = [v["forecast"] for k, v in results.items() if k != "Ensemble"]
    combined  = np.mean(available, axis=0)
    # Simple CI: ±1 std across model forecasts
    std  = np.std(available, axis=0)
    return combined, combined - 1.96 * std, combined + 1.96 * std


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def run_all_forecasts(
    series: pd.Series,
    horizon: int = FORECAST_HORIZON,
) -> dict[str, dict]:
    """
    Train all models, compute validation MAPE, and return horizon-step forecasts.

    Returns dict keyed by model name:
        forecast : np.ndarray (length = horizon)
        lower    : np.ndarray | None
        upper    : np.ndarray | None
        mape     : float (in-sample validation MAPE, %)
        dates    : pd.DatetimeIndex
    """
    train  = series.iloc[:-VALIDATION_WINDOW]
    val    = series.iloc[-VALIDATION_WINDOW:]
    dates  = _future_dates(series, horizon)
    results: dict[str, dict] = {}

    _models = {
        "ARIMA":   _forecast_arima,
        "ETS":     _forecast_ets,
        "Prophet": _forecast_prophet,
        "XGBoost": _forecast_xgboost,
    }

    for name, fn in _models.items():
        try:
            val_fc, _, _ = fn(train, VALIDATION_WINDOW)
            fc, lo, hi   = fn(series, horizon)
            results[name] = {
                "forecast": fc,
                "lower":    lo,
                "upper":    hi,
                "mape":     _mape(val.values, val_fc),
                "dates":    dates,
            }
        except Exception as exc:
            print(f"[models] {name} failed: {exc}")

    # Ensemble
    if len(results) >= 2:
        fc, lo, hi = _ensemble(results)
        avg_mape   = float(np.mean([v["mape"] for v in results.values()]))
        results["Ensemble"] = {
            "forecast": fc,
            "lower":    lo,
            "upper":    hi,
            "mape":     avg_mape,
            "dates":    dates,
        }

    return results
