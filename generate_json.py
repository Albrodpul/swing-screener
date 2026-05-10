"""Convert last_run.parquet → web/public/last_run.json for the Next.js frontend."""
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
    """Convert numpy/pandas scalars to JSON-safe Python types."""
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
    parquet = ROOT / "data" / "last_run.parquet"
    output  = ROOT / "web" / "public" / "last_run.json"

    if not parquet.exists():
        print("[generate_json] No parquet found, skipping.")
        return

    df = pd.read_parquet(parquet)
    stocks = []

    for _, row in df.iterrows():
        try:
            c = humanize_card(row)
        except Exception:
            c = {}

        price = _safe(c.get("precio") or row.get("close") or row.get("price"))

        stocks.append({
            "ticker":         str(row["ticker"]),
            "name":           _safe(row.get("name")),
            "signal":         str(row["signal"]),
            "sector":         _safe(row.get("sector")),
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
    print(f"[generate_json] {len(stocks)} stocks → {output}")


if __name__ == "__main__":
    main()
