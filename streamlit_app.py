"""Unusual Options scanner — lightweight Streamlit entry for Cloud."""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Unusual Options", layout="centered")
st.title("Unusual Options")
st.caption("Free scanner · phone friendly")

mode = st.radio("Mode", ["Demo", "Unusual", "Watchlist", "GEX"], horizontal=True)
ticker = (st.text_input("Ticker", "NVDA") or "NVDA").strip().upper()
go = st.button("Scan", type="primary", use_container_width=True)

# Lazy imports so the page can boot even if market libs are still installing.
try:
    from gex import compute_gex, demo_gex, format_gex_text
    from scanner import demo_alerts, scan_ticker, scan_watchlist
except Exception as exc:
    st.error("Dependencies are still loading or failed to import.")
    st.exception(exc)
    st.stop()


def show_alerts(alerts):
    if not alerts:
        st.warning("No unusual contracts matched.")
        return
    st.write(f"Found **{len(alerts)}** hits (top 15):")
    for a in alerts[:15]:
        st.markdown(
            f"**{a.ticker} {a.option_type.upper()} ${a.strike:g}** `{a.expiry}`  \n"
            f"Vol {a.volume:,} · OI {a.open_interest:,} · Vol/OI {a.vol_oi_ratio}x · "
            f"Premium ${a.premium:,.0f} · Score {a.score}"
        )
        st.divider()


if mode == "Demo" or not go:
    show_alerts(demo_alerts())
    if mode != "Demo":
        st.info("Tap **Scan** for live data.")
    st.stop()

try:
    if mode == "Watchlist":
        with st.spinner("Scanning watchlist…"):
            show_alerts(
                scan_watchlist(
                    ["SPY", "QQQ", "AAPL", "NVDA", "TSLA", "AMZN", "META", "MSFT"],
                    max_expiries=2,
                    min_volume=500,
                    min_open_interest=100,
                    min_vol_oi_ratio=3.0,
                    min_premium=100_000,
                )
            )
    elif mode == "GEX":
        with st.spinner(f"GEX {ticker}…"):
            st.text(format_gex_text(compute_gex(ticker, max_expiries=2)))
    else:
        with st.spinner(f"Scanning {ticker}…"):
            show_alerts(
                scan_ticker(
                    ticker,
                    max_expiries=2,
                    min_volume=500,
                    min_open_interest=100,
                    min_vol_oi_ratio=3.0,
                    min_premium=100_000,
                )
            )
except Exception as exc:
    st.error(f"Scan failed: {exc}")
    st.exception(exc)
