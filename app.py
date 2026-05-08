"""Swing Screener — interfaz mobile-first."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from screener.pipeline import run_pipeline
from screener.plain_language import humanize_card
from screener.portfolio import load_portfolio, add_ticker, remove_ticker, portfolio_enabled
from data.fetch_prices import get_prices
from technicals.indicators import sma, atr
from technicals.breakout import detect_breakout


st.set_page_config(
    page_title="Screener",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────────────────────────────────
# CSS global
# ──────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: #0b1622 !important;
    font-family: 'Nunito', sans-serif !important;
}
[data-testid="stMain"] { background-color: #0b1622 !important; }

/* Chrome de Streamlit */
#MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stDeployButton"], [data-testid="stDecoration"] { display:none !important; }
header[data-testid="stHeader"] { background:transparent !important; height:0 !important; }
[data-testid="collapsedControl"]  { display:none !important; }

/* Contenedor principal */
.block-container { padding: 1rem 0.8rem 3rem !important; max-width: 720px !important; }

/* Texto */
h1,h2,h3,h4,p,label,span,div,
[data-testid="stMarkdownContainer"] { color: #e2e8f0 !important; font-family:'Nunito',sans-serif !important; }
.stCaption, [data-testid="stCaptionContainer"] { color: #94a3b8 !important; }

/* Cards */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #132033 !important;
    border: 1px solid #1e3a52 !important;
    border-radius: 14px !important;
    margin-bottom: 10px !important;
    overflow: hidden !important;
}

/* Inputs */
[data-testid="stTextInput"] input {
    background: #132033 !important;
    border: 1px solid #1e3a52 !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-family: 'Nunito', sans-serif !important;
}
[data-testid="stTextInput"] label { color: #94a3b8 !important; }

/* Pills (signal filter) */
[data-testid="stPillsButton"] button {
    border-radius: 20px !important;
    font-weight: 700 !important;
    font-size: 0.8rem !important;
    font-family: 'Nunito', sans-serif !important;
    border: 1.5px solid #1e3a52 !important;
    background: #0d1e30 !important;
    color: #94a3b8 !important;
    transition: all .15s !important;
}
[data-testid="stPillsButton"] button[aria-checked="true"] {
    background: #2d7eb5 !important;
    border-color: #2d7eb5 !important;
    color: #fff !important;
}

/* Botones */
[data-testid="baseButton-secondary"] {
    background: #1a2e44 !important;
    border: 1px solid #1e3a52 !important;
    color: #94a3b8 !important;
    border-radius: 8px !important;
    font-family: 'Nunito', sans-serif !important;
    font-weight: 600 !important;
}
[data-testid="baseButton-primary"] {
    background: #2d7eb5 !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Nunito', sans-serif !important;
    font-weight: 700 !important;
}

/* Expander */
[data-testid="stExpander"] {
    background: #0d1e30 !important;
    border: 1px solid #1e3a52 !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary { color: #94a3b8 !important; }

/* Progress */
[data-testid="stProgressBar"] > div { background: #1e3a52 !important; border-radius: 6px !important; }
[data-testid="stProgressBar"] > div > div { background: #2d7eb5 !important; border-radius: 6px !important; }

/* Metrics */
[data-testid="stMetric"] {
    background: #132033 !important;
    border: 1px solid #1e3a52 !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
}
[data-testid="stMetricValue"] { color: #e2e8f0 !important; font-weight: 800 !important; }
[data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.75rem !important; }

/* Divider */
hr { border-color: #1e3a52 !important; margin: 0.6rem 0 !important; }

/* Spinner */
[data-testid="stSpinner"] { color: #2d7eb5 !important; }

/* Multiselect */
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {
    background: #132033 !important;
    border-color: #1e3a52 !important;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────
# Cache
# ──────────────────────────────────────────────────────────────────────────
LAST_RUN_PATH = ROOT / "data" / "last_run.parquet"


@st.cache_data(show_spinner=False, ttl=3600)
def load_cached_run() -> pd.DataFrame | None:
    if LAST_RUN_PATH.exists():
        return pd.read_parquet(LAST_RUN_PATH)
    return None


def execute_pipeline(mode: str) -> None:
    tickers = ["NVDA", "AAPL", "MSFT", "AMD", "INTC", "MU", "STX", "WDC", "LRCX", "SNDK"] \
              if mode == "smoke" else None
    df = run_pipeline(tickers=tickers, fund_mode="yfinance_only", verbose=False)
    df.to_parquet(LAST_RUN_PATH)
    load_cached_run.clear()


# ──────────────────────────────────────────────────────────────────────────
# Datos
# ──────────────────────────────────────────────────────────────────────────
df = load_cached_run()

# ──────────────────────────────────────────────────────────────────────────
# Header
# ──────────────────────────────────────────────────────────────────────────
h_left, h_right = st.columns([4, 2])
with h_left:
    st.markdown("## 📈 Screener")
    if df is not None and not df.empty and LAST_RUN_PATH.exists():
        import datetime
        mtime = datetime.datetime.fromtimestamp(LAST_RUN_PATH.stat().st_mtime)
        st.caption(f"Datos del {mtime.strftime('%-d %b, %H:%M')}")
    else:
        st.caption("Sin datos — pulsa Actualizar")
with h_right:
    b1, b2 = st.columns(2)
    if b1.button("🔄", help="Actualizar universo completo", use_container_width=True):
        with st.spinner("Calculando..."):
            execute_pipeline("full")
        st.rerun()
    if b2.button("💨", help="Smoke test: 10 tickers", use_container_width=True):
        with st.spinner("10 tickers..."):
            execute_pipeline("smoke")
        st.rerun()

if df is None or df.empty:
    st.info("Sin datos aún. Pulsa 🔄 para actualizar.")
    st.stop()

# ──────────────────────────────────────────────────────────────────────────
# Portfolio
# ──────────────────────────────────────────────────────────────────────────
if portfolio_enabled():
    portfolio_data = load_portfolio()
    holdings = set(portfolio_data.get("holdings", {}).keys())
else:
    holdings = set()

SIG_EMOJI  = {"COMPRA": "🟢", "OBSERVAR": "👀", "SALIDA": "🔴", "EVITAR": "⚠️", "INELIGIBLE": "⚫"}
SIG_COLOR  = {"COMPRA": "#10b981", "OBSERVAR": "#f59e0b", "SALIDA": "#ef4444",
              "EVITAR": "#6b7280", "INELIGIBLE": "#475569"}

if holdings:
    st.markdown("#### 💼 Mi cartera")
    chips_html = "<div style='display:flex;flex-wrap:wrap;gap:8px;margin-bottom:4px'>"
    for tk in sorted(holdings):
        row_match = df[df["ticker"] == tk]
        sig  = row_match.iloc[0]["signal"] if not row_match.empty else "?"
        col  = SIG_COLOR.get(sig, "#6b7280")
        emj  = SIG_EMOJI.get(sig, "❓")
        chips_html += (
            f"<span style='background:{col}22;border:1.5px solid {col};"
            f"color:{col};border-radius:20px;padding:4px 12px;"
            f"font-weight:700;font-size:0.85rem'>{emj} {tk}</span>"
        )
    chips_html += "</div>"
    st.markdown(chips_html, unsafe_allow_html=True)

    # Vista rápida: tarjetas de cartera colapsables
    with st.expander("Ver estado completo de cartera"):
        for tk in sorted(holdings):
            row_match = df[df["ticker"] == tk]
            if row_match.empty:
                st.markdown(f"❓ **{tk}** — sin datos")
                continue
            r   = row_match.iloc[0]
            sig = r["signal"]
            col = SIG_COLOR.get(sig, "#6b7280")
            emj = SIG_EMOJI.get(sig, "❓")
            rs  = r.get("rs_rating")
            rs_s = f"RS {rs:.0f}" if rs and not pd.isna(rs) else ""
            name = r.get("name") or tk
            exits = r.get("exit_reasons") or []
            if hasattr(exits, "tolist"): exits = exits.tolist()
            st.markdown(
                f"<div style='border-left:3px solid {col};padding:8px 12px;"
                f"background:#0d1e30;border-radius:0 8px 8px 0;margin-bottom:8px'>"
                f"<span style='font-weight:800;color:{col}'>{emj} {tk}</span>"
                f"<span style='color:#94a3b8;font-size:0.85rem;margin-left:8px'>{name}</span>"
                f"<span style='float:right;color:#94a3b8;font-size:0.8rem'>{rs_s}</span><br>"
                f"<span style='color:{col};font-size:0.8rem;font-weight:700'>{sig}</span>"
                + (f"<br><span style='color:#ef4444;font-size:0.78rem'>⚠ {exits[0]}</span>" if exits and sig=="SALIDA" else "")
                + "</div>",
                unsafe_allow_html=True,
            )
            if portfolio_enabled():
                if st.button(f"✕ Quitar {tk} de cartera", key=f"rm_port_{tk}"):
                    remove_ticker(tk)
                    st.rerun()
    st.divider()

# ──────────────────────────────────────────────────────────────────────────
# Filtros inline
# ──────────────────────────────────────────────────────────────────────────
n_compra  = int((df["signal"] == "COMPRA").sum())
n_observar = int((df["signal"] == "OBSERVAR").sum())
n_salida  = int((df["signal"] == "SALIDA").sum())
n_saltar  = int(df["signal"].isin(["EVITAR", "INELIGIBLE"]).sum())

PILL_OPTS = [
    f"🟢 Comprar ({n_compra})",
    f"👀 Vigilar ({n_observar})",
    f"🔴 Vender ({n_salida})",
    f"⚪ Saltar ({n_saltar})",
    "📋 Todo",
]
PILL_TO_SIGS = {
    PILL_OPTS[0]: ["COMPRA"],
    PILL_OPTS[1]: ["OBSERVAR"],
    PILL_OPTS[2]: ["SALIDA"],
    PILL_OPTS[3]: ["EVITAR", "INELIGIBLE"],
    PILL_OPTS[4]: ["COMPRA", "OBSERVAR", "SALIDA", "EVITAR", "INELIGIBLE"],
}

selected_pill = st.pills(
    "Filtro",
    PILL_OPTS,
    default=PILL_OPTS[1] if n_compra == 0 else PILL_OPTS[0],
    label_visibility="collapsed",
)
if selected_pill is None:
    selected_pill = PILL_OPTS[1] if n_compra == 0 else PILL_OPTS[0]

search = st.text_input("🔍  Buscar empresa o ticker", placeholder="Ej: Nvidia, MU, semiconductores...",
                        label_visibility="collapsed")

with st.expander("⚙️  Filtrar por sector"):
    sectors_all = sorted(df["sector"].dropna().unique().tolist())
    sectors_sel = st.multiselect("Sectores", sectors_all, default=sectors_all,
                                  label_visibility="collapsed")

# ──────────────────────────────────────────────────────────────────────────
# Aplicar filtros
# ──────────────────────────────────────────────────────────────────────────
mask = df["signal"].isin(PILL_TO_SIGS[selected_pill])
if sectors_sel:
    mask &= df["sector"].isin(sectors_sel)
if search:
    s = search.strip().lower()
    name_col = df["name"] if "name" in df.columns else df["ticker"]
    mask &= (
        df["ticker"].str.lower().str.contains(s, na=False)
        | name_col.astype(str).str.lower().str.contains(s, na=False)
    )

score = df["rs_rating"].fillna(0) * 0.5 + df["fund_composite"].fillna(0) * 0.5
shown = df[mask].assign(_score=score[mask]).sort_values("_score", ascending=False).drop(columns="_score")

st.caption(f"{len(shown)} empresa{'s' if len(shown)!=1 else ''} · {len(df)} en total")

if shown.empty:
    st.info("Ninguna empresa cumple los filtros. Prueba con 'Todo' o borra la búsqueda.")
    st.stop()

# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────
def fuerza_color(v: float | None) -> str:
    if v is None or pd.isna(v): return "#6b7280"
    if v >= 75: return "#10b981"
    if v >= 50: return "#f59e0b"
    return "#ef4444"


# ──────────────────────────────────────────────────────────────────────────
# Tarjetas
# ──────────────────────────────────────────────────────────────────────────
for _, row in shown.head(50).iterrows():
    c       = humanize_card(row)
    ticker  = c["ticker"]
    fuerza  = c["fuerza"]
    fcolor  = fuerza_color(fuerza)
    sig_col = SIG_COLOR.get(row["signal"], "#6b7280")
    in_port = ticker in holdings

    with st.container(border=True):
        # Barra de color según señal (top border via HTML)
        st.markdown(
            f"<div style='height:4px;background:{sig_col};"
            f"margin:-1px -1px 12px -1px;border-radius:13px 13px 0 0'></div>",
            unsafe_allow_html=True,
        )

        # Cabecera: ticker + nombre + fuerza
        top_l, top_r = st.columns([3, 1])
        with top_l:
            name  = (row.get("name") or ticker)
            price = c["precio"]
            st.markdown(
                f"<div style='line-height:1.2'>"
                f"<span style='font-size:1.2rem;font-weight:900;color:#e2e8f0'>"
                f"{c['emoji']} {ticker}</span>"
                f"{'<span style=\"color:#f59e0b;margin-left:6px\">💼</span>' if in_port else ''}"
                f"<br><span style='font-size:0.82rem;color:#94a3b8'>{name}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with top_r:
            st.markdown(
                f"<div style='text-align:right;line-height:1.2'>"
                f"<span style='font-size:0.7rem;color:#64748b;display:block'>Fuerza</span>"
                f"<span style='font-size:1.5rem;font-weight:900;color:{fcolor}'>"
                f"{'—' if fuerza is None else f'{fuerza:.0f}'}</span>"
                f"<span style='font-size:0.8rem;color:#64748b'>/100</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # Señal + sector + precio
        price_str = f" · ${price:.2f}" if price else ""
        st.markdown(
            f"<div style='margin:8px 0 4px'>"
            f"<span style='background:{sig_col}22;border:1px solid {sig_col};"
            f"color:{sig_col};border-radius:12px;padding:2px 10px;"
            f"font-size:0.78rem;font-weight:700'>{c['label']}</span>"
            f"<span style='color:#64748b;font-size:0.78rem;margin-left:8px'>"
            f"{c['sector'] or ''}{price_str}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Explicación
        st.markdown(
            f"<p style='color:#cbd5e1;font-size:0.88rem;margin:8px 0 10px;line-height:1.5'>"
            f"{c['explicacion']}</p>",
            unsafe_allow_html=True,
        )

        # Barras de calidad e impulso
        if c["calidad"] is not None:
            st.progress(min(int(c["calidad"]), 100),
                        text=f"Salud empresa: {c['calidad']:.0f}/100")
        if c["impulso"] is not None:
            st.progress(min(int(c["impulso"]), 100),
                        text=f"Mejor que el {c['impulso']:.0f}% del mercado")

        # Fila inferior: portfolio + detalle técnico
        bot_l, bot_r = st.columns([1, 1])
        with bot_l:
            with st.expander("📊 Análisis y gráfico"):
                t = c["tecnico"]
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("RS", f"{t['rs_rating']:.0f}" if t['rs_rating'] else "—")
                m2.metric("Stage 2", "✅" if t['trend_template'] else "❌")
                m3.metric("Breakout", "✅" if t['breakout'] else "❌")
                m4.metric("Piotroski", f"{t['f_score']}/9" if t['f_score'] is not None else "—")

                for label, items in [
                    ("✅ A favor", t["entry_reasons"]),
                    ("⛔ Bloqueadores", t["entry_blockers"]),
                    ("⚠️ Avisos", t["exit_reasons"]),
                ]:
                    if items:
                        st.markdown(f"**{label}**")
                        for x in items:
                            st.markdown(f"- {x}")

                try:
                    prices  = get_prices(ticker)
                    tail    = prices.tail(252)
                    fig = go.Figure(data=[go.Candlestick(
                        x=tail.index,
                        open=tail["open"], high=tail["high"],
                        low=tail["low"],   close=tail["close"],
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
                    bk    = detect_breakout(prices)
                    pivot = bk.get("pivot") if bk else None
                    if pivot:
                        fig.add_hline(
                            y=pivot, line=dict(color="#10b981", dash="dash"),
                            annotation_text=f"Techo {pivot:.2f}",
                            annotation_position="right",
                        )
                    hi22  = prices["high"].rolling(22, min_periods=22).max()
                    chand = (hi22 - 3 * atr(prices, 22)).reindex(tail.index)
                    fig.add_trace(go.Scatter(
                        x=tail.index, y=chand, name="Stop",
                        line=dict(color="#6b7280", dash="dot", width=1),
                    ))
                    fig.update_layout(
                        paper_bgcolor="#0d1e30", plot_bgcolor="#0d1e30",
                        font=dict(color="#94a3b8", family="Nunito"),
                        title=dict(text=f"{ticker} — 12 meses", font=dict(color="#e2e8f0")),
                        height=420, xaxis_rangeslider_visible=False,
                        hovermode="x unified",
                        margin=dict(l=4, r=4, t=36, b=4),
                        legend=dict(orientation="h", y=-0.08,
                                    font=dict(size=10, color="#94a3b8")),
                        xaxis=dict(gridcolor="#1e3a52", color="#64748b"),
                        yaxis=dict(gridcolor="#1e3a52", color="#64748b"),
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.caption(f"Gráfico no disponible: {e}")

        with bot_r:
            if portfolio_enabled():
                if in_port:
                    if st.button("💼 En cartera", key=f"p_{ticker}",
                                 type="primary", use_container_width=True,
                                 help="Toca para quitar"):
                        remove_ticker(ticker)
                        st.rerun()
                else:
                    if st.button("＋ Añadir a cartera", key=f"p_{ticker}",
                                 use_container_width=True,
                                 help="Marcar como posición activa"):
                        add_ticker(ticker)
                        st.rerun()

if len(shown) > 50:
    st.caption(f"Mostrando 50 de {len(shown)}. Usa el buscador para afinar.")
