"""Relative Strength rating tipo IBD, sin suscripción.

Fórmula:
    RS_raw = 0.40*ret_3m + 0.20*ret_6m + 0.20*ret_9m + 0.20*ret_12m
    RS_rating = percentile rank (0-100) de RS_raw en el universo.
RS_line = close / SPY_close. Bandera "RS_line at new high" si último cierre
de la línea está dentro del 99% del máximo de las últimas 50 sesiones.
"""
from __future__ import annotations
import pandas as pd
import numpy as np


def _ret(close: pd.Series, n: int) -> float:
    if len(close) <= n:
        return float("nan")
    return float(close.iloc[-1] / close.iloc[-1 - n] - 1.0)


def rs_raw(close: pd.Series) -> float:
    return (
        0.40 * _ret(close, 63)   # 3m
        + 0.20 * _ret(close, 126)  # 6m
        + 0.20 * _ret(close, 189)  # 9m
        + 0.20 * _ret(close, 252)  # 12m
    )


def compute_rs_universe(price_map: dict[str, pd.DataFrame]) -> dict[str, dict]:
    """Devuelve dict ticker -> {rs_raw, rs_rating}."""
    raws = {}
    for tk, df in price_map.items():
        if df is None or "close" not in df.columns or len(df) < 260:
            continue
        v = rs_raw(df["close"])
        if v == v:  # not nan
            raws[tk] = v
    if not raws:
        return {}
    s = pd.Series(raws)
    ranks = s.rank(pct=True) * 100
    return {tk: {"rs_raw": raws[tk], "rs_rating": float(ranks[tk])} for tk in raws}


def rs_line(close: pd.Series, bench_close: pd.Series) -> pd.Series:
    df = pd.concat([close, bench_close], axis=1, join="inner")
    df.columns = ["c", "b"]
    return df["c"] / df["b"]


def rs_line_state(close: pd.Series, bench_close: pd.Series, lookback: int = 50) -> dict:
    rl = rs_line(close, bench_close).dropna()
    if len(rl) < lookback:
        return {"rs_line_at_high": False, "rs_line_above_sma50": False}
    last = rl.iloc[-1]
    recent_max = rl.tail(lookback).max()
    sma50 = rl.tail(lookback).mean()
    return {
        "rs_line_at_high": bool(last >= recent_max * 0.99),
        "rs_line_above_sma50": bool(last > sma50),
        "rs_line_value": float(last),
    }
