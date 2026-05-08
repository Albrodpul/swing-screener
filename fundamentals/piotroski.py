"""Piotroski F-Score (0-9). Puerta dura: si F<5 → ineligible.

Implementación pragmática: usa los campos que tenemos (TTM + trimestrales).
Si faltan datos para una bandera concreta, no se puntúa (no penaliza ni premia).
"""
from __future__ import annotations
from .helpers import safe_num, get_field, fmp_quarterly_series, yfinance_series


def _ttm_sum(records, field, n=4):
    if not records:
        return None
    vals = [r.get(field) for r in records[:n] if r.get(field) is not None]
    if len(vals) < n:
        return None
    return sum(vals)


def compute_f_score(fund: dict) -> dict:
    if not fund:
        return {"f_score": 0, "missing": True, "details": {}}
    score = 0
    details = {}

    # Métricas TTM y trimestrales
    is_q = fund.get("quarterly_income") if fund.get("source") == "fmp" else None
    cf_q = fund.get("quarterly_cashflow") if fund.get("source") == "fmp" else None
    bs_q = fund.get("quarterly_balance") if fund.get("source") == "fmp" else None

    # 1. Net Income TTM > 0
    ni = None
    if is_q:
        ni = _ttm_sum(is_q, "netIncome")
    if ni is None:
        ni = safe_num(get_field(fund, "net_income"))
    if ni is not None:
        flag = ni > 0
        details["net_income_positive"] = flag
        if flag:
            score += 1

    # 2. CFO TTM > 0
    cfo = None
    if cf_q:
        cfo = _ttm_sum(cf_q, "operatingCashFlow") or _ttm_sum(cf_q, "netCashProvidedByOperatingActivities")
    if cfo is None:
        cfo = safe_num(get_field(fund, "operating_cashflow"))
    if cfo is not None:
        flag = cfo > 0
        details["cfo_positive"] = flag
        if flag:
            score += 1

    # 3. Quality of earnings: CFO > NI
    if cfo is not None and ni is not None:
        flag = cfo > ni
        details["cfo_gt_ni"] = flag
        if flag:
            score += 1

    # 4. ROA mejorando: ROA TTM > ROA TTM hace 1 año
    if is_q and bs_q:
        ni_curr = _ttm_sum(is_q[:4], "netIncome") if len(is_q) >= 4 else None
        ni_prev = _ttm_sum(is_q[4:8], "netIncome") if len(is_q) >= 8 else None
        ta_curr = safe_num(is_q[0].get("totalAssets")) if is_q else None
        # totalAssets viene en balance no en income. Buscar en bs_q
        ta_curr = safe_num(bs_q[0].get("totalAssets")) if bs_q else None
        ta_prev = safe_num(bs_q[4].get("totalAssets")) if (bs_q and len(bs_q) >= 5) else None
        if ni_curr and ta_curr and ni_prev and ta_prev and ta_curr > 0 and ta_prev > 0:
            roa_curr = ni_curr / ta_curr
            roa_prev = ni_prev / ta_prev
            flag = roa_curr > roa_prev
            details["roa_improving"] = flag
            if flag:
                score += 1

    # 5. Leverage decreciendo: Long term debt / TA TTM < hace 1 año
    if bs_q and len(bs_q) >= 5:
        ltd_curr = safe_num(bs_q[0].get("longTermDebt"))
        ltd_prev = safe_num(bs_q[4].get("longTermDebt"))
        ta_curr = safe_num(bs_q[0].get("totalAssets"))
        ta_prev = safe_num(bs_q[4].get("totalAssets"))
        if ltd_curr is not None and ltd_prev is not None and ta_curr and ta_prev:
            flag = (ltd_curr / ta_curr) < (ltd_prev / ta_prev)
            details["leverage_decreasing"] = flag
            if flag:
                score += 1

    # 6. Current ratio mejorando
    if bs_q and len(bs_q) >= 5:
        ca_c = safe_num(bs_q[0].get("totalCurrentAssets"))
        cl_c = safe_num(bs_q[0].get("totalCurrentLiabilities"))
        ca_p = safe_num(bs_q[4].get("totalCurrentAssets"))
        cl_p = safe_num(bs_q[4].get("totalCurrentLiabilities"))
        if ca_c and cl_c and ca_p and cl_p and cl_c > 0 and cl_p > 0:
            flag = (ca_c / cl_c) > (ca_p / cl_p)
            details["current_ratio_improving"] = flag
            if flag:
                score += 1

    # 7. Sin emisión de acciones (shares out estables o decreciendo)
    if bs_q and len(bs_q) >= 5:
        so_c = safe_num(bs_q[0].get("commonStock") or bs_q[0].get("commonStockSharesOutstanding"))
        so_p = safe_num(bs_q[4].get("commonStock") or bs_q[4].get("commonStockSharesOutstanding"))
        if so_c is not None and so_p is not None and so_p > 0:
            flag = so_c <= so_p * 1.02
            details["no_dilution"] = flag
            if flag:
                score += 1

    # 8. Margen bruto mejorando
    if is_q and len(is_q) >= 5:
        gp_c = safe_num(is_q[0].get("grossProfit"))
        rev_c = safe_num(is_q[0].get("revenue"))
        gp_p = safe_num(is_q[4].get("grossProfit"))
        rev_p = safe_num(is_q[4].get("revenue"))
        if all(v for v in (gp_c, rev_c, gp_p, rev_p)):
            flag = (gp_c / rev_c) > (gp_p / rev_p)
            details["gross_margin_improving"] = flag
            if flag:
                score += 1

    # 9. Asset turnover mejorando
    if is_q and bs_q and len(is_q) >= 5 and len(bs_q) >= 5:
        rev_c = safe_num(is_q[0].get("revenue"))
        rev_p = safe_num(is_q[4].get("revenue"))
        ta_c = safe_num(bs_q[0].get("totalAssets"))
        ta_p = safe_num(bs_q[4].get("totalAssets"))
        if all(v for v in (rev_c, rev_p, ta_c, ta_p)):
            flag = (rev_c / ta_c) > (rev_p / ta_p)
            details["asset_turnover_improving"] = flag
            if flag:
                score += 1

    # Si no hay nada, penalizar (data missing implica que no podemos juzgar)
    return {
        "f_score": score,
        "details": details,
        "missing": len(details) < 5,
    }


def compute_f_score_universe(funds_by_ticker):
    rows = []
    for tk, fund in funds_by_ticker.items():
        out = compute_f_score(fund or {})
        rows.append({"ticker": tk, "f_score": out["f_score"], "f_missing": out["missing"]})
    import pandas as pd
    return pd.DataFrame(rows).set_index("ticker")
