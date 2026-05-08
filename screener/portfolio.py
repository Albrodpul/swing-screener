"""Portfolio persistence.

Modo local  — sin secrets: lee/escribe data/portfolio.json directamente.
Modo GitHub — con secrets GITHUB_PAT + GITHUB_REPO: sincroniza vía API
              (usado en Streamlit Cloud para persistir entre sesiones).
"""
from __future__ import annotations
import base64
import json
import requests
from datetime import date
from pathlib import Path

import streamlit as st

PORTFOLIO_FILE = "data/portfolio.json"
_LOCAL_PATH = Path(__file__).resolve().parents[1] / PORTFOLIO_FILE


def _cfg() -> tuple[str, str]:
    try:
        pat  = st.secrets.get("GITHUB_PAT", "")
        repo = st.secrets.get("GITHUB_REPO", "")
    except Exception:
        pat, repo = "", ""
    return pat, repo


def _use_github() -> bool:
    pat, repo = _cfg()
    return bool(pat and repo)


def portfolio_enabled() -> bool:
    return True  # siempre activo; usa local o GitHub según entorno


@st.cache_data(ttl=60, show_spinner=False)
def load_portfolio() -> dict:
    """{'holdings': {'NVDA': {'added': '2026-05-08'}, ...}}"""
    if _use_github():
        pat, repo = _cfg()
        try:
            r = requests.get(
                f"https://api.github.com/repos/{repo}/contents/{PORTFOLIO_FILE}",
                headers={"Authorization": f"token {pat}",
                         "Accept": "application/vnd.github.v3+json"},
                timeout=10,
            )
            if r.status_code == 200:
                raw = base64.b64decode(r.json()["content"]).decode()
                return json.loads(raw)
        except Exception:
            pass
        return {"holdings": {}}

    # Modo local
    if _LOCAL_PATH.exists():
        try:
            return json.loads(_LOCAL_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"holdings": {}}


def save_portfolio(data: dict) -> bool:
    if _use_github():
        pat, repo = _cfg()
        try:
            headers = {"Authorization": f"token {pat}",
                       "Accept": "application/vnd.github.v3+json"}
            url = f"https://api.github.com/repos/{repo}/contents/{PORTFOLIO_FILE}"
            r   = requests.get(url, headers=headers, timeout=10)
            sha = r.json().get("sha") if r.status_code == 200 else None
            content = base64.b64encode(
                json.dumps(data, indent=2, ensure_ascii=False).encode()
            ).decode()
            payload: dict = {"message": "update: cartera", "content": content}
            if sha:
                payload["sha"] = sha
            resp = requests.put(url, headers=headers, json=payload, timeout=10)
            if resp.status_code in (200, 201):
                load_portfolio.clear()
                return True
        except Exception:
            pass
        return False

    # Modo local
    try:
        _LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        _LOCAL_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        load_portfolio.clear()
        return True
    except Exception:
        return False


def add_ticker(ticker: str) -> None:
    data = load_portfolio()
    data.setdefault("holdings", {})[ticker] = {"added": str(date.today())}
    save_portfolio(data)


def remove_ticker(ticker: str) -> None:
    data = load_portfolio()
    data.setdefault("holdings", {}).pop(ticker, None)
    save_portfolio(data)
