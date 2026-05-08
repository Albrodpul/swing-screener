"""Swing Screener — entry point with multi-page navigation."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation(
    [
        st.Page("pages/dashboard.py", title="Dashboard", icon="📊", default=True),
        st.Page("pages/portfolio.py", title="Mi Cartera", icon="💼"),
    ],
    position="hidden",
)
pg.run()
