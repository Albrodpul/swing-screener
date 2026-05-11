"""Orquestador principal: ejecuta el pipeline diario.

Pasos:
1. Construir universo
2. Descargar precios (universo + benchmarks SPY/QQQ + ETFs sectoriales)
3. Calcular RS rating cross-sectional
4. Calcular sector rotation
5. Por cada ticker: trend_template + breakout + exit_signals + fundamental
6. Combinar via interlock
7. Devolver DataFrame con resultados ordenados
"""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.config_loader import load_config  # noqa: E402
from data.universe import build_universe, get_names_map  # noqa: E402
from data.fetch_prices import get_prices_batch  # noqa: E402
from data.fetch_fundamentals import get_fundamentals  # noqa: E402

from technicals.trend_template import latest_trend_state  # noqa: E402
from technicals.relative_strength import compute_rs_universe, rs_line_state  # noqa: E402
from technicals.breakout import detect_breakout  # noqa: E402
from technicals.exit_signals import aggregate_exit  # noqa: E402

from fundamentals.qv_score import compute_qv_scores  # noqa: E402
from fundamentals.inflection import compute_fi_universe  # noqa: E402
from fundamentals.piotroski import compute_f_score_universe  # noqa: E402

from themes.sector_rotation import (
    compute_sector_rs, assign_theme_score, ALL_SECTOR_ETFS, get_sector_etf
)  # noqa: E402

from screener.interlock import decide_signal, composite_fundamental  # noqa: E402


def _load_fundamentals(tickers: list[str], mode: str = "auto", verbose: bool = True) -> dict[str, dict]:
    out: dict[str, dict] = {}
    iterator = tickers
    if verbose:
        try:
            from tqdm import tqdm
            iterator = tqdm(tickers, desc="Fundamentales")
        except Exception:
            pass
    for tk in iterator:
        try:
            out[tk] = get_fundamentals(tk, mode=mode)
        except Exception:
            out[tk] = {}
    return out


def run_pipeline(tickers: list[str] | None = None,
                 fund_mode: str = "auto",
                 verbose: bool = True,
                 market: str = "US",
                 spy_ticker: str = "SPY",
                 qqq_ticker: str | None = "QQQ") -> pd.DataFrame:
    cfg = load_config()
    universe = tickers if tickers else build_universe()
    if verbose:
        print(f"Universo [{market}]: {len(universe)} tickers")

    if market == "US":
        bench_tickers = [spy_ticker, qqq_ticker] + list(ALL_SECTOR_ETFS) if qqq_ticker else [spy_ticker] + list(ALL_SECTOR_ETFS)
    else:
        bench_tickers = [spy_ticker] + ([qqq_ticker] if qqq_ticker else [])
    bench_tickers = [t for t in bench_tickers if t]
    all_tickers = sorted(set(universe) | set(bench_tickers))

    # 1. Precios
    price_map = get_prices_batch(all_tickers, verbose=verbose)

    # 2. Sector RS (solo US)
    sector_rs = compute_sector_rs(price_map) if market == "US" else {}

    # 3. RS rating cross-sectional sobre universo (no incluir ETFs)
    universe_in_data = [t for t in universe if t in price_map]
    rs_results = compute_rs_universe({t: price_map[t] for t in universe_in_data})

    # 4. Fundamentales
    funds = _load_fundamentals(universe_in_data, mode=fund_mode, verbose=verbose)
    names_map = get_names_map()

    # 5. Scores fundamentales
    qv_df = compute_qv_scores(funds)
    fi_df = compute_fi_universe(funds)
    f_df = compute_f_score_universe(funds)
    theme_map = assign_theme_score(funds, sector_rs)

    spy = price_map.get(spy_ticker)
    qqq = price_map.get(qqq_ticker) if qqq_ticker else None

    rows = []
    iterator = universe_in_data
    if verbose:
        try:
            from tqdm import tqdm
            iterator = tqdm(universe_in_data, desc="Screening")
        except Exception:
            pass

    piotroski_min = cfg["screening"].get("piotroski_min", 5)
    weights = cfg["screening"].get("weights", {})

    for tk in iterator:
        prices = price_map.get(tk)
        if prices is None or len(prices) < 220:
            continue

        trend = latest_trend_state(prices)
        breakout = detect_breakout(prices)
        rs = rs_results.get(tk, {"rs_rating": None, "rs_raw": None})
        rsl = rs_line_state(prices["close"], spy["close"]) if spy is not None else {}

        sector = (funds.get(tk) or {}).get("sector")
        sector_etf = get_sector_etf(sector) if market == "US" else None
        sector_etf_prices = price_map.get(sector_etf) if sector_etf else None
        exits = aggregate_exit(prices, spy, qqq, sector_etf_prices,
                               use_market_distribution=(market == "US"))

        f_score = int(f_df.loc[tk, "f_score"]) if tk in f_df.index else 0
        f_missing = bool(f_df.loc[tk, "f_missing"]) if tk in f_df.index else True
        qv_score = float(qv_df.loc[tk, "qv_score"]) if tk in qv_df.index and qv_df.loc[tk, "qv_score"] == qv_df.loc[tk, "qv_score"] else None
        fi_score = float(fi_df.loc[tk, "fi_score"]) if tk in fi_df.index else None
        fi_flags = fi_df.loc[tk, "fi_flags"] if tk in fi_df.index else []
        theme = theme_map.get(tk, {})

        fund_eligible = (f_score >= piotroski_min) or f_missing  # si datos insuficientes, no veta agresivamente
        fi_negative_streak = (fi_score is not None and fi_score < -40)

        composite_fund = composite_fundamental(qv_score, fi_score, theme.get("theme_score"), weights)

        decision = decide_signal(
            trend=trend, breakout=breakout, rs=rs, rs_line=rsl,
            exits=exits, fund_eligible=fund_eligible,
            fi_negative_streak=fi_negative_streak,
        )

        rows.append({
            "ticker": tk,
            "market": market,
            "name": (funds.get(tk) or {}).get("name") or names_map.get(tk) or tk,
            "sector": sector,
            "industry": (funds.get(tk) or {}).get("industry"),
            "sector_etf": theme.get("sector_etf"),
            "signal": decision["signal"],
            "close": trend.get("close"),
            "qv_score": qv_score,
            "fi_score": fi_score,
            "theme_score": theme.get("theme_score"),
            "f_score": f_score,
            "fund_composite": composite_fund,
            "rs_rating": rs.get("rs_rating"),
            "trend_template": trend.get("trend_template"),
            "not_extended": trend.get("not_extended"),
            "breakout": breakout.get("breakout"),
            "volume_ok": breakout.get("volume_ok"),
            "exit_active": exits.get("any_active"),
            "exit_reasons": exits.get("reasons"),
            "entry_reasons": decision.get("entry_reasons"),
            "entry_blockers": decision.get("entry_blockers"),
            "fi_flags": fi_flags,
            "pct_above_sma50": trend.get("pct_above_sma50"),
            "high_52w": trend.get("high_52w"),
            "low_52w": trend.get("low_52w"),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # Orden: COMPRA primero por composite, luego EVITAR/OBSERVAR/SALIDA
    sig_order = {"COMPRA": 0, "EVITAR": 1, "OBSERVAR": 2, "SALIDA": 3, "INELIGIBLE": 4}
    df["_sig_order"] = df["signal"].map(sig_order).fillna(99)
    df = df.sort_values(["_sig_order", "fund_composite"], ascending=[True, False]).drop(columns=["_sig_order"])
    return df.reset_index(drop=True)


if __name__ == "__main__":
    # Ejemplo rápido con 10 tickers
    test = ["NVDA", "SMCI", "AAPL", "MSFT", "INTC", "PLTR", "TSLA", "COIN", "AMD", "GOOG"]
    df = run_pipeline(test, fund_mode="yfinance_only")
    print(df[["ticker", "signal", "fund_composite", "rs_rating", "trend_template", "exit_active"]])
