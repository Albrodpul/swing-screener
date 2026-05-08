"""Trend Template (Stage 2) — Weinstein + Minervini.

Devuelve booleanos por fila y el conjunto agregado.
"""
from __future__ import annotations
import pandas as pd

from .indicators import sma, slope


def compute_trend_template(prices: pd.DataFrame) -> pd.DataFrame:
    """prices: DataFrame con columnas open/high/low/close/volume indexado por fecha.

    Devuelve DataFrame con columnas booleanas + métricas auxiliares.
    """
    out = pd.DataFrame(index=prices.index)
    close = prices["close"]
    out["sma50"] = sma(close, 50)
    out["sma150"] = sma(close, 150)
    out["sma200"] = sma(close, 200)
    out["high_52w"] = close.rolling(252, min_periods=200).max()
    out["low_52w"] = close.rolling(252, min_periods=200).min()
    out["sma200_slope"] = slope(out["sma200"], 20)
    out["sma50_slope"] = slope(out["sma50"], 10)

    out["price_above_150_200"] = (close > out["sma150"]) & (close > out["sma200"])
    out["mas_aligned"] = (out["sma50"] > out["sma150"]) & (out["sma150"] > out["sma200"])
    out["sma200_uptrend"] = out["sma200_slope"] > 0
    out["sma50_uptrend"] = out["sma50_slope"] > 0
    out["above_30pct_low"] = close >= 1.30 * out["low_52w"]
    out["near_52w_high"] = close >= 0.75 * out["high_52w"]

    out["trend_template"] = (
        out["price_above_150_200"]
        & out["mas_aligned"]
        & out["sma200_uptrend"]
        & out["sma50_uptrend"]
        & out["above_30pct_low"]
        & out["near_52w_high"]
    )

    # Filtro no-extendido (criterio Minervini)
    out["pct_above_sma50"] = (close - out["sma50"]) / out["sma50"]
    out["not_extended"] = out["pct_above_sma50"] < 0.25
    out["close"] = close
    return out


def latest_trend_state(prices: pd.DataFrame) -> dict:
    if prices is None or len(prices) < 220:
        return {"trend_template": False, "not_extended": False, "reason": "insufficient_history"}
    tt = compute_trend_template(prices)
    last = tt.iloc[-1]
    return {
        "trend_template": bool(last["trend_template"]),
        "not_extended": bool(last["not_extended"]),
        "pct_above_sma50": float(last["pct_above_sma50"]) if last["pct_above_sma50"] == last["pct_above_sma50"] else None,
        "price_above_150_200": bool(last["price_above_150_200"]),
        "mas_aligned": bool(last["mas_aligned"]),
        "sma200_uptrend": bool(last["sma200_uptrend"]),
        "sma50_uptrend": bool(last["sma50_uptrend"]),
        "above_30pct_low": bool(last["above_30pct_low"]),
        "near_52w_high": bool(last["near_52w_high"]),
        "close": float(last["close"]),
        "sma50": float(last["sma50"]) if last["sma50"] == last["sma50"] else None,
        "sma200": float(last["sma200"]) if last["sma200"] == last["sma200"] else None,
        "high_52w": float(last["high_52w"]) if last["high_52w"] == last["high_52w"] else None,
        "low_52w": float(last["low_52w"]) if last["low_52w"] == last["low_52w"] else None,
    }
