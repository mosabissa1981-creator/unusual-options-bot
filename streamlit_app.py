"""Unusual Options scanner — lightweight Streamlit entry for Cloud."""

from __future__ import annotations

import streamlit as st

APP_VERSION = "2026-08-21d"

st.set_page_config(page_title="Unusual Options", layout="centered")
st.title("Unusual Options")
st.caption(f"Phone scanner · build {APP_VERSION}")

mode = st.radio("Mode", ["Demo", "Unusual", "Watchlist", "GEX"], horizontal=True)
ticker = (st.text_input("Ticker", "NVDA") or "NVDA").strip().upper()
go = st.button("Scan", type="primary", use_container_width=True)

try:
    from gex import compute_gex, format_gex_text
    from scanner import demo_alerts, scan_ticker, scan_watchlist
except Exception as exc:
    st.error("App failed to import modules.")
    st.exception(exc)
    st.stop()


def show_alerts(alerts, title: str) -> None:
    if not alerts:
        st.warning("No unusual contracts matched.")
        return

    st.success(f"Found {len(alerts)} {title} (top 15)")
    for a in alerts[:15]:
        # Avoid markdown/backticks — they render broken on some iPhone browsers.
        st.write(
            f"{a.ticker} {a.option_type.upper()} ${a.strike:g} | Exp {a.expiry} | Score {a.score}"
        )
        st.write(
            f"Vol {a.volume:,} | OI {a.open_interest:,} | Vol/OI {a.vol_oi_ratio}x | "
            f"Premium ${a.premium:,.0f}"
        )
        st.write(f"Last ${a.last_price:.2f} | Spot ${a.spot:.2f}")
        if a.reasons:
            st.write("Reasons: " + ", ".join(a.reasons))
        st.write("---")


if mode == "Demo" or not go:
    st.warning("DEMO MODE: sample NVDA/TSLA alerts only. Ticker box is ignored.")
    show_alerts(demo_alerts(), "demo hits")
    if mode != "Demo":
        st.info("Switch mode and tap Scan for a live attempt.")
    st.stop()

try:
    if mode == "Watchlist":
        with st.spinner("Scanning watchlist..."):
            show_alerts(
                scan_watchlist(
                    ["SPY", "QQQ", "AAPL", "NVDA", "TSLA", "AMZN", "META", "MSFT"],
                    max_expiries=2,
                    min_volume=500,
                    min_open_interest=100,
                    min_vol_oi_ratio=3.0,
                    min_premium=100_000,
                ),
                "live hits",
            )
    elif mode == "GEX":
        with st.spinner(f"GEX {ticker}..."):
            st.text(format_gex_text(compute_gex(ticker, max_expiries=2)))
    else:
        with st.spinner(f"Scanning {ticker}..."):
            show_alerts(
                scan_ticker(
                    ticker,
                    max_expiries=2,
                    min_volume=500,
                    min_open_interest=100,
                    min_vol_oi_ratio=3.0,
                    min_premium=100_000,
                ),
                "live hits",
            )
except Exception as exc:
    st.error(f"Live scan failed: {exc}")
    st.warning("Falling back to DEMO sample alerts.")
    show_alerts(demo_alerts(), "demo hits")
