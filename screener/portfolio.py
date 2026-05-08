"""Portfolio persistence: lee y escribe data/portfolio.json vía GitHub API."""
from __future__ import annotations
import base64
import json
import requests
from datetime import date

import streamlit as st


PORTFOLIO_FILE = "data/portfolio.json"


def _cfg() -> tuple[str, str]:
    try:
        pat  = st.secrets.get("GITHUB_PAT", "")
        repo = st.secrets.get("GITHUB_REPO", "")
    except Exception:
        pat, repo = "", ""
    return pat, repo


def portfolio_enabled() -> bool:
    pat, repo = _cfg()
    return bool(pat and repo)


@st.cache_data(ttl=60, show_spinner=False)
def load_portfolio() -> dict:
    """{'holdings': {'NVDA': {'added': '2026-05-08'}, ...}}"""
    pat, repo = _cfg()
    if not pat or not repo:
        return {"holdings": {}}
    try:
        r = requests.get(
            f"https://api.github.com/repos/{repo}/contents/{PORTFOLIO_FILE}",
            headers={"Authorization": f"token {pat}", "Accept": "application/vnd.github.v3+json"},
            timeout=10,
        )
        if r.status_code == 200:
            raw = base64.b64decode(r.json()["content"]).decode()
            return json.loads(raw)
    except Exception:
        pass
    return {"holdings": {}}


def save_portfolio(data: dict) -> bool:
    pat, repo = _cfg()
    if not pat or not repo:
        return False
    try:
        headers = {"Authorization": f"token {pat}", "Accept": "application/vnd.github.v3+json"}
        url = f"https://api.github.com/repos/{repo}/contents/{PORTFOLIO_FILE}"
        r = requests.get(url, headers=headers, timeout=10)
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


def add_ticker(ticker: str) -> None:
    data = load_portfolio()
    data.setdefault("holdings", {})[ticker] = {"added": str(date.today())}
    save_portfolio(data)


def remove_ticker(ticker: str) -> None:
    data = load_portfolio()
    data.setdefault("holdings", {}).pop(ticker, None)
    save_portfolio(data)
