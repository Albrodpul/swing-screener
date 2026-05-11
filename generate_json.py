"""Merge last_run_us.parquet + last_run_eu.parquet → web/public/last_run.json."""
from __future__ import annotations
import json
import math
import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from screener.plain_language import humanize_card


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


def _load_parquet(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        return pd.read_parquet(path)
    except Exception as e:
        print(f"[generate_json] Error leyendo {path}: {e}")
        return None


def main() -> None:
    data_dir = ROOT / "data"
    output   = ROOT / "web" / "public" / "last_run.json"

    frames = []
    for name in ("last_run_us.parquet", "last_run_eu.parquet"):
        df = _load_parquet(data_dir / name)
        if df is not None:
            frames.append(df)
            print(f"[generate_json] {name}: {len(df)} tickers")

    if not frames:
        print("[generate_json] No parquets found, skipping.")
        return

    df = pd.concat(frames, ignore_index=True)
    stocks = []

    for _, row in df.iterrows():
        try:
            c = humanize_card(row)
        except Exception:
            c = {}

        price = _safe(c.get("precio") or row.get("close") or row.get("price"))

        stocks.append({
            "ticker":         str(row["ticker"]),
            "market":         str(row.get("market", "US")),
            "name":           _safe(row.get("name")),
            "signal":         str(row["signal"]),
            "sector":         _safe(row.get("sector")),
            "industry":       _safe(row.get("industry")),
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
        })

    data = {
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "count":      len(stocks),
        "stocks":     stocks,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    us_n = sum(1 for s in stocks if s["market"] == "US")
    eu_n = sum(1 for s in stocks if s["market"] == "EU")
    print(f"[generate_json] {len(stocks)} stocks (US: {us_n}, EU: {eu_n}) → {output}")


if __name__ == "__main__":
    main()
