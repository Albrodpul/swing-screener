"""Shared UI: CSS, constants, card renderer, bottom nav, add dialog."""
from __future__ import annotations
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── Constants ───────────────────────────────────────────────────────────────
SIG_COLOR = {
    "COMPRA":     "#10b981",
    "OBSERVAR":   "#f59e0b",
    "SALIDA":     "#ef4444",
    "EVITAR":     "#6b7280",
    "INELIGIBLE": "#475569",
}
SIG_EMOJI = {
    "COMPRA":     "🟢",
    "OBSERVAR":   "👀",
    "SALIDA":     "🔴",
    "EVITAR":     "⚠️",
    "INELIGIBLE": "⚫",
}
SIG_LABEL = {
    "COMPRA":     "Comprar",
    "OBSERVAR":   "Vigilar",
    "SALIDA":     "Salida",
    "EVITAR":     "Evitar",
    "INELIGIBLE": "No apto",
}

# ── CSS ─────────────────────────────────────────────────────────────────────
_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap');

:root {
  --bg: #0b1622;
  --card: #132033;
  --card-hover: #16273f;
  --deep: #0d1e30;
  --border: #1e3a52;
  --border-hover: #2d4a6a;
  --primary: #2d7eb5;
  --primary-hover: #3a8fc7;
  --primary-glow: rgba(45,126,181,0.25);
  --text: #e2e8f0;
  --muted: #94a3b8;
  --subtle: #64748b;
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  --nav-h: 64px;
  --sidebar-w: 220px;
}

/* ── Reset Streamlit chrome ─────────────────────────────── */
html, body, [data-testid="stAppViewContainer"], .stApp {
  background-color: var(--bg) !important;
  font-family: 'Nunito', sans-serif !important;
}
[data-testid="stMain"] { background-color: var(--bg) !important; }
#MainMenu, footer,
[data-testid="stToolbar"],
[data-testid="stDeployButton"],
[data-testid="stDecoration"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; height: 0 !important; }
[data-testid="stSidebarNav"] { display: none !important; }
/* Keep collapsedControl visible so user can reopen sidebar */

/* ── Main container ─────────────────────────────────────── */
.block-container {
  padding: 1.5rem 1.5rem 2rem !important;
  max-width: 920px !important;
  margin: 0 auto !important;
}

/* ── Sidebar ────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: #0a1520 !important;
  border-right: 1px solid var(--border) !important;
  min-width: var(--sidebar-w) !important;
  max-width: var(--sidebar-w) !important;
}
[data-testid="stSidebarContent"] { padding: 1.25rem 0.875rem !important; }

/* Page links in sidebar */
[data-testid="stPageLink"] a {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  padding: 9px 12px !important;
  border-radius: 9px !important;
  color: var(--muted) !important;
  font-weight: 700 !important;
  font-size: 0.9rem !important;
  text-decoration: none !important;
  transition: background 0.15s, color 0.15s !important;
  margin-bottom: 2px !important;
}
[data-testid="stPageLink"] a:hover {
  background: rgba(45,126,181,0.12) !important;
  color: var(--text) !important;
}
[data-testid="stPageLink"][aria-current="page"] a,
[data-testid="stPageLink"] a[aria-current="page"] {
  background: rgba(45,126,181,0.18) !important;
  color: var(--primary) !important;
}

/* ── Typography ─────────────────────────────────────────── */
h1,h2,h3,h4,p,label,span,div,
[data-testid="stMarkdownContainer"] {
  color: var(--text) !important;
  font-family: 'Nunito', sans-serif !important;
}
.stCaption,
[data-testid="stCaptionContainer"] { color: var(--muted) !important; }

/* ── Cards ──────────────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  margin-bottom: 10px !important;
  overflow: hidden !important;
  transition: background 0.15s, border-color 0.15s, box-shadow 0.15s !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  background: var(--card-hover) !important;
  border-color: var(--border-hover) !important;
  box-shadow: 0 4px 20px rgba(0,0,0,0.2) !important;
}

/* ── Search input ───────────────────────────────────────── */
[data-testid="stTextInput"] input {
  background: var(--card) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: 10px !important;
  color: var(--text) !important;
  font-family: 'Nunito', sans-serif !important;
  font-size: 0.95rem !important;
  padding: 10px 16px !important;
  transition: border-color 0.15s, box-shadow 0.15s !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px var(--primary-glow) !important;
  outline: none !important;
}
[data-testid="stTextInput"] label { display: none !important; }

/* ── Signal pills ───────────────────────────────────────── */
[data-testid="stPillsButton"] button {
  border-radius: 20px !important;
  font-weight: 700 !important;
  font-size: 0.8rem !important;
  font-family: 'Nunito', sans-serif !important;
  border: 1.5px solid var(--border) !important;
  background: var(--deep) !important;
  color: var(--muted) !important;
  transition: all .15s !important;
  padding: 5px 14px !important;
}
[data-testid="stPillsButton"] button[aria-checked="true"] {
  background: var(--primary) !important;
  border-color: var(--primary) !important;
  color: #fff !important;
  box-shadow: 0 2px 8px var(--primary-glow) !important;
}

/* ── Buttons ────────────────────────────────────────────── */
[data-testid="baseButton-secondary"] {
  background: rgba(19,32,51,0.8) !important;
  border: 1px solid var(--border) !important;
  color: var(--muted) !important;
  border-radius: 8px !important;
  font-family: 'Nunito', sans-serif !important;
  font-weight: 600 !important;
  transition: all .15s !important;
}
[data-testid="baseButton-secondary"]:hover {
  background: #1e3a52 !important;
  border-color: var(--primary) !important;
  color: var(--text) !important;
}
[data-testid="baseButton-primary"] {
  background: var(--primary) !important;
  border: none !important;
  border-radius: 8px !important;
  font-family: 'Nunito', sans-serif !important;
  font-weight: 700 !important;
  transition: background .15s !important;
}
[data-testid="baseButton-primary"]:hover {
  background: var(--primary-hover) !important;
}

/* ── Checkboxes ─────────────────────────────────────────── */
[data-testid="stCheckbox"] label {
  color: var(--muted) !important;
  font-size: 0.85rem !important;
  font-weight: 600 !important;
}

/* ── Progress bars ──────────────────────────────────────── */
[data-testid="stProgressBar"] > div {
  background: var(--border) !important;
  border-radius: 6px !important;
}
[data-testid="stProgressBar"] > div > div {
  border-radius: 6px !important;
}
[data-testid="stProgressText"] {
  color: var(--muted) !important;
  font-size: 0.78rem !important;
}

/* ── Metrics ────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: var(--deep) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  padding: 10px 14px !important;
}
[data-testid="stMetricValue"] {
  color: var(--text) !important;
  font-weight: 800 !important;
}
[data-testid="stMetricLabel"] {
  color: var(--subtle) !important;
  font-size: 0.75rem !important;
}

/* ── Divider ────────────────────────────────────────────── */
hr { border-color: var(--border) !important; margin: 0.5rem 0 !important; }

/* ── Spinner ────────────────────────────────────────────── */
[data-testid="stSpinner"] { color: var(--primary) !important; }

/* ── Multiselect ────────────────────────────────────────── */
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
  background: var(--card) !important;
  border-color: var(--border) !important;
  border-radius: 10px !important;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] {
  background: rgba(45,126,181,0.2) !important;
  border-color: var(--primary) !important;
  border-radius: 8px !important;
}

/* ── Dialog ─────────────────────────────────────────────── */
[data-testid="stModal"] > div {
  background: #0f1a28 !important;
  border: 1px solid var(--border) !important;
  border-radius: 16px !important;
}

/* ── Info/Warning boxes ─────────────────────────────────── */
[data-testid="stAlert"] {
  border-radius: 10px !important;
  border-color: var(--border) !important;
}

/* ── Bottom Navigation (mobile) ─────────────────────────── */
.bnav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: var(--nav-h);
  background: #07111c;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-around;
  z-index: 9999;
  padding-bottom: env(safe-area-inset-bottom, 0);
}
.bnav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  color: var(--subtle);
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.6rem;
  font-weight: 700;
  font-family: 'Nunito', sans-serif;
  padding: 4px 28px;
  border-radius: 8px;
  transition: color .15s;
  line-height: 1;
}
.bnav-item.active { color: var(--primary) !important; }
.bnav-item svg { width: 22px; height: 22px; margin-bottom: 1px; }
.bnav-fab {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--primary);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: -16px;
  box-shadow: 0 6px 20px rgba(45,126,181,0.55);
  transition: background .15s, transform .12s;
  flex-shrink: 0;
}
.bnav-fab:hover { background: var(--primary-hover); transform: scale(1.07); }
.bnav-fab svg { width: 22px; height: 22px; color: #fff; stroke: #fff; }

/* ── Desktop FAB ────────────────────────────────────────── */
.dfab {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--primary);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 28px rgba(45,126,181,0.45);
  color: white;
  font-size: 2rem;
  font-weight: 300;
  line-height: 1;
  z-index: 999;
  transition: background .15s, transform .12s;
}
.dfab:hover { background: var(--primary-hover); transform: scale(1.07); }

/* ── Responsive breakpoints ─────────────────────────────── */
@media (max-width: 768px) {
  /* Sidebar stays as Streamlit's native slide-over on mobile */
  .dfab { display: none !important; }
  .block-container { padding-bottom: 80px !important; }
}
@media (min-width: 769px) {
  .bnav { display: none !important; }
  /* Force sidebar always visible on desktop regardless of Streamlit's JS state */
  section[data-testid="stSidebar"] {
    transform: translateX(0) !important;
    display: flex !important;
    visibility: visible !important;
    width: var(--sidebar-w) !important;
    min-width: var(--sidebar-w) !important;
  }
}
"""


def inject_styles() -> None:
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


# ── Helpers ─────────────────────────────────────────────────────────────────
def _as_list(x) -> list:
    if x is None:
        return []
    if hasattr(x, "tolist"):
        return x.tolist()
    if isinstance(x, list):
        return x
    return []


def fuerza_color(v) -> str:
    if v is None or pd.isna(v):
        return "#6b7280"
    if v >= 75:
        return "#10b981"
    if v >= 50:
        return "#f59e0b"
    return "#ef4444"


# ── Add ticker dialog ────────────────────────────────────────────────────────
@st.dialog("Añadir a cartera", width="small")
def show_add_dialog() -> None:
    from screener.portfolio import add_ticker

    st.markdown(
        "<p style='color:#94a3b8;font-size:0.9rem;margin-bottom:12px'>"
        "Ingresa el ticker de la acción (símbolo bursátil en inglés).</p>",
        unsafe_allow_html=True,
    )
    ticker_in = st.text_input(
        "Ticker",
        placeholder="NVDA, AAPL, TSM, MU...",
        label_visibility="collapsed",
    ).strip().upper()

    c1, c2 = st.columns(2)
    if c1.button("Añadir", type="primary", use_container_width=True):
        if ticker_in:
            add_ticker(ticker_in)
            if "modal" in st.query_params:
                del st.query_params["modal"]
            st.rerun()
        else:
            st.error("Escribe un ticker primero")
    if c2.button("Cancelar", use_container_width=True):
        if "modal" in st.query_params:
            del st.query_params["modal"]
        st.rerun()


# ── Bottom nav ───────────────────────────────────────────────────────────────
_ICON_DASHBOARD = """<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
  <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"/>
</svg>"""

_ICON_PORTFOLIO = """<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
  <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0M12 12.75h.008v.008H12v-.008z"/>
</svg>"""

_ICON_PLUS = """<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor">
  <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15"/>
</svg>"""


def render_bottom_nav(current: str = "dashboard") -> None:
    da = "active" if current == "dashboard" else ""
    pa = "active" if current == "portfolio" else ""
    # Use window.parent.location.href to navigate within the same tab (not iframe).
    # For the FAB, preserve current path so it works on both pages.
    st.markdown(
        f"""
<div class="bnav">
  <button class="bnav-item {da}" onclick="window.parent.location.href='/'">
    {_ICON_DASHBOARD}
    <span>Dashboard</span>
  </button>
  <button class="bnav-fab" onclick="window.parent.location.href=window.parent.location.pathname+'?modal=add'">
    {_ICON_PLUS}
  </button>
  <button class="bnav-item {pa}" onclick="window.parent.location.href='/portfolio'">
    {_ICON_PORTFOLIO}
    <span>Cartera</span>
  </button>
</div>
<button class="dfab" onclick="window.parent.location.href=window.parent.location.pathname+'?modal=add'">+</button>
""",
        unsafe_allow_html=True,
    )


# ── Chart renderer ───────────────────────────────────────────────────────────
def render_chart(ticker: str) -> None:
    import plotly.graph_objects as go
    from data.fetch_prices import get_prices
    from technicals.indicators import sma, atr
    from technicals.breakout import detect_breakout

    try:
        prices = get_prices(ticker)
        tail = prices.tail(252)
        fig = go.Figure(data=[go.Candlestick(
            x=tail.index,
            open=tail["open"], high=tail["high"],
            low=tail["low"], close=tail["close"],
            name=ticker,
            increasing_line_color="#10b981",
            decreasing_line_color="#ef4444",
        )])
        for n, color in [(50, "#3b82f6"), (150, "#f97316"), (200, "#ef4444")]:
            s_line = sma(prices["close"], n).reindex(tail.index)
            fig.add_trace(go.Scatter(
                x=tail.index, y=s_line, name=f"SMA{n}",
                line=dict(color=color, width=1.2),
            ))
        bk = detect_breakout(prices)
        pivot = bk.get("pivot") if bk else None
        if pivot:
            fig.add_hline(
                y=pivot, line=dict(color="#10b981", dash="dash"),
                annotation_text=f"Techo {pivot:.2f}",
                annotation_position="right",
            )
        hi22 = prices["high"].rolling(22, min_periods=22).max()
        chand = (hi22 - 3 * atr(prices, 22)).reindex(tail.index)
        fig.add_trace(go.Scatter(
            x=tail.index, y=chand, name="Stop",
            line=dict(color="#6b7280", dash="dot", width=1),
        ))
        fig.update_layout(
            paper_bgcolor="#0d1e30", plot_bgcolor="#0d1e30",
            font=dict(color="#94a3b8", family="Nunito"),
            title=dict(text=f"{ticker} — 12 meses", font=dict(color="#e2e8f0")),
            height=400, xaxis_rangeslider_visible=False,
            hovermode="x unified",
            margin=dict(l=4, r=4, t=36, b=4),
            legend=dict(orientation="h", y=-0.1, font=dict(size=10, color="#94a3b8")),
            xaxis=dict(gridcolor="#1e3a52", color="#64748b"),
            yaxis=dict(gridcolor="#1e3a52", color="#64748b"),
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.caption(f"Gráfico no disponible: {e}")


# ── Stock card renderer ──────────────────────────────────────────────────────
def render_stock_card(
    row,
    in_portfolio: bool,
    show_chart: bool = False,
    key_prefix: str = "",
) -> bool:
    """Render a stock card. Returns True if portfolio was modified (caller should rerun)."""
    from screener.plain_language import humanize_card
    from screener.portfolio import add_ticker, remove_ticker

    c = humanize_card(row)
    ticker = c["ticker"]
    fuerza = c["fuerza"]
    fcolor = fuerza_color(fuerza)
    sig_col = SIG_COLOR.get(row["signal"], "#6b7280")
    label = SIG_LABEL.get(row["signal"], row["signal"])

    with st.container(border=True):
        # Signal color top border
        st.markdown(
            f"<div style='height:4px;background:{sig_col};"
            f"margin:-1px -1px 12px -1px;border-radius:13px 13px 0 0'></div>",
            unsafe_allow_html=True,
        )

        # Header: ticker + name | fuerza score
        top_l, top_r = st.columns([3, 1])
        with top_l:
            name = row.get("name") or ticker
            port_badge = '<span style="color:#f59e0b;margin-left:6px;font-size:1rem">💼</span>' if in_portfolio else ""
            st.markdown(
                f"<div style='line-height:1.25'>"
                f"<span style='font-size:1.15rem;font-weight:900;color:#e2e8f0'>{ticker}</span>"
                f"{port_badge}"
                f"<br><span style='font-size:0.82rem;color:#94a3b8'>{name}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with top_r:
            fuerza_str = "—" if fuerza is None else f"{fuerza:.0f}"
            st.markdown(
                f"<div style='text-align:right;line-height:1.2'>"
                f"<span style='font-size:0.68rem;color:#64748b;display:block;margin-bottom:1px'>Fuerza</span>"
                f"<span style='font-size:1.5rem;font-weight:900;color:{fcolor}'>{fuerza_str}</span>"
                f"<span style='font-size:0.78rem;color:#64748b'>/100</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Signal badge + sector + price
        price = c["precio"]
        price_str = f" · ${price:.2f}" if price else ""
        sector_str = c.get("sector") or ""
        st.markdown(
            f"<div style='margin:6px 0 8px'>"
            f"<span style='background:{sig_col}22;border:1px solid {sig_col};color:{sig_col};"
            f"border-radius:12px;padding:2px 10px;font-size:0.77rem;font-weight:700'>{label}</span>"
            f"<span style='color:#64748b;font-size:0.77rem;margin-left:8px'>"
            f"{sector_str}{price_str}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Explanation
        st.markdown(
            f"<p style='color:#cbd5e1;font-size:0.87rem;margin:0 0 10px;line-height:1.55'>"
            f"{c['explicacion']}</p>",
            unsafe_allow_html=True,
        )

        # Progress bars (calidad + impulso)
        if c.get("calidad") is not None:
            st.progress(min(int(c["calidad"]), 100), text=f"Salud empresa: {c['calidad']:.0f}/100")
        if c.get("impulso") is not None:
            st.progress(min(int(c["impulso"]), 100), text=f"Mejor que el {c['impulso']:.0f}% del mercado")

        # Portfolio action button
        modified = False
        if in_portfolio:
            if st.button(
                f"✕  Quitar {ticker} de mi cartera",
                key=f"{key_prefix}rm_{ticker}",
                type="primary",
                use_container_width=True,
            ):
                remove_ticker(ticker)
                modified = True
        else:
            if st.button(
                f"＋  Añadir {ticker} a mi cartera",
                key=f"{key_prefix}add_{ticker}",
                use_container_width=True,
            ):
                add_ticker(ticker)
                modified = True

        # Technical analysis toggle (dashboard) or always shown (portfolio)
        if show_chart:
            _render_technical_detail(row, c, ticker)
            render_chart(ticker)
        else:
            if st.checkbox("Ver análisis técnico y gráfico", key=f"{key_prefix}tech_{ticker}"):
                _render_technical_detail(row, c, ticker)
                render_chart(ticker)

    return modified


def _render_technical_detail(row, c: dict, ticker: str) -> None:
    t = c.get("tecnico", {})
    rs = t.get("rs_rating")
    fs = t.get("f_score")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("RS", f"{rs:.0f}" if rs else "—")
    m2.metric("Stage 2", "✅" if t.get("trend_template") else "❌")
    m3.metric("Breakout", "✅" if t.get("breakout") else "❌")
    m4.metric("Piotroski", f"{fs}/9" if fs is not None else "—")

    for lbl, items in [
        ("A favor", _as_list(t.get("entry_reasons"))),
        ("Bloqueadores", _as_list(t.get("entry_blockers"))),
        ("Avisos de salida", _as_list(t.get("exit_reasons"))),
    ]:
        if items:
            st.markdown(f"**{lbl}**")
            for x in items:
                st.markdown(f"- {x}")
