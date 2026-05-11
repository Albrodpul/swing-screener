"""Construcción del universo de tickers a analizar.

Fuentes US:
- S&P 500, S&P 400, S&P 600: Wikipedia (cacheado 7 días)
- Nasdaq-100: Wikipedia (cacheado 7 días)

Fuentes EU:
- FTSE 100: Wikipedia → sufijo .L para yfinance
- DAX 40:   Wikipedia → sufijo .DE para yfinance
- CAC 40:   Wikipedia → sufijo .PA para yfinance
"""
from __future__ import annotations
import io
import time
from pathlib import Path

import pandas as pd
import requests

from .config_loader import load_config, cache_dir

WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKI_NDX   = "https://en.wikipedia.org/wiki/Nasdaq-100"
WIKI_SP400 = "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
WIKI_SP600 = "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies"
WIKI_FTSE  = "https://en.wikipedia.org/wiki/FTSE_100_Index"
WIKI_DAX   = "https://en.wikipedia.org/wiki/DAX"
WIKI_CAC   = "https://en.wikipedia.org/wiki/CAC_40"
WIKI_IBEX  = "https://en.wikipedia.org/wiki/IBEX_35"

UA = {"User-Agent": "Mozilla/5.0 swing-screener"}
CACHE_TTL = 7 * 24 * 3600


def _read_wiki_table(url: str, cache_name: str, table_idx: int = 0,
                     ticker_col_candidates=("Symbol", "Ticker")) -> pd.DataFrame:
    cache_path = cache_dir() / cache_name
    if cache_path.exists() and (time.time() - cache_path.stat().st_mtime) < CACHE_TTL:
        return pd.read_parquet(cache_path)

    r = requests.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    tables = pd.read_html(io.StringIO(r.text))
    df = tables[table_idx]
    tcol = next((c for c in ticker_col_candidates if c in df.columns), None)
    if tcol is None:
        for t in tables:
            tcol = next((c for c in ticker_col_candidates if c in t.columns), None)
            if tcol is not None:
                df = t
                break
        if tcol is None:
            raise RuntimeError(f"No encuentro columna ticker en {url}")
    df = df.rename(columns={tcol: "ticker"})
    df["ticker"] = df["ticker"].astype(str).str.replace(".", "-", regex=False).str.strip()
    df.to_parquet(cache_path)
    return df


# ── US indices ────────────────────────────────────────────────────────────────

def get_sp500() -> list[str]:
    df = _read_wiki_table(WIKI_SP500, "sp500.parquet", 0)
    return df["ticker"].tolist()


def get_nasdaq100() -> list[str]:
    cache_path = cache_dir() / "nasdaq100.parquet"
    if cache_path.exists() and (time.time() - cache_path.stat().st_mtime) < CACHE_TTL:
        return pd.read_parquet(cache_path)["ticker"].tolist()
    r = requests.get(WIKI_NDX, headers=UA, timeout=20)
    r.raise_for_status()
    tables = pd.read_html(io.StringIO(r.text))
    chosen = None
    for t in tables:
        cols = {c.lower() for c in t.columns.astype(str)}
        if "ticker" in cols or "symbol" in cols:
            tcol = "Ticker" if "Ticker" in t.columns else ("Symbol" if "Symbol" in t.columns else None)
            if tcol and len(t) >= 80:
                chosen = t.rename(columns={tcol: "ticker"})
                break
    if chosen is None:
        raise RuntimeError("No localicé la tabla de Nasdaq-100 en Wikipedia")
    chosen["ticker"] = chosen["ticker"].astype(str).str.replace(".", "-", regex=False).str.strip()
    name_col = next((c for c in ("Company", "Security", "Name") if c in chosen.columns), None)
    cols = ["ticker"] + ([name_col] if name_col else [])
    out = chosen[cols].copy()
    if name_col:
        out = out.rename(columns={name_col: "name"})
    out.to_parquet(cache_path)
    return out["ticker"].tolist()


def get_sp400() -> list[str]:
    df = _read_wiki_table(
        WIKI_SP400, "sp400.parquet", 0,
        ticker_col_candidates=("Ticker symbol", "Symbol", "Ticker"),
    )
    return df["ticker"].tolist()


def get_sp600() -> list[str]:
    df = _read_wiki_table(
        WIKI_SP600, "sp600.parquet", 0,
        ticker_col_candidates=("Ticker symbol", "Symbol", "Ticker"),
    )
    return df["ticker"].tolist()


# ── EU indices ────────────────────────────────────────────────────────────────

def _get_eu_index(url: str, cache_name: str, suffix: str,
                  ticker_col_candidates: tuple, min_rows: int = 30,
                  suffix_already_included: bool = False) -> list[str]:
    cache_path = cache_dir() / cache_name
    if cache_path.exists() and (time.time() - cache_path.stat().st_mtime) < CACHE_TTL:
        return pd.read_parquet(cache_path)["ticker"].tolist()

    r = requests.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    tables = pd.read_html(io.StringIO(r.text))

    chosen, tcol = None, None
    for t in tables:
        tcol = next((c for c in ticker_col_candidates if c in t.columns), None)
        if tcol and len(t) >= min_rows:
            chosen = t
            break

    if chosen is None or tcol is None:
        raise RuntimeError(f"No localicé tabla en {url}")

    chosen = chosen[[tcol]].rename(columns={tcol: "ticker"}).copy()
    chosen["ticker"] = chosen["ticker"].astype(str).str.strip()
    if not suffix_already_included:
        chosen["ticker"] = chosen["ticker"] + suffix
    suffix_re = suffix.lstrip(".")
    chosen = chosen[chosen["ticker"].str.match(r'^[A-Z0-9]{1,6}\.' + suffix_re + r'$')]
    chosen.to_parquet(cache_path)
    return chosen["ticker"].tolist()


def get_ftse100() -> list[str]:
    return _get_eu_index(
        WIKI_FTSE, "ftse100.parquet", ".L",
        ticker_col_candidates=("EPIC", "Ticker", "Symbol", "Ticker symbol"),
        min_rows=90,
    )


def get_dax40() -> list[str]:
    return _get_eu_index(
        WIKI_DAX, "dax40.parquet", ".DE",
        ticker_col_candidates=("Ticker symbol", "Ticker", "Symbol"),
        min_rows=35,
    )


def get_cac40() -> list[str]:
    return _get_eu_index(
        WIKI_CAC, "cac40.parquet", ".PA",
        ticker_col_candidates=("Ticker", "Symbol", "Ticker symbol"),
        min_rows=35,
    )


def get_ibex35() -> list[str]:
    return _get_eu_index(
        WIKI_IBEX, "ibex35.parquet", ".MC",
        ticker_col_candidates=("Ticker", "Symbol", "Ticker symbol"),
        min_rows=30,
        suffix_already_included=True,
    )


# ── Universe builders ─────────────────────────────────────────────────────────

def _build_from_cfg(cfg_section: dict) -> list[str]:
    tickers: set[str] = set()
    for src in cfg_section.get("include", []):
        fn = {
            "sp500": get_sp500, "nasdaq100": get_nasdaq100,
            "sp400": get_sp400, "sp600": get_sp600,
            "ftse100": get_ftse100, "dax40": get_dax40, "cac40": get_cac40, "ibex35": get_ibex35,
        }.get(src)
        if fn:
            tickers.update(fn())
    tickers.update(cfg_section.get("extra", []) or [])
    for x in cfg_section.get("exclude", []) or []:
        tickers.discard(x)
    return sorted(tickers)


def build_universe() -> list[str]:
    """US universe. Reads from universe.us (new config) or universe (legacy flat)."""
    cfg = load_config()
    u = cfg.get("universe", {})
    return _build_from_cfg(u.get("us", u))


def build_eu_universe() -> list[str]:
    """EU universe. Reads from universe.eu."""
    cfg = load_config()
    eu = cfg.get("universe", {}).get("eu", {})
    return _build_from_cfg(eu)


def get_names_map() -> dict[str, str]:
    out: dict[str, str] = {}
    for fname, name_col in [("sp500.parquet", "Security"), ("nasdaq100.parquet", "name")]:
        p = cache_dir() / fname
        if not p.exists():
            continue
        try:
            df = pd.read_parquet(p)
            if name_col not in df.columns:
                for c in ("Security", "Company", "Name", "name"):
                    if c in df.columns:
                        name_col = c
                        break
                else:
                    continue
            for _, row in df.iterrows():
                tk = str(row["ticker"]).strip()
                nm = str(row[name_col]).strip()
                if tk and nm and tk not in out:
                    out[tk] = nm
        except Exception:
            pass
    return out


if __name__ == "__main__":
    us = build_universe()
    eu = build_eu_universe()
    print(f"US: {len(us)} tickers")
    print(f"EU: {len(eu)} tickers")
    print(f"Total único: {len(set(us) | set(eu))}")
