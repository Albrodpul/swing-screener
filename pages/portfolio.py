"""Portfolio page — detailed view of owned stocks."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from screener._ui_common import (
    inject_styles, render_bottom_nav, render_stock_card, show_add_dialog,
    SIG_COLOR, SIG_EMOJI, SIG_LABEL,
)
from screener.portfolio import load_portfolio, remove_ticker

# ── Styles ──────────────────────────────────────────────────────────────────
inject_styles()

# ── Add dialog ───────────────────────────────────────────────────────────────
if st.query_params.get("modal") == "add":
    show_add_dialog()

# ── Data ────────────────────────────────────────────────────────────────────
LAST_RUN = ROOT / "data" / "last_run.parquet"


@st.cache_data(show_spinner=False, ttl=3600)
def _load_screener() -> pd.DataFrame | None:
    if LAST_RUN.exists():
        return pd.read_parquet(LAST_RUN)
    return None


df = _load_screener()
portfolio_data = load_portfolio()
holdings = set(portfolio_data.get("holdings", {}).keys())
holdings_meta = portfolio_data.get("holdings", {})

# ── Sidebar (desktop) ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='font-size:1.2rem;font-weight:900;color:#e2e8f0;margin-bottom:16px'>"
        "📈 Screener</div>",
        unsafe_allow_html=True,
    )
    st.page_link("pages/dashboard.py", label="Dashboard", icon="📊")
    st.page_link("pages/portfolio.py", label="Mi Cartera", icon="💼")

# ── Page header ──────────────────────────────────────────────────────────────
h_l, h_r = st.columns([3, 1])
with h_l:
    count = len(holdings)
    st.markdown(
        "<h2 style='margin:0;font-size:1.6rem;font-weight:900'>💼 Mi Cartera</h2>",
        unsafe_allow_html=True,
    )
    if count:
        st.caption(f"{count} posición{'es' if count != 1 else ''} en seguimiento")
    else:
        st.caption("Sin posiciones activas")
with h_r:
    if st.button("＋ Añadir", type="primary", use_container_width=True):
        st.query_params["modal"] = "add"
        st.rerun()

st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)

# ── Empty state ───────────────────────────────────────────────────────────────
if not holdings:
    st.markdown(
        """
<div style='text-align:center;padding:4rem 1rem 3rem;'>
  <div style='font-size:3.5rem;line-height:1;margin-bottom:1rem'>💼</div>
  <div style='font-size:1.15rem;font-weight:800;color:#94a3b8;margin-bottom:0.5rem'>
    Cartera vacía
  </div>
  <div style='font-size:0.9rem;color:#64748b;max-width:280px;margin:0 auto;line-height:1.6'>
    Añade acciones desde el Dashboard pulsando
    <strong style='color:#94a3b8'>＋ Añadir a mi cartera</strong>
    en cada tarjeta, o usa el botón + de abajo.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    render_bottom_nav("portfolio")
    st.stop()

# ── Summary chips row ─────────────────────────────────────────────────────────
if df is not None and not df.empty:
    port_df = df[df["ticker"].isin(holdings)]
    if not port_df.empty:
        sig_counts: dict[str, int] = port_df["signal"].value_counts().to_dict()
        chips = ""
        for sig, n in sorted(sig_counts.items(), key=lambda x: ["COMPRA","OBSERVAR","SALIDA","EVITAR","INELIGIBLE"].index(x[0]) if x[0] in ["COMPRA","OBSERVAR","SALIDA","EVITAR","INELIGIBLE"] else 99):
            col = SIG_COLOR.get(sig, "#6b7280")
            emoji = SIG_EMOJI.get(sig, "❓")
            lbl = SIG_LABEL.get(sig, sig)
            chips += (
                f"<span style='background:{col}22;border:1px solid {col};color:{col};"
                f"border-radius:20px;padding:4px 14px;font-weight:700;font-size:0.82rem;"
                f"display:inline-flex;align-items:center;gap:4px'>"
                f"{emoji} {lbl} ({n})</span>"
            )
        st.markdown(
            f"<div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px'>{chips}</div>",
            unsafe_allow_html=True,
        )

# ── No market data ────────────────────────────────────────────────────────────
if df is None or df.empty:
    st.warning("Sin datos de mercado. Ve al **Dashboard** y pulsa **⟳ Actualizar**.")
    for tk in sorted(holdings):
        added = holdings_meta.get(tk, {}).get("added", "")
        added_str = f" · añadido {added}" if added else ""
        st.markdown(
            f"<div style='background:#132033;border:1px solid #1e3a52;border-radius:12px;"
            f"padding:16px 20px;margin-bottom:8px;display:flex;align-items:center;gap:12px'>"
            f"<span style='font-size:1.1rem;font-weight:900;color:#e2e8f0'>{tk}</span>"
            f"<span style='color:#64748b;font-size:0.82rem'>{added_str}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    render_bottom_nav("portfolio")
    st.stop()

# ── Portfolio cards ───────────────────────────────────────────────────────────
known   = [tk for tk in sorted(holdings) if tk in df["ticker"].values]
missing = [tk for tk in sorted(holdings) if tk not in df["ticker"].values]

for tk in known:
    row = df[df["ticker"] == tk].iloc[0]
    if render_stock_card(row, in_portfolio=True, show_chart=True, key_prefix="port_"):
        st.rerun()

if missing:
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    for tk in missing:
        added = holdings_meta.get(tk, {}).get("added", "")
        st.markdown(
            f"<div style='background:#132033;border:1px solid #1e3a52;border-radius:12px;"
            f"padding:14px 18px;margin-bottom:8px;opacity:0.65;display:flex;"
            f"align-items:center;gap:12px'>"
            f"<span style='font-size:1.1rem;font-weight:900;color:#94a3b8'>❓ {tk}</span>"
            f"<span style='color:#64748b;font-size:0.82rem'>Sin datos hoy</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

# ── Bottom nav ────────────────────────────────────────────────────────────────
render_bottom_nav("portfolio")
