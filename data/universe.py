"""Construcción del universo de tickers a analizar.

Fuentes:
- S&P 500: Wikipedia (cacheado)
- Nasdaq-100: Wikipedia (cacheado)
- Lista extra y exclusiones desde config.yaml
"""
from __future__ import annotations
import io
import time
from pathlib import Path

import pandas as pd
import requests

from .config_loader import load_config, cache_dir

WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKI_NDX = "https://en.wikipedia.org/wiki/Nasdaq-100"

UA = {"User-Agent": "Mozilla/5.0 swing-screener"}


def _read_wiki_table(url: str, cache_name: str, table_idx: int = 0,
                     ticker_col_candidates=("Symbol", "Ticker")) -> pd.DataFrame:
    cache_path = cache_dir() / cache_name
    # cache 7 días
    if cache_path.exists() and (time.time() - cache_path.stat().st_mtime) < 7 * 24 * 3600:
        return pd.read_parquet(cache_path)

    r = requests.get(url, headers=UA, timeout=20)
    r.raise_for_status()
    tables = pd.read_html(io.StringIO(r.text))
    df = tables[table_idx]
    # localizar columna ticker
    tcol = next((c for c in ticker_col_candidates if c in df.columns), None)
    if tcol is None:
        # buscar en otras tablas
        for i, t in enumerate(tables):
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


def get_sp500() -> list[str]:
    df = _read_wiki_table(WIKI_SP500, "sp500.parquet", 0)
    return df["ticker"].tolist()


def get_nasdaq100() -> list[str]:
    # Tabla con la composición suele ser la 4ª (índice variable). Probamos varias.
    cache_path = cache_dir() / "nasdaq100.parquet"
    if cache_path.exists() and (time.time() - cache_path.stat().st_mtime) < 7 * 24 * 3600:
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
    # Detectar columna de nombre
    name_col = next((c for c in ("Company", "Security", "Name") if c in chosen.columns), None)
    cols = ["ticker"] + ([name_col] if name_col else [])
    out = chosen[cols].copy()
    if name_col:
        out = out.rename(columns={name_col: "name"})
    out.to_parquet(cache_path)
    return out["ticker"].tolist()


def get_names_map() -> dict[str, str]:
    """Devuelve dict ticker -> nombre empresa, leyendo de los caches de wikipedia."""
    out: dict[str, str] = {}
    for fname, name_col in [("sp500.parquet", "Security"), ("nasdaq100.parquet", "name")]:
        p = cache_dir() / fname
        if not p.exists():
            continue
        try:
            df = pd.read_parquet(p)
            if name_col not in df.columns:
                # fallback a otras posibles columnas
                for c in ("Security", "Company", "Name", "name"):
                    if c in df.columns:
                        name_col = c
                        break
                else:
                    continue
            for _, r in df.iterrows():
                tk = str(r["ticker"]).strip()
                nm = str(r[name_col]).strip()
                if tk and nm and tk not in out:
                    out[tk] = nm
        except Exception:
            pass
    return out


def build_universe() -> list[str]:
    cfg = load_config()
    u = cfg.get("universe", {})
    tickers: set[str] = set()
    for src in u.get("include", []):
        if src == "sp500":
            tickers.update(get_sp500())
        elif src == "nasdaq100":
            tickers.update(get_nasdaq100())
        elif isinstance(src, list):
            tickers.update(src)
    tickers.update(u.get("extra", []) or [])
    for x in u.get("exclude", []) or []:
        tickers.discard(x)
    return sorted(tickers)


if __name__ == "__main__":
    tk = build_universe()
    print(f"Universo: {len(tk)} tickers")
    print(tk[:20])
