"""Mide qué sectores tienen viento de cola.

Calcula RS 3 meses de cada ETF sectorial vs SPY y devuelve percentil.
Mapea cada ticker a su sector ETF.
"""
from __future__ import annotations
import pandas as pd

# Mapeo sector GICS -> ETF SPDR/temático
SECTOR_TO_ETF = {
    "Technology": "XLK",
    "Information Technology": "XLK",
    "Communication Services": "XLC",
    "Consumer Cyclical": "XLY",
    "Consumer Discretionary": "XLY",
    "Consumer Defensive": "XLP",
    "Consumer Staples": "XLP",
    "Healthcare": "XLV",
    "Health Care": "XLV",
    "Financial Services": "XLF",
    "Financials": "XLF",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Basic Materials": "XLB",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
}

# ETFs temáticos adicionales
THEME_ETFS = ["SMH", "SOXX", "IGV", "ARKK", "HACK", "XBI"]
ALL_SECTOR_ETFS = sorted(set(SECTOR_TO_ETF.values()) | {"SPY", "QQQ"} | set(THEME_ETFS))


def compute_sector_rs(price_map: dict[str, pd.DataFrame], lookback: int = 63) -> dict[str, float]:
    """Devuelve dict {etf: rs_score 0-100} basado en retorno 63d vs SPY."""
    if "SPY" not in price_map:
        return {}
    spy = price_map["SPY"]["close"]
    if len(spy) < lookback + 1:
        return {}
    spy_ret = float(spy.iloc[-1] / spy.iloc[-(lookback + 1)] - 1)
    raws = {}
    for etf, df in price_map.items():
        if etf == "SPY" or etf not in ALL_SECTOR_ETFS:
            continue
        c = df["close"]
        if len(c) < lookback + 1:
            continue
        ret = float(c.iloc[-1] / c.iloc[-(lookback + 1)] - 1)
        raws[etf] = ret - spy_ret
    if not raws:
        return {}
    s = pd.Series(raws)
    pct = s.rank(pct=True) * 100
    return pct.to_dict()


def get_sector_etf(sector_name: str | None) -> str | None:
    if not sector_name:
        return None
    return SECTOR_TO_ETF.get(sector_name)


def assign_theme_score(funds_by_ticker: dict[str, dict],
                        sector_rs: dict[str, float]) -> dict[str, dict]:
    """Devuelve por ticker {sector_etf, sector_rs_pct, theme_score}.

    theme_score = sector_rs_pct (single source v1; surprise clustering en módulo aparte).
    """
    out = {}
    for tk, fund in funds_by_ticker.items():
        sector = (fund or {}).get("sector")
        etf = get_sector_etf(sector)
        rs = sector_rs.get(etf) if etf else None
        out[tk] = {
            "sector": sector,
            "sector_etf": etf,
            "sector_rs_pct": rs,
            "theme_score": rs if rs is not None else 50.0,
        }
    return out
