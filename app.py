"""Swing Screener — interfaz web simple en lenguaje plano.

Lanzar:
    .\\.venv\\Scripts\\streamlit.exe run app.py
"""
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
from screener.plain_language import humanize_card, SIGNAL_SHORT
from data.fetch_prices import get_prices
from technicals.indicators import sma, atr
from technicals.breakout import detect_breakout


st.set_page_config(page_title="Swing Screener", page_icon="📈", layout="wide")


# ──────────────────────────────────────────────────────────────────────────
# Cache de resultados
# ──────────────────────────────────────────────────────────────────────────
LAST_RUN_PATH = ROOT / "data" / "last_run.parquet"


@st.cache_data(show_spinner=False, ttl=3600)   # relee el parquet cada hora
def load_cached_run() -> pd.DataFrame | None:
    if LAST_RUN_PATH.exists():
        return pd.read_parquet(LAST_RUN_PATH)
    return None


def execute_pipeline(mode: str) -> pd.DataFrame:
    if mode == "smoke":
        tickers = ["NVDA", "AAPL", "MSFT", "AMD", "INTC", "MU", "STX", "WDC", "LRCX", "SNDK"]
    else:
        tickers = None
    df = run_pipeline(tickers=tickers, fund_mode="yfinance_only", verbose=False)
    df.to_parquet(LAST_RUN_PATH)
    return df


# ──────────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────────
st.sidebar.title("📈 Swing Screener")
st.sidebar.caption("Pulsa un botón para actualizar los datos.")

col_a, col_b = st.sidebar.columns(2)
if col_a.button("🔄 Actualizar (rápido)", use_container_width=True):
    with st.spinner("Calculando con cache..."):
        load_cached_run.clear()
        execute_pipeline("full")
    st.rerun()

if col_b.button("🚀 Smoke (10)", use_container_width=True):
    with st.spinner("Calculando 10 tickers..."):
        load_cached_run.clear()
        execute_pipeline("smoke")
    st.rerun()

st.sidebar.divider()

df = load_cached_run()
if df is None or df.empty:
    st.title("📈 Swing Screener")
    st.info("No hay datos guardados aún. Pulsa 'Actualizar' o 'Smoke' en la barra lateral.")
    st.stop()

# Filtros
st.sidebar.subheader("Filtros")

view = st.sidebar.radio(
    "Qué mostrar",
    ["🟢 Comprar hoy", "👀 Vigilar", "🔴 Vender", "⚪ Saltar", "Todo"],
    index=0,
)

sectors_all = sorted(df["sector"].dropna().unique().tolist())
sectors_sel = st.sidebar.multiselect("Sector", sectors_all, default=sectors_all)

search = st.sidebar.text_input("Buscar (ticker o nombre)", "").strip()

st.sidebar.divider()
st.sidebar.markdown(
    "**Recordatorio**: este screener te da **pistas**, no consejo financiero. "
    "Decide tú con tu cabeza."
)


# ──────────────────────────────────────────────────────────────────────────
# Filtrar
# ──────────────────────────────────────────────────────────────────────────
SIG_FILTER = {
    "🟢 Comprar hoy": ["COMPRA"],
    "👀 Vigilar":     ["OBSERVAR"],
    "🔴 Vender":      ["SALIDA"],
    "⚪ Saltar":      ["EVITAR", "INELIGIBLE"],
    "Todo":           ["COMPRA", "OBSERVAR", "SALIDA", "EVITAR", "INELIGIBLE"],
}

mask = df["signal"].isin(SIG_FILTER[view])
if sectors_sel:
    mask &= df["sector"].isin(sectors_sel)
if search:
    s = search.lower()
    name_col = df["name"] if "name" in df.columns else df["ticker"]
    mask &= (
        df["ticker"].str.lower().str.contains(s, na=False)
        | name_col.astype(str).str.lower().str.contains(s, na=False)
    )

shown = df[mask].copy()


# ──────────────────────────────────────────────────────────────────────────
# Header con resumen
# ──────────────────────────────────────────────────────────────────────────
st.title("📈 Qué hago hoy")

c1, c2, c3, c4 = st.columns(4)
c1.metric("🟢 Comprar", int((df["signal"] == "COMPRA").sum()))
c2.metric("👀 Vigilar", int((df["signal"] == "OBSERVAR").sum()))
c3.metric("🔴 Vender",  int((df["signal"] == "SALIDA").sum()))
c4.metric("⚪ Saltar",  int((df["signal"].isin(["EVITAR", "INELIGIBLE"])).sum()))

st.caption(f"{len(shown)} empresas en el filtro actual ({len(df)} en total).")
st.divider()


# ──────────────────────────────────────────────────────────────────────────
# Lista de tarjetas
# ──────────────────────────────────────────────────────────────────────────
def fuerza_color(v: float | None) -> str:
    if v is None or pd.isna(v):
        return "#888"
    if v >= 75: return "#10b981"
    if v >= 50: return "#f59e0b"
    return "#ef4444"


def _ordenacion(df_: pd.DataFrame) -> pd.DataFrame:
    # Mayor fuerza = más interesante
    score = df_["rs_rating"].fillna(0) * 0.5 + df_["fund_composite"].fillna(0) * 0.5
    return df_.assign(_score=score).sort_values("_score", ascending=False).drop(columns="_score")


shown = _ordenacion(shown)

if shown.empty:
    st.info("Nada que mostrar con los filtros actuales.")
    st.stop()

# ──────────────────────────────────────────────────────────────────────────
# Render tarjetas
# ──────────────────────────────────────────────────────────────────────────
for _, row in shown.head(50).iterrows():
    c = humanize_card(row)
    fuerza = c["fuerza"]
    fcolor = fuerza_color(fuerza)

    with st.container(border=True):
        head1, head2 = st.columns([3, 2])
        with head1:
            name = row.get("name") if "name" in row.index else None
            title = f"### {c['emoji']} **{c['ticker']}**"
            if name and name != c['ticker']:
                title += f" · {name}"
            title += f" — {c['label']}"
            st.markdown(title)
            st.caption(f"{c['sector']}  ·  Precio: {c['precio']:.2f} $" if c['precio'] else c['sector'])
        with head2:
            if fuerza is not None:
                st.markdown(
                    f"<div style='text-align:right'>"
                    f"<span style='font-size:0.85rem;color:#666'>Fuerza global</span><br>"
                    f"<span style='font-size:1.6rem;font-weight:700;color:{fcolor}'>{fuerza:.0f}/100</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.markdown(f"**{c['explicacion']}**")

        # Sub-puntuaciones plano
        sc1, sc2 = st.columns(2)
        if c["calidad"] is not None:
            sc1.progress(min(int(c["calidad"]), 100), text=f"Salud de la empresa: {c['calidad']:.0f}/100")
        if c["impulso"] is not None:
            sc2.progress(min(int(c["impulso"]), 100), text=f"Va mejor que el {c['impulso']:.0f}% del mercado")

        with st.expander("📊 Ver detalle técnico y gráfico"):
            t = c["tecnico"]
            mc1, mc2, mc3, mc4 = st.columns(4)
            mc1.metric("RS rating", f"{t['rs_rating']:.0f}" if t['rs_rating'] is not None else "—")
            mc2.metric("Stage 2 (tendencia)", "✅" if t['trend_template'] else "❌")
            mc3.metric("Breakout hoy", "✅" if t['breakout'] else "❌")
            mc4.metric("Piotroski", f"{t['f_score']}/9" if t['f_score'] is not None else "—")

            if t["entry_reasons"]:
                st.markdown("**A favor**")
                for x in t["entry_reasons"]:
                    st.markdown(f"- {x}")
            if t["entry_blockers"]:
                st.markdown("**Lo que falla para entrar**")
                for x in t["entry_blockers"]:
                    st.markdown(f"- {x}")
            if t["exit_reasons"]:
                st.markdown("**Avisos**")
                for x in t["exit_reasons"]:
                    st.markdown(f"- {x}")

            # Gráfico interactivo
            try:
                prices = get_prices(c["ticker"])
                tail = prices.tail(252)
                fig = go.Figure(data=[go.Candlestick(
                    x=tail.index,
                    open=tail["open"], high=tail["high"], low=tail["low"], close=tail["close"],
                    name=c["ticker"],
                )])
                for n, color in [(50, "#3b82f6"), (150, "#f97316"), (200, "#ef4444")]:
                    s = sma(prices["close"], n).reindex(tail.index)
                    fig.add_trace(go.Scatter(x=tail.index, y=s, name=f"SMA{n}", line=dict(color=color, width=1)))
                bk = detect_breakout(prices)
                pivot = bk.get("pivot") if bk else None
                if pivot:
                    fig.add_hline(y=pivot, line=dict(color="#10b981", dash="dash"),
                                  annotation_text=f"Techo reciente {pivot:.2f}", annotation_position="right")
                # Stop ATR
                hi22 = prices["high"].rolling(22, min_periods=22).max()
                chand = (hi22 - 3 * atr(prices, 22)).reindex(tail.index)
                fig.add_trace(go.Scatter(x=tail.index, y=chand, name="Stop sugerido", line=dict(color="#888", dash="dot")))
                fig.update_layout(
                    title=f"{c['ticker']} — últimos 12 meses",
                    height=500, xaxis_rangeslider_visible=False, hovermode="x unified",
                    margin=dict(l=10, r=10, t=40, b=10),
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"No se pudo cargar el gráfico: {e}")

if len(shown) > 50:
    st.caption(f"Mostrando 50 de {len(shown)}. Refina con filtros si necesitas más.")
