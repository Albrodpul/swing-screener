"""Fundamental Inflection Score (FI).

Detecta empresas en *giro* fundamental — el setup tipo SanDisk / cycle turn.

Señales (cada una -1/0/+1):
1. Revisiones netas al alza últimas 4 semanas > +20%
2. Racha de sorpresas: últimos 2 trimestres beat > +5%
3. Aceleración de ingresos: rev_yoy_q0 > 0 y > rev_yoy_q-1
4. Pendiente de margen bruto últimos 4 trimestres > 0
5. FCF inflexión: TTM cruzó arriba de 0 o crecimiento >25% YoY
6. Subida de guidance (proxy: estimaciones futuras revisadas al alza)

Output: -100 a +100.
"""
from __future__ import annotations
from typing import Any
import math

import pandas as pd
import numpy as np

from .helpers import safe_num, fmp_quarterly_series, yfinance_series


def _yoy_growth(series: list[float]) -> float | None:
    """Crecimiento yoy del último valor vs hace 4 trimestres."""
    if len(series) < 5:
        return None
    last = series[-1]
    prev = series[-5]
    if prev is None or prev == 0:
        return None
    return (last / prev) - 1.0


def _slope_norm(series: list[float]) -> float | None:
    """Pendiente normalizada de regresión lineal."""
    if len(series) < 4:
        return None
    arr = np.array([v for v in series if v is not None], dtype=float)
    if len(arr) < 4:
        return None
    x = np.arange(len(arr))
    m, _ = np.polyfit(x, arr, 1)
    mean = arr.mean()
    if mean == 0:
        return None
    return float(m / mean)


def _revenues(fund: dict) -> list[float]:
    if fund.get("source") == "fmp":
        return fmp_quarterly_series(fund.get("quarterly_income"), "revenue")
    return yfinance_series(fund.get("quarterly_income"), "Total Revenue")


def _gross_profits(fund: dict) -> list[float]:
    if fund.get("source") == "fmp":
        gp = fmp_quarterly_series(fund.get("quarterly_income"), "grossProfit")
        rev = fmp_quarterly_series(fund.get("quarterly_income"), "revenue")
        if gp and rev and len(gp) == len(rev):
            return [g / r if r else None for g, r in zip(gp, rev) if r]
        return []
    # yfinance: Gross Profit vs Total Revenue
    gp = yfinance_series(fund.get("quarterly_income"), "Gross Profit")
    rev = yfinance_series(fund.get("quarterly_income"), "Total Revenue")
    if gp and rev and len(gp) == len(rev):
        return [g / r if r else None for g, r in zip(gp, rev) if r]
    return []


def _fcf_series(fund: dict) -> list[float]:
    if fund.get("source") == "fmp":
        return fmp_quarterly_series(fund.get("quarterly_cashflow"), "freeCashFlow")
    return yfinance_series(fund.get("quarterly_cashflow"), "Free Cash Flow")


def _eps_acceleration(fund: dict) -> int:
    """Detecta aceleración real de EPS: últimos 3 trimestres reportados
    todos positivos y cada uno mayor que el anterior (tipo Nvidia/Micron recovery).
    Retorna -1 si pérdidas crecientes, 0 si ambiguo, +1 si aceleración real.
    """
    surprises = fund.get("earnings_surprises") or []
    if not isinstance(surprises, list):
        return 0
    reported = sorted(
        [s for s in surprises if s.get("epsActual") is not None],
        key=lambda s: s.get("date", "")
    )
    eps_vals = [safe_num(s.get("epsActual")) for s in reported]
    eps_vals = [v for v in eps_vals if v is not None]
    if len(eps_vals) < 3:
        return 0
    last3 = eps_vals[-3:]
    # 3 trimestres positivos y cada uno mayor al anterior → aceleración real
    if all(v > 0 for v in last3) and last3[-1] > last3[-2] > last3[-3]:
        return 1
    # Pérdidas crecientes
    if all(v < 0 for v in last3) and last3[-1] < last3[-2]:
        return -1
    return 0


def _earnings_surprise_signal(fund: dict) -> int:
    surprises = fund.get("earnings_surprises") or []
    # Para FMP es lista de dicts. Para yfinance es earnings_history dict.
    if isinstance(surprises, list) and surprises:
        # /stable/earnings: lista con epsActual/epsEstimated. Filtra a reportados (epsActual no null) y ordena por fecha desc
        reported = [s for s in surprises if s.get("epsActual") is not None and s.get("epsEstimated") is not None]
        reported.sort(key=lambda s: s.get("date", ""), reverse=True)
        last_two = reported[:2]
        if last_two:
            beats = []
            for s in last_two:
                est = safe_num(s.get("epsEstimated") or s.get("estimatedEarning"))
                act = safe_num(s.get("epsActual") or s.get("actualEarningResult"))
                if est and act and est != 0:
                    beats.append((act - est) / abs(est))
            if len(beats) >= 2 and all(b > 0.05 for b in beats):
                return 1
            if len(beats) >= 2 and all(b < -0.05 for b in beats):
                return -1
    # yfinance earnings_history
    eh = fund.get("earnings_history")
    if isinstance(eh, dict) and eh:
        # estructura: {field: {timestamp: value}}
        eps_act = eh.get("epsActual") or {}
        eps_est = eh.get("epsEstimate") or {}
        common = sorted(set(eps_act.keys()) & set(eps_est.keys()), reverse=True)[:2]
        beats = []
        for k in common:
            a = safe_num(eps_act.get(k))
            e = safe_num(eps_est.get(k))
            if a is not None and e is not None and e != 0:
                beats.append((a - e) / abs(e))
        if len(beats) >= 2 and all(b > 0.05 for b in beats):
            return 1
        if len(beats) >= 2 and all(b < -0.05 for b in beats):
            return -1
    return 0


def _revisions_signal(fund: dict) -> int:
    """+1 si revisiones netas al alza recientes > 20%, -1 si bajadas, 0 ambiguo."""
    est = fund.get("analyst_estimates")
    if isinstance(est, list) and est:
        # FMP: "estimatedRevenueAvg" actual vs el del trimestre anterior
        if len(est) >= 2:
            cur_rev_avg = safe_num(est[0].get("revenueAvg") or est[0].get("estimatedRevenueAvg"))
            prev_rev_avg = safe_num(est[1].get("revenueAvg") or est[1].get("estimatedRevenueAvg"))
            if cur_rev_avg and prev_rev_avg and prev_rev_avg > 0:
                delta = cur_rev_avg / prev_rev_avg - 1
                if delta > 0.05:
                    return 1
                if delta < -0.05:
                    return -1
    # respaldo: revenue_growth de yfinance
    rg = safe_num(fund.get("revenue_growth"))
    if rg is not None:
        if rg > 0.20:
            return 1
        if rg < -0.05:
            return -1
    return 0


def compute_fi_score(fund: dict) -> dict:
    if not fund:
        return {"fi_score": 0.0, "signals": {}, "flags": []}
    signals = {}
    flags = []

    # 1. Revisiones
    rev_sig = _revisions_signal(fund)
    signals["revisions"] = rev_sig
    if rev_sig > 0:
        flags.append("Revisiones de analistas al alza")
    elif rev_sig < 0:
        flags.append("Revisiones de analistas a la baja")

    # 2. Sorpresas
    surp = _earnings_surprise_signal(fund)
    signals["surprises"] = surp
    if surp > 0:
        flags.append("Beat consistente últimos 2 trimestres")
    elif surp < 0:
        flags.append("Miss consistente últimos 2 trimestres")

    # 3. Aceleración revenue (requiere crecimiento meaningful >5% y acelerando)
    revenues = _revenues(fund)
    if len(revenues) >= 6:
        try:
            yoy_now = revenues[-1] / revenues[-5] - 1
            yoy_prev = revenues[-2] / revenues[-6] - 1
            # Aceleración real: creciendo >5% YoY Y acelerando vs trimestre anterior
            if yoy_now > 0.05 and yoy_now > yoy_prev:
                signals["revenue_accel"] = 1
                flags.append(f"Ingresos acelerando ({yoy_now*100:.0f}% YoY vs {yoy_prev*100:.0f}% trimestre anterior)")
            # Alto crecimiento aunque no acelere (>20% YoY sostenido)
            elif yoy_now > 0.20:
                signals["revenue_accel"] = 1
                flags.append(f"Ingresos en alto crecimiento ({yoy_now*100:.0f}% YoY)")
            elif yoy_now < yoy_prev and yoy_now < 0:
                signals["revenue_accel"] = -1
                flags.append("Ingresos desacelerando en negativo")
            else:
                signals["revenue_accel"] = 0
        except Exception:
            signals["revenue_accel"] = 0
    else:
        signals["revenue_accel"] = 0

    # 4. Margen bruto
    gm = _gross_profits(fund)
    if len(gm) >= 4:
        s = _slope_norm(gm[-4:])
        if s is not None and s > 0.005:
            signals["gross_margin"] = 1
            flags.append("Margen bruto en expansión los últimos 4 trimestres")
        elif s is not None and s < -0.005:
            signals["gross_margin"] = -1
            flags.append("Margen bruto en contracción")
        else:
            signals["gross_margin"] = 0
    else:
        signals["gross_margin"] = 0

    # 5. FCF
    fcfs = _fcf_series(fund)
    if len(fcfs) >= 5:
        last4 = sum(fcfs[-4:])
        prev4 = sum(fcfs[-8:-4]) if len(fcfs) >= 8 else None
        if prev4 is not None and prev4 != 0:
            growth = (last4 - prev4) / abs(prev4)
            if last4 > 0 and (prev4 < 0 or growth > 0.25):
                signals["fcf"] = 1
                flags.append("Free cash flow inflexionando al alza")
            elif last4 < prev4 and last4 < 0:
                signals["fcf"] = -1
                flags.append("Free cash flow deteriorándose")
            else:
                signals["fcf"] = 0
        else:
            signals["fcf"] = 0
    else:
        signals["fcf"] = 0

    # 6. Aceleración de EPS (3 trimestres consecutivos creciendo = superperformer pattern)
    eps_accel = _eps_acceleration(fund)
    signals["eps_accel"] = eps_accel
    if eps_accel > 0:
        flags.append("EPS acelerando 3 trimestres consecutivos (patrón superperformer)")
    elif eps_accel < 0:
        flags.append("Pérdidas crecientes")

    raw = sum(signals.values())  # rango -6..+6
    fi_score = max(-100.0, min(100.0, raw / 6.0 * 100.0))
    return {
        "fi_score": float(fi_score),
        "signals": signals,
        "flags": flags,
    }


def compute_fi_universe(funds_by_ticker: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for tk, fund in funds_by_ticker.items():
        out = compute_fi_score(fund or {})
        rows.append({"ticker": tk, "fi_score": out["fi_score"],
                     "fi_flags": out["flags"], "fi_signals": out["signals"]})
    return pd.DataFrame(rows).set_index("ticker")
