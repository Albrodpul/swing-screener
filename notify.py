"""Notificaciones Telegram tras el pipeline.

Variables de entorno necesarias (GitHub Secrets):
  TELEGRAM_BOT_TOKEN  — token del bot
  TELEGRAM_CHAT_ID    — tu chat_id
  GITHUB_TOKEN        — provisto automáticamente por Actions
  GITHUB_REPOSITORY   — provisto automáticamente por Actions
"""
from __future__ import annotations
import base64
import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID", "")
GH_TOKEN   = os.environ.get("GITHUB_TOKEN", "")
GH_REPO    = os.environ.get("GITHUB_REPOSITORY", "")

SIG_EMOJI = {"COMPRA": "🟢", "OBSERVAR": "👀", "SALIDA": "🔴",
             "EVITAR": "⚠️", "INELIGIBLE": "⚫"}


def send(text: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        print(f"[notify] {text}\n")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"[notify] Error enviando mensaje: {e}")


def _load_portfolio() -> list[str]:
    if not GH_TOKEN or not GH_REPO:
        return []
    try:
        r = requests.get(
            f"https://api.github.com/repos/{GH_REPO}/contents/data/portfolio.json",
            headers={"Authorization": f"token {GH_TOKEN}",
                     "Accept": "application/vnd.github.v3+json"},
            timeout=10,
        )
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode()
            data = json.loads(raw)
            return list(data.get("holdings", {}).keys())
    except Exception:
        pass
    return []


def _as_list(x) -> list:
    if x is None:
        return []
    if hasattr(x, "tolist"):
        return x.tolist()
    if isinstance(x, list):
        return x
    return []


def main() -> None:
    parquet = ROOT / "data" / "last_run.parquet"
    if not parquet.exists():
        send("⚠️ El pipeline terminó pero no generó datos.")
        return

    df = pd.read_parquet(parquet)
    portfolio = _load_portfolio()

    # ── Oportunidades de compra ─────────────────────────────────────────────
    compras = df[df["signal"] == "COMPRA"]
    if compras.empty:
        send("📊 Pipeline completado — hoy <b>sin oportunidades de compra</b> claras.\n"
             f"Universo: {len(df)} empresas.")
    else:
        lines = [f"🟢 <b>Oportunidades de compra hoy</b> ({len(compras)})\n"]
        for _, r in compras.head(8).iterrows():
            name = r.get("name") or r["ticker"]
            rs   = r.get("rs_rating")
            rs_s = f"  RS {rs:.0f}/100" if rs else ""
            lines.append(f"• <b>{r['ticker']}</b> — {name}{rs_s}")
            reasons = _as_list(r.get("entry_reasons"))
            if reasons:
                lines.append(f"  <i>{reasons[0]}</i>")
        send("\n".join(lines))

    # ── Estado de cartera ───────────────────────────────────────────────────
    if not portfolio:
        return

    port_df = df[df["ticker"].isin(portfolio)]
    missing  = [t for t in portfolio if t not in df["ticker"].values]

    lines = ["💼 <b>Tu cartera hoy</b>\n"]
    for _, r in port_df.iterrows():
        emoji = SIG_EMOJI.get(r["signal"], "❓")
        rs    = r.get("rs_rating")
        rs_s  = f"  RS {rs:.0f}" if rs else ""
        lines.append(f"{emoji} <b>{r['ticker']}</b>{rs_s} — {r['signal']}")
        if r["signal"] == "SALIDA":
            exits = _as_list(r.get("exit_reasons"))
            if exits:
                lines.append(f"  ↳ {exits[0]}")
        elif r["signal"] == "COMPRA":
            entries = _as_list(r.get("entry_reasons"))
            if entries:
                lines.append(f"  ↳ {entries[0]}")
    for t in missing:
        lines.append(f"❓ <b>{t}</b> — sin datos hoy")

    send("\n".join(lines))


if __name__ == "__main__":
    main()
