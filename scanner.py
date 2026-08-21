"""Fetch option chains and score unusual activity."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable

import pandas as pd
import requests
import yfinance as yf


class MarketDataError(RuntimeError):
    """Raised when Yahoo/options data cannot be fetched cleanly."""


def _yahoo_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*",
        }
    )
    return session


def _ticker(symbol: str) -> yf.Ticker:
    return yf.Ticker(symbol.upper().strip(), session=_yahoo_session())


def _friendly_market_error(symbol: str, exc: Exception) -> MarketDataError:
    text = str(exc).lower()
    if "expecting value" in text or "json" in text:
        return MarketDataError(
            f"{symbol}: Yahoo returned empty/blocked data (common on Streamlit Cloud). "
            "Wait 30–60s and retry, or use Demo mode."
        )
    if "rate" in text or "too many" in text:
        return MarketDataError(
            f"{symbol}: Yahoo rate-limited this server. Wait a minute and retry, or use Demo."
        )
    return MarketDataError(f"{symbol}: market data error — {exc}")


@dataclass
class UnusualAlert:
    ticker: str
    contract: str
    option_type: str
    strike: float
    expiry: str
    volume: int
    open_interest: int
    vol_oi_ratio: float
    last_price: float
    premium: float
    spot: float
    score: float
    reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default: int = 0) -> int:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def score_contract(
    *,
    ticker: str,
    option_type: str,
    row: pd.Series,
    spot: float,
    expiry: str,
    min_volume: int,
    min_open_interest: int,
    min_vol_oi_ratio: float,
    min_premium: float,
) -> UnusualAlert | None:
    volume = _safe_int(row.get("volume"))
    open_interest = _safe_int(row.get("openInterest"))
    last_price = _safe_float(row.get("lastPrice"))
    strike = _safe_float(row.get("strike"))
    contract = str(row.get("contractSymbol") or f"{ticker}-{expiry}-{option_type}-{strike}")

    if volume < min_volume or open_interest < min_open_interest or last_price <= 0:
        return None

    vol_oi = volume / max(open_interest, 1)
    premium = volume * last_price * 100  # options multiplier

    reasons: list[str] = []
    score = 0.0

    if vol_oi >= min_vol_oi_ratio:
        reasons.append(f"vol/OI {vol_oi:.1f}x")
        score += min(vol_oi, 20) * 2

    if premium >= min_premium:
        reasons.append(f"premium ${premium:,.0f}")
        score += min(premium / min_premium, 10) * 3

    if spot > 0 and strike > 0:
        moneyness = abs(strike - spot) / spot
        if 0.02 <= moneyness <= 0.15:
            reasons.append("mildly OTM")
            score += 4

    if not reasons:
        return None

    return UnusualAlert(
        ticker=ticker,
        contract=contract,
        option_type=option_type,
        strike=strike,
        expiry=expiry,
        volume=volume,
        open_interest=open_interest,
        vol_oi_ratio=round(vol_oi, 2),
        last_price=last_price,
        premium=round(premium, 2),
        spot=round(spot, 2),
        score=round(score, 2),
        reasons=reasons,
    )


def scan_ticker(
    ticker: str,
    *,
    max_expiries: int = 3,
    min_volume: int = 200,
    min_open_interest: int = 50,
    min_vol_oi_ratio: float = 2.0,
    min_premium: float = 50_000,
) -> list[UnusualAlert]:
    symbol = ticker.upper().strip()
    stock = _ticker(symbol)
    try:
        expiries = list(stock.options or [])
    except Exception as exc:
        raise _friendly_market_error(symbol, exc) from exc

    if not expiries:
        raise MarketDataError(
            f"{symbol}: no option expiries returned. Ticker may be invalid, or Yahoo blocked the request."
        )

    spot = _safe_float(getattr(stock.fast_info, "last_price", None))
    if spot <= 0:
        try:
            hist = stock.history(period="1d")
            if not hist.empty:
                spot = _safe_float(hist["Close"].iloc[-1])
        except Exception:
            spot = 0.0

    alerts: list[UnusualAlert] = []
    for expiry in expiries[:max_expiries]:
        try:
            chain = stock.option_chain(expiry)
        except Exception:
            continue

        for option_type, frame in (("call", chain.calls), ("put", chain.puts)):
            if frame is None or frame.empty:
                continue
            for _, row in frame.iterrows():
                alert = score_contract(
                    ticker=symbol,
                    option_type=option_type,
                    row=row,
                    spot=spot,
                    expiry=expiry,
                    min_volume=min_volume,
                    min_open_interest=min_open_interest,
                    min_vol_oi_ratio=min_vol_oi_ratio,
                    min_premium=min_premium,
                )
                if alert:
                    alerts.append(alert)

    return alerts


def scan_watchlist(tickers: Iterable[str], **kwargs) -> list[UnusualAlert]:
    all_alerts: list[UnusualAlert] = []
    errors: list[str] = []
    for ticker in tickers:
        symbol = ticker.strip().upper()
        if not symbol:
            continue
        try:
            all_alerts.extend(scan_ticker(symbol, **kwargs))
        except Exception as exc:
            errors.append(str(exc))
            print(f"[warn] {symbol}: {exc}")
    all_alerts.sort(key=lambda a: a.score, reverse=True)
    if not all_alerts and errors:
        raise MarketDataError(errors[0])
    return all_alerts


def demo_alerts() -> list[UnusualAlert]:
    """Synthetic alerts so you can see the bot format without market data."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return [
        UnusualAlert(
            ticker="NVDA",
            contract=f"NVDA{now.replace('-', '')[2:]}C00140000",
            option_type="call",
            strike=140.0,
            expiry=now,
            volume=18500,
            open_interest=2100,
            vol_oi_ratio=8.81,
            last_price=2.45,
            premium=4_532_500,
            spot=131.2,
            score=42.5,
            reasons=["vol/OI 8.8x", "premium $4,532,500", "mildly OTM"],
        ),
        UnusualAlert(
            ticker="TSLA",
            contract=f"TSLA{now.replace('-', '')[2:]}P00240000",
            option_type="put",
            strike=240.0,
            expiry=now,
            volume=9200,
            open_interest=1500,
            vol_oi_ratio=6.13,
            last_price=3.10,
            premium=2_852_000,
            spot=248.5,
            score=31.2,
            reasons=["vol/OI 6.1x", "premium $2,852,000"],
        ),
    ]
