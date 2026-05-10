"""Descarga y cache de precios OHLCV via yfinance.

Política de cache:
- Un fichero parquet por ticker en cache/prices/{TICKER}.parquet
- Si la última fila es de hoy o ayer (mercado cerrado), no refresca.
- Si está más antigua, refresca incrementalmente.
"""
from __future__ import annotations
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from .config_loader import cache_dir

PRICES_DIR_NAME = "prices"
DEFAULT_PERIOD = "3y"  # suficiente para SMA200 + RS 12m con margen


def _prices_dir() -> Path:
    p = cache_dir() / PRICES_DIR_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def _is_fresh(df: pd.DataFrame, max_age_days: int = 2) -> bool:
    if df is None or df.empty:
        return False
    last = pd.Timestamp(df.index[-1]).tz_localize(None)
    return (pd.Timestamp.utcnow().tz_localize(None) - last) <= pd.Timedelta(days=max_age_days)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def _download_one(ticker: str, period: str = DEFAULT_PERIOD) -> pd.DataFrame:
    df = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if df is None or df.empty:
        raise RuntimeError(f"yfinance vacío para {ticker}")
    # yfinance puede devolver MultiIndex en columnas si hay un solo ticker
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)
    df.index.name = "date"
    return df[["open", "high", "low", "close", "volume"]]


def get_prices(ticker: str, force_refresh: bool = False,
               period: str = DEFAULT_PERIOD) -> pd.DataFrame:
    path = _prices_dir() / f"{ticker}.parquet"
    if path.exists() and not force_refresh:
        try:
            df = pd.read_parquet(path)
            if _is_fresh(df):
                return df
        except Exception:
            pass
    try:
        df = _download_one(ticker, period=period)
        df.to_parquet(path)
        return df
    except Exception as e:
        if path.exists():
            return pd.read_parquet(path)
        raise


def get_prices_batch(tickers: list[str], force_refresh: bool = False,
                     verbose: bool = True, max_workers: int = 12) -> dict[str, pd.DataFrame]:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    out: dict[str, pd.DataFrame] = {}
    failures: list[str] = []

    def _fetch(tk: str) -> tuple[str, pd.DataFrame]:
        return tk, get_prices(tk, force_refresh=force_refresh)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch, tk): tk for tk in tickers}
        pbar = None
        if verbose:
            try:
                from tqdm import tqdm
                pbar = tqdm(total=len(tickers), desc="Precios")
            except Exception:
                pass
        for future in as_completed(futures):
            tk = futures[future]
            try:
                _, df = future.result()
                out[tk] = df
            except Exception:
                failures.append(tk)
            if pbar:
                pbar.update(1)
        if pbar:
            pbar.close()

    if verbose and failures:
        print(f"Sin datos para {len(failures)} tickers: {failures[:10]}{'...' if len(failures) > 10 else ''}")
    return out


if __name__ == "__main__":
    df = get_prices("AAPL")
    print(df.tail())
