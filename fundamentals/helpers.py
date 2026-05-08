"""Utilidades para extraer series trimestrales del JSON cacheado.

Soporta dos formatos:
- FMP: lista de dicts ordenados por fecha (más reciente primero)
- yfinance: dict con claves de fecha a métricas
"""
from __future__ import annotations
from typing import Any
import math


def safe_num(x: Any) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def fmp_quarterly_series(records: list[dict] | None, field: str) -> list[float]:
    """Extrae serie de un campo FMP en orden cronológico ascendente (más antiguo primero)."""
    if not records:
        return []
    vals = []
    # FMP devuelve más reciente primero; invertimos
    for r in reversed(records):
        v = safe_num(r.get(field))
        if v is not None:
            vals.append(v)
    return vals


def yfinance_series(d: dict | None, field: str) -> list[float]:
    """Extrae serie de un dict yfinance (quarterly_financials.to_dict())."""
    if not d:
        return []
    # yfinance.to_dict() => {timestamp: {field: value, ...}, ...} cuando es financials
    # PERO realmente es {field: {timestamp: value}}
    if field in d and isinstance(d[field], dict):
        items = sorted(d[field].items(), key=lambda kv: str(kv[0]))
        return [safe_num(v) for _, v in items if safe_num(v) is not None]
    # forma alternativa
    out = []
    for ts, row in d.items():
        if isinstance(row, dict) and field in row:
            v = safe_num(row[field])
            if v is not None:
                out.append((str(ts), v))
    out.sort(key=lambda kv: kv[0])
    return [v for _, v in out]


def get_field(fund: dict, *keys: str) -> Any:
    """Devuelve el primer campo no None de las claves."""
    for k in keys:
        v = fund.get(k)
        if v is not None and v != "":
            return v
    return None
