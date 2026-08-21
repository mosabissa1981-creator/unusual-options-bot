"""Unusual Options + GEX scanner — mobile-friendly Streamlit app for iPhone."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Unusual Options",
    page_icon=":chart_with_upwards_trend:",
    layout="centered",
    initial_sidebar_state="collapsed",
)

try:
    from gex import compute_gex, demo_gex, format_gex_text
    from scanner import demo_alerts, scan_ticker, scan_watchlist
except Exception as exc:  # pragma: no cover - boot diagnostics on Streamlit Cloud
    st.title("Unusual Options")
    st.error("App failed to import modules.")
    st.exception(exc)
    st.stop()

WATCHLIST = ["SPY", "QQQ", "AAPL", "NVDA", "TSLA", "AMZN", "META", "MSFT"]


@st.cache_data(ttl=120, show_spinner=False)
def cached_scan_ticker(symbol: str):
    return scan_ticker(
        symbol,
        max_expiries=2,
        min_volume=500,
        min_open_interest=100,
        min_vol_oi_ratio=3.0,
        min_premium=100_000,
    )


@st.cache_data(ttl=120, show_spinner=False)
def cached_watchlist():
    return scan_watchlist(
        WATCHLIST,
        max_expiries=2,
        min_volume=500,
        min_open_interest=100,
        min_vol_oi_ratio=3.0,
        min_premium=100_000,
    )


@st.cache_data(ttl=120, show_spinner=False)
def cached_gex(symbol: str):
    return compute_gex(symbol, max_expiries=2)


def show_alerts(alerts):
    if not alerts:
        st.warning("No unusual contracts matched.")
        return
    st.success(f"Found {len(alerts)} unusual contracts (showing top 20)")
    for a in alerts[:20]:
        with st.container(border=True):
            st.markdown(
                f"**{a.ticker} {a.option_type.upper()} ${a.strike:g}** · exp `{a.expiry}` · score **{a.score}**"
            )
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Vol", f"{a.volume:,}")
            c2.metric("OI", f"{a.open_interest:,}")
            c3.metric("Vol/OI", f"{a.vol_oi_ratio}x")
            c4.metric("Premium", f"${a.premium:,.0f}")
            st.caption(
                f"Last ${a.last_price:.2f} · Spot ${a.spot:.2f} · {', '.join(a.reasons)}"
            )


st.title("Unusual Options")
st.caption("Free scanner for phone & desktop. Delayed Yahoo data.")

mode = st.radio(
    "Mode",
    ["Demo", "Unusual", "Watchlist", "GEX"],
    horizontal=True,
    index=0,
)
ticker = st.text_input("Ticker", value="NVDA").strip().upper() or "NVDA"
run = st.button("Scan", type="primary", use_container_width=True)

# Always show Demo content so the app boots even before a live scan.
if mode == "Demo" or (not run and mode == "Demo"):
    show_alerts(demo_alerts())
    st.info("Switch mode to Unusual / Watchlist / GEX, then tap Scan.")
    st.stop()

if not run:
    st.info("Tap **Scan** to load live data.")
    st.stop()

try:
    if mode == "Watchlist":
        with st.spinner("Scanning watchlist…"):
            show_alerts(cached_watchlist())
    elif mode == "GEX":
        with st.spinner(f"Computing GEX for {ticker}…"):
            st.code(format_gex_text(cached_gex(ticker)), language=None)
    else:
        with st.spinner(f"Scanning {ticker}…"):
            show_alerts(cached_scan_ticker(ticker))
except Exception as exc:
    st.error(f"Scan failed: {exc}")
    st.exception(exc)
