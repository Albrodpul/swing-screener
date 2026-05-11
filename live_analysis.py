"""Análisis en vivo de un ticker concreto. Escribe data/live/{ticker}.json"""
from __future__ import annotations
import argparse
import json
import math
import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from screener.pipeline import run_pipeline
from screener.plain_language import humanize_card

MARKET_CONFIG = {
    "US": {"spy": "SPY", "qqq": "QQQ"},
    "EU": {"spy": "EZU", "qqq": None},
}


def _safe(v):
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if hasattr(v, "tolist"):
        result = v.tolist()
        if isinstance(result, list):
            return [str(x) for x in result]
        return None if (isinstance(result, float) and math.isnan(result)) else result
    if hasattr(v, "item"):
        val = v.item()
        return None if (isinstance(val, float) and math.isnan(val)) else val
    if isinstance(v, list):
        return [str(x) for x in v]
    return v


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--market", default="US", choices=["US", "EU"])
    args = parser.parse_args()

    ticker = args.ticker.strip().upper()
    market = args.market.upper()
    cfg = MARKET_CONFIG[market]

    print(f"[live_analysis] Analizando {ticker} ({market})...")
    df = run_pipeline(
        tickers=[ticker],
        fund_mode="auto",
        verbose=True,
        market=market,
        spy_ticker=cfg["spy"],
        qqq_ticker=cfg["qqq"],
    )

    if df.empty:
        print(f"[live_analysis] Sin datos para {ticker}")
        sys.exit(1)

    row = df.iloc[0]

    try:
        c = humanize_card(row)
    except Exception:
        c = {}

    price = _safe(c.get("precio") or row.get("close"))

    result = {
        "ticker":         str(row["ticker"]),
        "market":         market,
        "name":           _safe(row.get("name")),
        "signal":         str(row["signal"]),
        "sector":         _safe(row.get("sector")),
        "industry":       _safe(row.get("industry")),
        "description":    _safe(row.get("description")),
        "rs_rating":      _safe(row.get("rs_rating")),
        "fund_composite": _safe(row.get("fund_composite")),
        "price":          price,
        "fuerza":         _safe(c.get("fuerza")),
        "explicacion":    c.get("explicacion", ""),
        "entry_reasons":  _safe(row.get("entry_reasons")) or [],
        "exit_reasons":   _safe(row.get("exit_reasons")) or [],
        "entry_blockers": _safe(row.get("entry_blockers")) or [],
        "trend_template": bool(row.get("trend_template", False)),
        "breakout":       bool(row.get("breakout", False)),
        "f_score":        _safe(row.get("f_score")),
        "fetched_at":     datetime.datetime.utcnow().isoformat() + "Z",
    }

    out_dir = ROOT / "data" / "live"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ticker}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    print(f"[live_analysis] {ticker} → {out_path}")
    print(f"[live_analysis] Señal: {result['signal']} | Fuerza: {result['fuerza']}")


if __name__ == "__main__":
    main()
