"""Descarga de fundamentales: FMP free tier como primaria, yfinance como respaldo.

Datos cacheados a parquet por ticker. Refresco semanal por defecto.

NOTA importante sobre FMP free tier:
- Límite ~250 req/día. Llamamos selectivamente a:
  * /v3/profile/{ticker}        -> sector, marketCap, descripción
  * /v3/ratios-ttm/{ticker}     -> ratios TTM (ROIC, ROE, márgenes...)
  * /v3/key-metrics-ttm/{ticker} -> EV/EBITDA, P/FCF, etc
  * /v3/income-statement/{ticker}?period=quarter&limit=8 -> históricos
  * /v3/cash-flow-statement/{ticker}?period=quarter&limit=8
  * /v3/balance-sheet-statement/{ticker}?period=quarter&limit=8
  * /v3/analyst-estimates/{ticker} -> revisiones
  * /v3/earnings-surprises/{ticker} -> sorpresas históricas
  Total ~7 endpoints x ~30 tickers/día si quieres respetar límite estrictamente.
- Para universo de 600 tickers, usar plan pago O hacer batch a lo largo de 2-3 días.
- En modo prototipo puedes pasar a `mode="yfinance_only"`.
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from .config_loader import load_config, cache_dir

FUND_DIR_NAME = "fundamentals"
FMP_BASE = "https://financialmodelingprep.com/stable"
MAX_AGE_S = 7 * 24 * 3600  # 7 días


def _fund_dir() -> Path:
    p = cache_dir() / FUND_DIR_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def _fmp_key() -> str | None:
    cfg = load_config()
    return cfg.get("api_keys", {}).get("fmp")


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
def _fmp_get(endpoint: str, symbol: str | None = None, params: dict | None = None) -> Any:
    """FMP /stable/* endpoints. Pasa symbol como query param."""
    key = _fmp_key()
    if not key or key.startswith("TU_API_KEY"):
        raise RuntimeError("Falta API key de FMP en config.yaml")
    p = dict(params or {})
    if symbol is not None:
        p["symbol"] = symbol
    p["apikey"] = key
    r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=15)
    if r.status_code == 429:
        raise RuntimeError("FMP rate limit alcanzado (429)")
    r.raise_for_status()
    return r.json()


def _yfinance_fundamentals(ticker: str) -> dict:
    """Respaldo: extrae lo que se puede de yfinance."""
    t = yf.Ticker(ticker)
    info = {}
    try:
        info = t.info or {}
    except Exception:
        info = {}
    out = {
        "source": "yfinance",
        "name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": info.get("marketCap"),
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "peg": info.get("trailingPegRatio") or info.get("pegRatio"),
        "ps": info.get("priceToSalesTrailing12Months"),
        "pb": info.get("priceToBook"),
        "ev_ebitda": info.get("enterpriseToEbitda"),
        "ev_revenue": info.get("enterpriseToRevenue"),
        "profit_margin": info.get("profitMargins"),
        "operating_margin": info.get("operatingMargins"),
        "gross_margin": info.get("grossMargins"),
        "roa": info.get("returnOnAssets"),
        "roe": info.get("returnOnEquity"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "debt_to_equity": info.get("debtToEquity"),
        "current_ratio": info.get("currentRatio"),
        "free_cashflow": info.get("freeCashflow"),
        "ebitda": info.get("ebitda"),
        "total_revenue": info.get("totalRevenue"),
        "total_debt": info.get("totalDebt"),
        "total_cash": info.get("totalCash"),
    }
    # series trimestrales para inflexión
    try:
        q_inc = t.quarterly_financials  # DataFrame, columnas trimestres
        out["quarterly_income"] = q_inc.to_dict() if isinstance(q_inc, pd.DataFrame) else {}
    except Exception:
        out["quarterly_income"] = {}
    try:
        q_cf = t.quarterly_cashflow
        out["quarterly_cashflow"] = q_cf.to_dict() if isinstance(q_cf, pd.DataFrame) else {}
    except Exception:
        out["quarterly_cashflow"] = {}
    try:
        q_bs = t.quarterly_balance_sheet
        out["quarterly_balance"] = q_bs.to_dict() if isinstance(q_bs, pd.DataFrame) else {}
    except Exception:
        out["quarterly_balance"] = {}
    try:
        out["earnings_history"] = t.earnings_history.to_dict() if t.earnings_history is not None else {}
    except Exception:
        out["earnings_history"] = {}
    try:
        out["earnings_dates"] = t.earnings_dates.to_dict() if t.earnings_dates is not None else {}
    except Exception:
        out["earnings_dates"] = {}
    return out


def _fmp_fundamentals(ticker: str) -> dict:
    out: dict = {"source": "fmp"}
    try:
        prof = _fmp_get("profile", symbol=ticker)
        if isinstance(prof, list) and prof:
            out.update({
                "name": prof[0].get("companyName"),
                "sector": prof[0].get("sector"),
                "industry": prof[0].get("industry"),
                "market_cap": prof[0].get("marketCap") or prof[0].get("mktCap"),
                "beta": prof[0].get("beta"),
                "description": prof[0].get("description"),
            })
    except Exception:
        pass
    try:
        rttm = _fmp_get("ratios-ttm", symbol=ticker)
        if isinstance(rttm, list) and rttm:
            r0 = rttm[0]
            out.update({
                "gross_margin_ttm": r0.get("grossProfitMarginTTM"),
                "operating_margin_ttm": r0.get("operatingProfitMarginTTM"),
                "ebitda_margin_ttm": r0.get("ebitdaMarginTTM"),
                "debt_equity_ttm": r0.get("debtToEquityRatioTTM") or r0.get("debtEquityRatioTTM"),
                "interest_coverage_ttm": r0.get("interestCoverageRatioTTM") or r0.get("interestCoverageTTM"),
                "current_ratio_ttm": r0.get("currentRatioTTM"),
                "peg_ttm": r0.get("priceToEarningsGrowthRatioTTM") or r0.get("pegRatioTTM"),
                "price_fcf_ttm": r0.get("priceToFreeCashFlowRatioTTM") or r0.get("priceToFreeCashFlowsRatioTTM"),
                "fcf_per_share_ttm": r0.get("freeCashFlowPerShareTTM"),
            })
    except Exception:
        pass
    try:
        kmetrics = _fmp_get("key-metrics-ttm", symbol=ticker)
        if isinstance(kmetrics, list) and kmetrics:
            k0 = kmetrics[0]
            out.update({
                "roe_ttm": k0.get("returnOnEquityTTM"),
                "roa_ttm": k0.get("returnOnAssetsTTM"),
                "ev_ebitda_ttm": k0.get("evToEBITDATTM") or k0.get("enterpriseValueOverEBITDATTM"),
                "ev_ocf_ttm": k0.get("evToOperatingCashFlowTTM"),
                "ev_fcf_ttm": k0.get("evToFreeCashFlowTTM"),
                "fcf_yield_ttm": k0.get("freeCashFlowYieldTTM"),
                "earnings_yield_ttm": k0.get("earningsYieldTTM"),
                "net_debt_ebitda_ttm": k0.get("netDebtToEBITDATTM"),
                "roic_ttm_km": k0.get("returnOnInvestedCapitalTTM") or k0.get("returnOnCapitalEmployedTTM") or k0.get("roicTTM"),
                "market_cap_km": k0.get("marketCap"),
            })
    except Exception:
        pass
    # series trimestrales — free tier limita a 5 últimos
    for ep, key in [
        ("income-statement", "quarterly_income"),
        ("cash-flow-statement", "quarterly_cashflow"),
        ("balance-sheet-statement", "quarterly_balance"),
    ]:
        try:
            data = _fmp_get(ep, symbol=ticker, params={"period": "quarter", "limit": 5})
            out[key] = data if isinstance(data, list) else []
        except Exception:
            out[key] = []
    try:
        out["analyst_estimates"] = _fmp_get("analyst-estimates", symbol=ticker, params={"limit": 4, "period": "annual"})
    except Exception:
        out["analyst_estimates"] = []
    try:
        # /stable/earnings reemplaza al legacy earnings-surprises (free tier max 5)
        out["earnings_surprises"] = _fmp_get("earnings", symbol=ticker, params={"limit": 5})
    except Exception:
        out["earnings_surprises"] = []
    return out


def get_fundamentals(ticker: str, mode: str = "auto",
                     force_refresh: bool = False) -> dict:
    """Devuelve dict con fundamentales del ticker. Cachea a parquet/json.

    mode: "auto" (FMP si hay key, sino yfinance), "fmp", "yfinance_only".
    """
    path = _fund_dir() / f"{ticker}.json"
    if path.exists() and not force_refresh:
        if (time.time() - path.stat().st_mtime) < MAX_AGE_S:
            try:
                with path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

    use_fmp = False
    if mode == "fmp":
        use_fmp = True
    elif mode == "auto":
        try:
            use_fmp = bool(_fmp_key()) and not _fmp_key().startswith("TU_API_KEY")
        except Exception:
            use_fmp = False

    data: dict = {}
    if use_fmp:
        try:
            data = _fmp_fundamentals(ticker)
        except Exception as e:
            data = {"source": "fmp_failed", "error": str(e)}
    if not data or "sector" not in data or data.get("source", "").endswith("failed"):
        # respaldo siempre
        try:
            yf_data = _yfinance_fundamentals(ticker)
            # merge: lo que falte en data se rellena con yfinance
            for k, v in yf_data.items():
                if k not in data or data.get(k) in (None, "", []):
                    data[k] = v
            if "source" not in data:
                data["source"] = "yfinance"
        except Exception:
            pass

    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, default=str)
    except Exception:
        pass
    return data


if __name__ == "__main__":
    d = get_fundamentals("AAPL", mode="yfinance_only")
    print({k: v for k, v in d.items() if not isinstance(v, (dict, list))})
