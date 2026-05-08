"""Dashboard — screener list with filters and signal overview."""
from __future__ import annotations
import sys
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from screener._ui_common import (
    inject_styles, render_bottom_nav, render_stock_card, show_add_dialog,
    SIG_COLOR,
)
from screener.pipeline import run_pipeline
from screener.portfolio import load_portfolio

# ── Styles ──────────────────────────────────────────────────────────────────
inject_styles()

# ── Add dialog (triggered by FAB or sidebar button) ─────────────────────────
if st.query_params.get("modal") == "add":
    show_add_dialog()

# ── Data ────────────────────────────────────────────────────────────────────
LAST_RUN = ROOT / "data" / "last_run.parquet"


@st.cache_data(show_spinner=False, ttl=3600)
def _load_data() -> pd.DataFrame | None:
    if LAST_RUN.exists():
        return pd.read_parquet(LAST_RUN)
    return None


def _run_pipeline(mode: str) -> None:
    tickers = (
        ["NVDA", "AAPL", "MSFT", "AMD", "INTC", "MU", "STX", "WDC", "LRCX", "SNDK"]
        if mode == "smoke"
        else None
    )
    df = run_pipeline(tickers=tickers, fund_mode="yfinance_only", verbose=False)
    df.to_parquet(LAST_RUN)
    _load_data.clear()


df = _load_data()
portfolio_data = load_portfolio()
holdings = set(portfolio_data.get("holdings", {}).keys())

# ── Sidebar (desktop) ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='font-size:1.2rem;font-weight:900;color:#e2e8f0;margin-bottom:16px'>"
        "📈 Screener</div>",
        unsafe_allow_html=True,
    )
    st.page_link("pages/dashboard.py", label="Dashboard", icon="📊")
    st.page_link("pages/portfolio.py", label="Mi Cartera", icon="💼")
    st.divider()
    if df is not None and LAST_RUN.exists():
        mtime = datetime.datetime.fromtimestamp(LAST_RUN.stat().st_mtime)
        st.caption(f"Actualizado: {mtime.strftime('%d %b, %H:%M')}")
    if st.button("⟳  Actualizar datos", use_container_width=True):
        with st.spinner("Descargando y calculando 525+ empresas..."):
            _run_pipeline("full")
        st.rerun()
    if st.button("⚡  Prueba rápida (10)", use_container_width=True):
        with st.spinner("Calculando 10 empresas..."):
            _run_pipeline("smoke")
        st.rerun()

# ── Page header ─────────────────────────────────────────────────────────────
h_l, h_r = st.columns([3, 2])
with h_l:
    st.markdown(
        "<h2 style='margin:0;font-size:1.6rem;font-weight:900'>📈 Screener</h2>",
        unsafe_allow_html=True,
    )
    if df is not None and LAST_RUN.exists():
        mtime = datetime.datetime.fromtimestamp(LAST_RUN.stat().st_mtime)
        st.caption(f"Datos del {mtime.strftime('%d %b, %H:%M')}")
    else:
        st.caption("Sin datos — pulsa Actualizar")
with h_r:
    b1, b2 = st.columns(2)
    if b1.button("⟳ Actualizar", use_container_width=True, help="Recalcula 525+ empresas"):
        with st.spinner("Calculando..."):
            _run_pipeline("full")
        st.rerun()
    if b2.button("⚡ Rápido", use_container_width=True, help="10 empresas de prueba"):
        with st.spinner("Calculando..."):
            _run_pipeline("smoke")
        st.rerun()

if df is None or df.empty:
    st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
    st.info("Sin datos aún. Pulsa **⟳ Actualizar** para comenzar.")
    render_bottom_nav("dashboard")
    st.stop()

# ── Signal summary chips ─────────────────────────────────────────────────────
n_compra  = int((df["signal"] == "COMPRA").sum())
n_observar = int((df["signal"] == "OBSERVAR").sum())
n_salida  = int((df["signal"] == "SALIDA").sum())
n_saltar  = int(df["signal"].isin(["EVITAR", "INELIGIBLE"]).sum())

st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

# KPI chips row — clickable via pills
PILL_OPTS = [
    f"🟢  Comprar ({n_compra})",
    f"👀  Vigilar ({n_observar})",
    f"🔴  Salida ({n_salida})",
    f"⚪  Saltar ({n_saltar})",
    "📋  Todo",
]
PILL_TO_SIGS = {
    PILL_OPTS[0]: ["COMPRA"],
    PILL_OPTS[1]: ["OBSERVAR"],
    PILL_OPTS[2]: ["SALIDA"],
    PILL_OPTS[3]: ["EVITAR", "INELIGIBLE"],
    PILL_OPTS[4]: ["COMPRA", "OBSERVAR", "SALIDA", "EVITAR", "INELIGIBLE"],
}

default_pill = PILL_OPTS[1] if n_compra == 0 else PILL_OPTS[0]
selected_pill = st.pills("Señal", PILL_OPTS, default=default_pill, label_visibility="collapsed")
if selected_pill is None:
    selected_pill = default_pill

# ── Search bar ───────────────────────────────────────────────────────────────
search = st.text_input(
    "Buscar",
    placeholder="🔍  Buscar empresa o ticker...",
    label_visibility="collapsed",
)

# ── Sector filter ────────────────────────────────────────────────────────────
sectors_all = sorted(df["sector"].dropna().unique().tolist())
if st.checkbox("Filtrar por sector", key="sector_toggle"):
    sectors_sel = st.multiselect(
        "Sectores",
        sectors_all,
        default=sectors_all,
        label_visibility="collapsed",
    )
    if not sectors_sel:
        sectors_sel = sectors_all
else:
    sectors_sel = sectors_all

# ── Apply filters ────────────────────────────────────────────────────────────
mask = df["signal"].isin(PILL_TO_SIGS[selected_pill])
mask &= df["sector"].isin(sectors_sel)
if search.strip():
    s = search.strip().lower()
    name_col = df["name"] if "name" in df.columns else df["ticker"]
    mask &= (
        df["ticker"].str.lower().str.contains(s, na=False)
        | name_col.astype(str).str.lower().str.contains(s, na=False)
    )

rs_score   = df["rs_rating"].fillna(0) if "rs_rating" in df.columns else 0
fund_score = df["fund_composite"].fillna(0) if "fund_composite" in df.columns else 0
score = rs_score * 0.5 + fund_score * 0.5
shown = (
    df[mask]
    .assign(_score=score[mask])
    .sort_values("_score", ascending=False)
    .drop(columns="_score")
)

st.caption(f"{len(shown)} empresa{'s' if len(shown) != 1 else ''} · {len(df)} en total")

if shown.empty:
    st.info("Ninguna empresa cumple los filtros actuales.")
    render_bottom_nav("dashboard")
    st.stop()

# ── Stock cards ──────────────────────────────────────────────────────────────
for _, row in shown.head(50).iterrows():
    if render_stock_card(
        row,
        in_portfolio=row["ticker"] in holdings,
        show_chart=False,
        key_prefix="dash_",
    ):
        st.rerun()

if len(shown) > 50:
    st.caption(f"Mostrando 50 de {len(shown)}. Usa el buscador para afinar.")

# ── Bottom nav ───────────────────────────────────────────────────────────────
render_bottom_nav("dashboard")
