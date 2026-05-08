"""Detección de breakout estilo VCP (Volatility Contraction Pattern) simplificada.

Pivot = máximo de últimas 25 sesiones excluyendo las 5 más recientes.
Contracción = ATR14 reciente < 0.6 * ATR14 hace 50 sesiones.
Breakout = cierre > pivot * 1.001 + volumen >= 1.4 * SMA50(volumen).
"""
from __future__ import annotations
import pandas as pd
import numpy as np

from .indicators import atr, sma


def detect_breakout(prices: pd.DataFrame,
                    pivot_lookback: int = 25,
                    pivot_buffer: int = 5,
                    contraction_window: int = 50,
                    contraction_ratio: float = 0.6,
                    volume_mult: float = 1.4) -> dict:
    if prices is None or len(prices) < 80:
        return {"breakout": False, "volume_ok": False, "contraction_ok": False, "reason": "insufficient_history"}
    high = prices["high"]
    close = prices["close"]
    volume = prices["volume"]

    # pivot: máx de últimas N sesiones excluyendo las B más recientes
    if len(high) < pivot_lookback + pivot_buffer + 1:
        return {"breakout": False, "volume_ok": False, "contraction_ok": False, "reason": "insufficient_history"}
    pivot_window = high.iloc[-(pivot_lookback + pivot_buffer):-pivot_buffer]
    pivot = float(pivot_window.max())

    last_close = float(close.iloc[-1])
    last_volume = float(volume.iloc[-1])
    vol_avg = float(sma(volume, 50).iloc[-1])

    a = atr(prices, 14)
    if len(a.dropna()) < contraction_window + 1:
        contraction_ok = False
    else:
        contraction_ok = bool(a.iloc[-1] < contraction_ratio * a.iloc[-(contraction_window + 1)])

    breakout = bool(last_close > pivot * 1.001)
    volume_ok = bool(last_volume >= volume_mult * vol_avg) if vol_avg == vol_avg else False

    return {
        "breakout": breakout,
        "volume_ok": volume_ok,
        "contraction_ok": contraction_ok,
        "pivot": pivot,
        "last_close": last_close,
        "volume_ratio": last_volume / vol_avg if vol_avg else None,
    }
