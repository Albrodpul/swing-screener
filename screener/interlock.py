"""Combina capa fundamental + técnica + temas y aplica regla de entrada/salida.

Regla dura del usuario: si CUALQUIER señal de salida está activa, descarta
COMPRA aunque cumpla todas las de entrada. Marca como EVITAR con motivo.
"""
from __future__ import annotations
from typing import Any
import pandas as pd


def decide_signal(*, trend: dict, breakout: dict, rs: dict, rs_line: dict,
                   exits: dict, fund_eligible: bool, fi_negative_streak: bool) -> dict:
    entry_pass = bool(
        trend.get("trend_template")
        and trend.get("not_extended")
        and (rs.get("rs_rating") or 0) >= 80
        and rs_line.get("rs_line_at_high", False)
        and breakout.get("breakout")
        and breakout.get("volume_ok")
    )
    exit_active = bool(exits.get("any_active") or fi_negative_streak)
    # SALIDA solo aplica si el ticker era candidato/líder. Si no, exit_active es ruido base → EVITAR.
    was_leader = bool(trend.get("trend_template")) or (rs.get("rs_rating") or 0) >= 70
    if not fund_eligible:
        signal = "INELIGIBLE"
    elif entry_pass and not exit_active:
        signal = "COMPRA"
    elif entry_pass and exit_active:
        signal = "EVITAR"
    elif exit_active and was_leader:
        signal = "SALIDA"
    elif exit_active:
        signal = "EVITAR"
    else:
        signal = "OBSERVAR"

    # razones humanas
    entry_reasons = []
    if trend.get("trend_template"):
        entry_reasons.append("Patrón de tendencia alcista (Stage 2)")
    if trend.get("not_extended"):
        entry_reasons.append(f"No extendida ({(trend.get('pct_above_sma50') or 0)*100:.0f}% sobre SMA50)")
    if (rs.get("rs_rating") or 0) >= 80:
        entry_reasons.append(f"Fuerza relativa alta (RS {rs.get('rs_rating'):.0f}/100)")
    if rs_line.get("rs_line_at_high"):
        entry_reasons.append("Línea de fuerza relativa en máximos")
    if rs_line.get("rs_slope_improving"):
        entry_reasons.append("Fuerza relativa mejorando últimas 4 semanas")
    if breakout.get("breakout") and breakout.get("volume_ok"):
        vr = breakout.get("volume_ratio") or 0
        entry_reasons.append(f"Breakout sobre pivot con volumen {vr:.1f}× lo normal")

    entry_blockers = []
    if not trend.get("trend_template"):
        if not trend.get("price_above_150_200"):
            entry_blockers.append("Precio por debajo de SMA150 o SMA200")
        if not trend.get("mas_aligned"):
            entry_blockers.append("Medias móviles no alineadas alcistas")
        if not trend.get("sma200_uptrend"):
            entry_blockers.append("SMA200 sin pendiente alcista")
        if not trend.get("near_52w_high"):
            entry_blockers.append("Lejos del máximo de 52 semanas")
    if trend.get("trend_template") and not trend.get("not_extended"):
        entry_blockers.append(f"Demasiado extendida ({(trend.get('pct_above_sma50') or 0)*100:.0f}% sobre SMA50)")
    if (rs.get("rs_rating") or 0) < 80:
        entry_blockers.append(f"Fuerza relativa insuficiente (RS {rs.get('rs_rating') or 0:.0f})")
    if not breakout.get("breakout"):
        entry_blockers.append("Sin breakout reciente sobre resistencia")
    if breakout.get("breakout") and not breakout.get("volume_ok"):
        entry_blockers.append("Breakout sin confirmación de volumen")

    return {
        "signal": signal,
        "entry_pass": entry_pass,
        "exit_active": exit_active,
        "entry_reasons": entry_reasons,
        "entry_blockers": entry_blockers,
        "exit_reasons": exits.get("reasons", []) + (["Deterioro fundamental sostenido"] if fi_negative_streak else []),
    }


def composite_fundamental(qv_score: float | None, fi_score: float | None,
                           theme_score: float | None,
                           weights: dict | None = None) -> float:
    w = weights or {"qv": 0.40, "fi": 0.35, "theme": 0.25}
    qv = qv_score if qv_score is not None else 50.0
    fi_norm = ((fi_score if fi_score is not None else 0.0) + 100) / 2  # -100..100 -> 0..100
    theme = theme_score if theme_score is not None else 50.0
    return float(w["qv"] * qv + w["fi"] * fi_norm + w["theme"] * theme)
