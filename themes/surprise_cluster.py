"""Detección de clustering de earnings beats por sector.

Cuenta empresas con beat consistente (ver inflection._earnings_surprise_signal)
agrupadas por sector. Si > N empresas del mismo sector beatean en 30 días,
hay narrativa positiva sectorial activa.

Output: {sector: {beats: int, total: int, beat_rate: float, hot: bool}}
"""
from __future__ import annotations
from collections import defaultdict

from ..fundamentals.inflection import _earnings_surprise_signal


def compute_surprise_cluster(funds_by_ticker: dict[str, dict],
                              hot_threshold: int = 4) -> dict[str, dict]:
    by_sector = defaultdict(lambda: {"beats": 0, "misses": 0, "total": 0})
    for tk, fund in funds_by_ticker.items():
        sector = (fund or {}).get("sector") or "Unknown"
        sig = _earnings_surprise_signal(fund or {})
        by_sector[sector]["total"] += 1
        if sig > 0:
            by_sector[sector]["beats"] += 1
        elif sig < 0:
            by_sector[sector]["misses"] += 1
    out = {}
    for sec, d in by_sector.items():
        rate = d["beats"] / d["total"] if d["total"] else 0
        out[sec] = {
            **d,
            "beat_rate": rate,
            "hot": d["beats"] >= hot_threshold,
        }
    return out
