"""Script de CI: ejecuta el pipeline para US o EU y guarda el parquet correspondiente."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from screener.pipeline import run_pipeline
from data.universe import build_universe, build_eu_universe

MARKET_CONFIG = {
    "us": {
        "build_fn": build_universe,
        "spy": "SPY",
        "qqq": "QQQ",
        "out": ROOT / "data" / "last_run_us.parquet",
    },
    "eu": {
        "build_fn": build_eu_universe,
        "spy": "EZU",   # iShares MSCI Eurozone ETF
        "qqq": None,
        "out": ROOT / "data" / "last_run_eu.parquet",
    },
}

parser = argparse.ArgumentParser()
parser.add_argument("--market", choices=["us", "eu"], default="us")
args = parser.parse_args()

cfg = MARKET_CONFIG[args.market]
universe = cfg["build_fn"]()

print(f"Iniciando pipeline [{args.market.upper()}]... {len(universe)} tickers")
df = run_pipeline(
    tickers=universe,
    fund_mode="yfinance_only",
    verbose=True,
    market=args.market.upper(),
    spy_ticker=cfg["spy"],
    qqq_ticker=cfg["qqq"],
)

out = cfg["out"]
out.parent.mkdir(exist_ok=True)
df.to_parquet(out)

signals = df["signal"].value_counts().to_dict()
print(f"\nResultado [{args.market.upper()}]: {len(df)} tickers")
for sig, n in sorted(signals.items()):
    print(f"  {sig}: {n}")
