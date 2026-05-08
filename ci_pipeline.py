"""Script de CI: ejecuta el pipeline y guarda last_run.parquet."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from screener.pipeline import run_pipeline

print("Iniciando pipeline...")
df = run_pipeline(fund_mode="yfinance_only", verbose=True)

out = ROOT / "data" / "last_run.parquet"
out.parent.mkdir(exist_ok=True)
df.to_parquet(out)

signals = df["signal"].value_counts().to_dict()
print(f"\nResultado: {len(df)} tickers")
for sig, n in sorted(signals.items()):
    print(f"  {sig}: {n}")
