"""Quality + Value score normalizado por sector.

Métricas Calidad: ROIC, ROE, gross_margin, FCF/Sales, -Net_Debt/EBITDA
Métricas Valor:    -EV/EBIT (o EV/EBITDA), -P/FCF, -PEG  (negados: cheap=alto)

Output 0-100 (percentil del z-score combinado dentro del universo).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from .helpers import safe_num, get_field


QUALITY_WEIGHTS = {
    "roic": 0.25,
    "roe": 0.20,
    "gross_margin": 0.20,
    "fcf_sales": 0.20,
    "neg_net_debt_ebitda": 0.15,
}
VALUE_WEIGHTS = {
    "neg_ev_ebitda": 0.40,
    "neg_p_fcf": 0.35,
    "neg_peg": 0.25,
}


def _extract_metrics(fund: dict) -> dict:
    roic = safe_num(get_field(fund, "roic_ttm_km", "roic_ttm", "returnOnCapitalEmployed"))
    roe = safe_num(get_field(fund, "roe_ttm", "roe"))
    gm = safe_num(get_field(fund, "gross_margin_ttm", "gross_margin"))
    fcf = safe_num(get_field(fund, "free_cashflow"))
    revenue = safe_num(get_field(fund, "total_revenue"))
    fcf_sales = (fcf / revenue) if (fcf is not None and revenue and revenue > 0) else None
    nd_ebitda = safe_num(get_field(fund, "net_debt_ebitda_ttm"))
    if nd_ebitda is None:
        debt = safe_num(get_field(fund, "total_debt"))
        cash = safe_num(get_field(fund, "total_cash"))
        ebitda = safe_num(get_field(fund, "ebitda"))
        if debt is not None and ebitda and ebitda > 0:
            nd_ebitda = (debt - (cash or 0)) / ebitda
    ev_ebitda = safe_num(get_field(fund, "ev_ebitda_ttm", "ev_ebitda"))
    p_fcf = safe_num(get_field(fund, "price_fcf_ttm"))
    peg = safe_num(get_field(fund, "peg_ttm", "peg"))

    return {
        "roic": roic,
        "roe": roe,
        "gross_margin": gm,
        "fcf_sales": fcf_sales,
        "neg_net_debt_ebitda": -nd_ebitda if nd_ebitda is not None else None,
        "neg_ev_ebitda": -ev_ebitda if (ev_ebitda is not None and ev_ebitda > 0) else None,
        "neg_p_fcf": -p_fcf if (p_fcf is not None and p_fcf > 0) else None,
        "neg_peg": -peg if (peg is not None and peg > 0) else None,
        "sector": fund.get("sector") or "Unknown",
    }


def _zscore(s: pd.Series) -> pd.Series:
    s = s.astype(float)
    mu = s.mean()
    sd = s.std(ddof=0)
    if sd == 0 or pd.isna(sd):
        return pd.Series([0.0] * len(s), index=s.index)
    return (s - mu) / sd


def _sector_zscore(values: pd.Series, sectors: pd.Series, min_peers: int = 10) -> pd.Series:
    out = pd.Series(index=values.index, dtype=float)
    for sec in sectors.dropna().unique():
        mask = sectors == sec
        if mask.sum() < min_peers:
            continue
        out[mask] = _zscore(values[mask])
    # quien quede sin sector con pocos peers usa global
    missing = out.isna() & values.notna()
    if missing.any():
        out[missing] = _zscore(values[missing])
    return out


def compute_qv_scores(funds_by_ticker: dict[str, dict]) -> pd.DataFrame:
    rows = []
    for tk, fund in funds_by_ticker.items():
        m = _extract_metrics(fund or {})
        m["ticker"] = tk
        rows.append(m)
    df = pd.DataFrame(rows).set_index("ticker")
    if df.empty:
        return df

    quality_z = pd.Series(0.0, index=df.index)
    quality_w_total = pd.Series(0.0, index=df.index)
    for k, w in QUALITY_WEIGHTS.items():
        col = pd.to_numeric(df[k], errors="coerce")
        z = _sector_zscore(col, df["sector"])
        present = col.notna() & z.notna()
        quality_z[present] = quality_z[present] + w * z[present]
        quality_w_total[present] = quality_w_total[present] + w
    quality_z = quality_z / quality_w_total.replace(0, np.nan)

    value_z = pd.Series(0.0, index=df.index)
    value_w_total = pd.Series(0.0, index=df.index)
    for k, w in VALUE_WEIGHTS.items():
        col = pd.to_numeric(df[k], errors="coerce")
        z = _sector_zscore(col, df["sector"])
        present = col.notna() & z.notna()
        value_z[present] = value_z[present] + w * z[present]
        value_w_total[present] = value_w_total[present] + w
    value_z = value_z / value_w_total.replace(0, np.nan)

    qv_raw = 0.55 * quality_z.fillna(0) + 0.45 * value_z.fillna(0)
    qv_score = qv_raw.rank(pct=True) * 100

    df["quality_z"] = quality_z
    df["value_z"] = value_z
    df["qv_score"] = qv_score
    return df
