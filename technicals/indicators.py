"""Indicadores técnicos básicos en numpy/pandas puro.

Evitamos pandas-ta como dependencia dura: implementaciones aquí cubren todo lo
que necesitamos. Si pandas-ta está disponible se puede usar como sanity check.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    close_prev = df["close"].shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - close_prev).abs(),
        (low - close_prev).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def slope(s: pd.Series, n: int) -> pd.Series:
    """Pendiente de regresión lineal sobre últimas n observaciones."""
    def _calc(window: np.ndarray) -> float:
        if np.isnan(window).any():
            return np.nan
        x = np.arange(len(window))
        # pendiente normalizada por el valor medio para que sea comparable
        m, _ = np.polyfit(x, window, 1)
        mean = np.mean(window)
        return m / mean if mean else np.nan
    return s.rolling(n, min_periods=n).apply(_calc, raw=True)


def rolling_max(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).max()


def rolling_min(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).min()


def percentile_rank(s: pd.Series) -> pd.Series:
    """Percentil del último valor de cada fila contra todo el cross-section."""
    return s.rank(pct=True) * 100
