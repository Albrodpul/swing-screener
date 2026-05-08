"""Renderizado de tarjetas family-friendly en español.

Cada tarjeta describe la decisión en lenguaje natural sin jerga técnica.
"""
from __future__ import annotations
from typing import Any
import pandas as pd
import numpy as np


def _as_list(x: Any) -> list:
    if x is None:
        return []
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


SIGNAL_LABEL = {
    "COMPRA": "🟢 COMPRA",
    "EVITAR": "🟠 EVITAR",
    "OBSERVAR": "⚪ OBSERVAR",
    "SALIDA": "🔴 SALIDA",
    "INELIGIBLE": "⛔ NO APTA",
}

SIGNAL_EXPLAIN = {
    "COMPRA": "Buen punto de entrada hoy. Cumple criterios de tendencia, fuerza y momento, y no hay señales de aviso.",
    "EVITAR": "Cumple criterios de entrada PERO hay alguna señal de aviso activa. Mejor esperar.",
    "OBSERVAR": "Empresa de calidad pero sin disparador de entrada hoy. Mantener en lista de seguimiento.",
    "SALIDA": "Si tuvieras posición, las señales sugieren reducir o cerrar.",
    "INELIGIBLE": "Calidad fundamental insuficiente (Piotroski bajo). No la sigo.",
}


def _bar(score: float | None, length: int = 20) -> str:
    if score is None or pd.isna(score):
        return "[?]"
    s = max(0.0, min(100.0, float(score)))
    filled = int(round(s / 100 * length))
    return f"[{'█' * filled}{'░' * (length - filled)}] {s:.0f}/100"


def render_card(row: pd.Series | dict) -> str:
    r = row if isinstance(row, dict) else row.to_dict()
    tk = r["ticker"]
    sig = r.get("signal", "OBSERVAR")
    label = SIGNAL_LABEL.get(sig, sig)
    sector = r.get("sector") or "—"
    close = r.get("close")
    high52 = r.get("high_52w")
    low52 = r.get("low_52w")

    lines = []
    lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f" {tk}  ·  {sector}  ·  {label}")
    if close is not None:
        info = f"Precio: {close:.2f}"
        if high52 and low52:
            info += f"   |   Rango 52s: {low52:.2f} – {high52:.2f}"
        lines.append(f" {info}")
    lines.append(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f" Veredicto: {SIGNAL_EXPLAIN.get(sig, '')}")
    lines.append("")
    lines.append(" 📊 Puntuaciones (0 = malo, 100 = excelente):")
    lines.append(f"   Calidad+Valor    {_bar(r.get('qv_score'))}")
    lines.append(f"   Inflexión        {_bar((r.get('fi_score') + 100) / 2 if r.get('fi_score') is not None else None)}")
    lines.append(f"   Viento sectorial {_bar(r.get('theme_score'))}")
    lines.append(f"   Composite total  {_bar(r.get('fund_composite'))}")
    lines.append(f"   Fuerza vs S&P    {_bar(r.get('rs_rating'))}")
    lines.append(f"   Piotroski        {r.get('f_score', 0)}/9")

    entry_reasons = _as_list(r.get("entry_reasons"))
    if entry_reasons:
        lines.append("")
        lines.append(" ✅ Lo que tiene a favor:")
        for x in entry_reasons:
            lines.append(f"   · {x}")

    fi_flags = _as_list(r.get("fi_flags"))
    if fi_flags:
        lines.append("")
        lines.append(" 🌱 Señales fundamentales:")
        for x in fi_flags:
            lines.append(f"   · {x}")

    blockers = _as_list(r.get("entry_blockers"))
    if blockers and sig != "COMPRA":
        lines.append("")
        lines.append(" ⚠️ Lo que falla para entrar:")
        for x in blockers:
            lines.append(f"   · {x}")

    exit_reasons = _as_list(r.get("exit_reasons"))
    if exit_reasons:
        lines.append("")
        lines.append(" 🚪 Señales de salida activas:")
        for x in exit_reasons:
            lines.append(f"   · {x}")

    return "\n".join(lines)


def render_top_buys(df: pd.DataFrame, n: int = 10) -> str:
    buys = df[df["signal"] == "COMPRA"].head(n)
    if buys.empty:
        return "No hay candidatas COMPRA hoy. Revisa la lista de OBSERVAR para próximos disparos."
    out = [f"\n=== TOP {len(buys)} CANDIDATAS COMPRA ===\n"]
    for _, row in buys.iterrows():
        out.append(render_card(row))
        out.append("")
    return "\n".join(out)


def render_top_observar(df: pd.DataFrame, n: int = 15) -> str:
    """Top OBSERVAR ordenadas por (RS+composite). Watchlist próximos disparos."""
    obs = df[df["signal"] == "OBSERVAR"].copy()
    if obs.empty:
        return "Sin OBSERVAR."
    obs["_score"] = obs["rs_rating"].fillna(0) * 0.5 + obs["fund_composite"].fillna(0) * 0.5
    obs = obs.sort_values("_score", ascending=False).head(n)
    out = [f"\n=== TOP {len(obs)} OBSERVAR (watchlist próximos disparos) ===\n"]
    for _, row in obs.iterrows():
        out.append(render_card(row))
        out.append("")
    return "\n".join(out)


def render_exit_watch(df: pd.DataFrame, n: int = 20) -> str:
    exits = df[df["signal"].isin(["SALIDA", "EVITAR"])].head(n)
    if exits.empty:
        return "Sin señales de salida activas en el universo."
    out = [f"\n=== {len(exits)} TICKERS CON SEÑAL DE SALIDA / EVITAR ===\n"]
    for _, row in exits.iterrows():
        out.append(render_card(row))
        out.append("")
    return "\n".join(out)


def summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """Tabla resumen para mostrar como DataFrame en el notebook."""
    cols = ["ticker", "signal", "sector", "fund_composite", "rs_rating",
            "qv_score", "fi_score", "theme_score", "f_score",
            "trend_template", "breakout", "exit_active"]
    return df[cols].copy()
