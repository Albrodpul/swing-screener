"""Las 6 señales de salida (E1..E6).

Cada una devuelve dict con `active: bool` y razón legible. Cualquiera activa
veta entrada y/o dispara salida si hay posición abierta.

Diseñadas para ser INDEPENDIENTES: el diseño del usuario marca que no se debe
entrar si CUALQUIERA está activa.
"""
from __future__ import annotations
import pandas as pd
import numpy as np

from .indicators import sma, ema, atr, rsi, rolling_max


# E1 — Cluster de distribución (señal de mercado, no de stock)
def e1_market_distribution(spy_prices: pd.DataFrame, qqq_prices: pd.DataFrame,
                            window: int = 25, threshold: int = 5) -> dict:
    """Cuenta días de distribución (cierre <-0.2% con volumen > día anterior)
    en SPY+QQQ últimos `window` días. Resets:
    - Follow-through day (cierre +1.0% con volumen > día anterior)
    - Nuevo máximo histórico tocado dentro de la ventana
    Si índice cierra a <1% de su máximo de 50 días, distribución pasada está
    absorbida por definición — no marca señal.
    """
    def _dd_count(df: pd.DataFrame) -> int:
        if df is None or len(df) < window + 1:
            return 0
        # Gate: si índice está pegado a máximo de 50d, contador es ruido
        recent = df["close"].iloc[-50:] if len(df) >= 50 else df["close"]
        if len(recent) >= 10:
            last_close = float(df["close"].iloc[-1])
            high_50 = float(recent.max())
            if last_close >= high_50 * 0.99:
                return 0
        c = df["close"].iloc[-(window + 1):]
        v = df["volume"].iloc[-(window + 1):]
        ret = c.pct_change()
        dd = (ret < -0.002) & (v.diff() > 0)
        ft = (ret > 0.010) & (v.diff() > 0)
        # Reset también si nuevo máximo de la ventana tocado
        rolling_high = c.cummax()
        new_high = c == rolling_high
        dd_window = dd.iloc[1:]
        reset_days = (ft.iloc[1:] | new_high.iloc[1:])
        reset_dates = reset_days[reset_days].index
        if len(reset_dates) > 0:
            last_reset = reset_dates.max()
            dd_window = dd_window.loc[dd_window.index > last_reset]
        return int(dd_window.sum())
    spy_dd = _dd_count(spy_prices)
    qqq_dd = _dd_count(qqq_prices)
    total = max(spy_dd, qqq_dd)
    return {
        "active": total >= threshold,
        "spy_dd": spy_dd,
        "qqq_dd": qqq_dd,
        "reason": f"Mercado en distribución: {total} días bajistas con volumen alto tras último rally de confirmación" if total >= threshold else None,
    }


# E2 — Pérdida de SMA50 con volumen (requiere 3 cierres consecutivos + volumen 1.5×)
def e2_loss_sma50(prices: pd.DataFrame, consecutive: int = 3) -> dict:
    if prices is None or len(prices) < 60:
        return {"active": False, "reason": None}
    close = prices["close"]
    vol = prices["volume"]
    sma50 = sma(close, 50)
    vol_avg = sma(vol, 50)
    last_close = float(close.iloc[-1])
    last_sma50 = float(sma50.iloc[-1]) if sma50.iloc[-1] == sma50.iloc[-1] else None
    last_vol = float(vol.iloc[-1])
    avg_vol = float(vol_avg.iloc[-1]) if vol_avg.iloc[-1] == vol_avg.iloc[-1] else None
    if last_sma50 is None or avg_vol is None:
        return {"active": False, "reason": None}
    # 3 cierres consecutivos bajo SMA50 evita falsas salidas por días malos puntuales
    below_streak = bool((close.iloc[-consecutive:].values < sma50.iloc[-consecutive:].values).all())
    high_vol = bool(last_vol > 1.5 * avg_vol)
    active = bool(below_streak and high_vol)
    return {
        "active": active,
        "last_close": last_close,
        "sma50": last_sma50,
        "reason": f"Pérdida de SMA50 confirmada: {consecutive} cierres consecutivos ({last_close:.2f} < {last_sma50:.2f}) con volumen {last_vol/avg_vol:.1f}×" if active else None,
    }


# E3 — Stop dinámico ATR (Chandelier)
def e3_chandelier_stop(prices: pd.DataFrame, atr_n: int = 22, mult: float = 3.0) -> dict:
    if prices is None or len(prices) < atr_n + 5:
        return {"active": False, "reason": None}
    high = prices["high"]
    close = prices["close"]
    a = atr(prices, atr_n)
    chandelier = high.rolling(atr_n, min_periods=atr_n).max() - mult * a
    last_close = float(close.iloc[-1])
    last_chand = float(chandelier.iloc[-1]) if chandelier.iloc[-1] == chandelier.iloc[-1] else None
    if last_chand is None:
        return {"active": False, "reason": None}
    active = bool(last_close < last_chand)
    return {
        "active": active,
        "last_close": last_close,
        "chandelier": last_chand,
        "reason": f"Stop ATR roto: cierre {last_close:.2f} < trailing stop {last_chand:.2f}" if active else None,
    }


# E4 — Climax / blow-off
def e4_blow_off(prices: pd.DataFrame) -> dict:
    if prices is None or len(prices) < 50:
        return {"active": False, "reason": None}
    close = prices["close"]
    sma50_v = sma(close, 50)
    rsi14 = rsi(close, 14)
    last_close = float(close.iloc[-1])
    last_sma50 = float(sma50_v.iloc[-1]) if sma50_v.iloc[-1] == sma50_v.iloc[-1] else None
    last_rsi = float(rsi14.iloc[-1]) if rsi14.iloc[-1] == rsi14.iloc[-1] else None
    if last_sma50 is None or last_rsi is None:
        return {"active": False, "reason": None}
    extension = last_close / last_sma50 - 1
    # Divergencia bajista: precio hace nuevo máximo en 10 días pero RSI no
    look = min(10, len(close) - 1)
    p_max_idx = close.iloc[-look:].idxmax()
    rsi_at_pmax = rsi14.loc[p_max_idx] if p_max_idx in rsi14.index else None
    rsi_max = rsi14.iloc[-look:].max()
    bearish_div = bool(rsi_at_pmax is not None and rsi_at_pmax < rsi_max - 5 and last_rsi > 70)
    climax = (extension > 0.70) or (last_rsi > 80 and bearish_div)
    return {
        "active": bool(climax),
        "extension": float(extension),
        "rsi": last_rsi,
        "bearish_divergence": bearish_div,
        "reason": f"Posible blow-off: extensión {extension*100:.0f}% sobre SMA50, RSI {last_rsi:.0f}" + (" + divergencia bajista" if bearish_div else "") if climax else None,
    }


# E5 — RS rolling over
def e5_rs_rolling_over(close: pd.Series, bench_close: pd.Series,
                       sma_n: int = 50, days: int = 5) -> dict:
    df = pd.concat([close, bench_close], axis=1, join="inner")
    df.columns = ["c", "b"]
    if len(df) < sma_n + days + 5:
        return {"active": False, "reason": None}
    rl = df["c"] / df["b"]
    rl_sma = rl.rolling(sma_n, min_periods=sma_n).mean()
    cmp_ = (rl < rl_sma).iloc[-days:]
    active = bool(cmp_.all() and cmp_.notna().all())
    return {
        "active": active,
        "reason": f"Fuerza relativa rompiendo: RS-line bajo su SMA{sma_n} durante {days} sesiones seguidas" if active else None,
    }


# E6 — Rotación sectorial
def e6_sector_rotation_out(sector_etf_prices: pd.DataFrame, spy_prices: pd.DataFrame,
                            sma_n: int = 50, days: int = 5) -> dict:
    if sector_etf_prices is None or spy_prices is None:
        return {"active": False, "reason": None}
    base = e5_rs_rolling_over(sector_etf_prices["close"], spy_prices["close"], sma_n, days)
    if base.get("active"):
        base["reason"] = f"Rotación sectorial out: ETF del sector bajo su SMA{sma_n} vs SPY {days} sesiones"
    base["kind"] = "sector"
    return base


# E7 — Presión de distribución sostenida (volumen vendedor domina 13 semanas)
def e7_distribution_pressure(prices: pd.DataFrame, window: int = 65) -> dict:
    """Compara volumen total en días alcistas vs bajistas últimas 13 semanas.
    Ratio <0.75 (mucho más volumen vendedor que comprador) indica distribución institucional.
    """
    if prices is None or len(prices) < window + 1:
        return {"active": False, "reason": None}
    df = prices.iloc[-(window + 1):].copy()
    df = df.assign(prev_close=df["close"].shift(1)).dropna()
    up_vol   = float(df.loc[df["close"] > df["prev_close"], "volume"].sum())
    down_vol = float(df.loc[df["close"] < df["prev_close"], "volume"].sum())
    if up_vol + down_vol == 0:
        return {"active": False, "reason": None}
    ratio = up_vol / (down_vol + 1)
    active = bool(ratio < 0.75)
    return {
        "active": active,
        "acc_dist_ratio": ratio,
        "reason": f"Distribución institucional: ratio compra/venta {ratio:.2f} en últimas {window // 5} semanas" if active else None,
    }


def aggregate_exit(prices: pd.DataFrame,
                   spy_prices: pd.DataFrame,
                   qqq_prices: pd.DataFrame,
                   sector_etf_prices: pd.DataFrame | None,
                   use_market_distribution: bool = True) -> dict:
    """Aplica las 6 señales y devuelve resumen."""
    e1 = e1_market_distribution(spy_prices, qqq_prices) if use_market_distribution else {"active": False, "reason": None}
    e2 = e2_loss_sma50(prices)
    e3 = e3_chandelier_stop(prices)
    e4 = e4_blow_off(prices)
    e5 = e5_rs_rolling_over(prices["close"], spy_prices["close"]) if spy_prices is not None else {"active": False}
    if sector_etf_prices is not None:
        e6 = e6_sector_rotation_out(sector_etf_prices, spy_prices)
    else:
        e6 = {"active": False, "reason": None}
    e7 = e7_distribution_pressure(prices)
    # E1 (distribución de mercado) basta sola — es señal global, no de un ticker.
    # Para señales individuales (E2-E7) se requieren 2+ activas simultáneamente
    # para evitar falsas salidas por días malos puntuales en mercados volátiles.
    stock_signals = [e2, e3, e4, e5, e6, e7]
    stock_active_count = sum(1 for s in stock_signals if s.get("active"))
    any_active = bool(e1.get("active") or stock_active_count >= 2)
    reasons = [s.get("reason") for s in (e1, e2, e3, e4, e5, e6, e7) if s.get("active") and s.get("reason")]
    return {
        "any_active": any_active,
        "E1": e1,
        "E2": e2,
        "E3": e3,
        "E4": e4,
        "E5": e5,
        "E6": e6,
        "E7": e7,
        "reasons": reasons,
    }
