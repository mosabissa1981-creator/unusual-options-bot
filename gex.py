"""Approximate dealer GEX (gamma exposure) from option chains."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any

import pandas as pd
import yfinance as yf


@dataclass
class StrikeGex:
    strike: float
    call_gex: float
    put_gex: float
    net_gex: float
    call_oi: int
    put_oi: int


@dataclass
class GexSnapshot:
    ticker: str
    spot: float
    expiry: str
    as_of: str
    net_gex: float
    call_gex: float
    put_gex: float
    flip_strike: float | None
    max_positive_strike: float | None
    max_negative_strike: float | None
    strikes: list[StrikeGex]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def black_scholes_gamma(
    spot: float,
    strike: float,
    t_years: float,
    iv: float,
    rate: float = 0.05,
) -> float:
    """Black-Scholes gamma for a 1-share option."""
    if spot <= 0 or strike <= 0 or t_years <= 0 or iv <= 0:
        return 0.0
    sqrt_t = math.sqrt(t_years)
    d1 = (math.log(spot / strike) + (rate + 0.5 * iv * iv) * t_years) / (iv * sqrt_t)
    return _norm_pdf(d1) / (spot * iv * sqrt_t)


def _years_to_expiry(expiry: str) -> float:
    try:
        exp = datetime.strptime(expiry, "%Y-%m-%d").date()
    except ValueError:
        return 1 / 365
    days = max((exp - date.today()).days, 1)
    return days / 365.0


def _row_gamma(row: pd.Series, spot: float, strike: float, expiry: str) -> float:
    if "gamma" in row.index:
        g = _safe_float(row.get("gamma"))
        if g > 0:
            return g
    iv = _safe_float(row.get("impliedVolatility"))
    # yfinance IV is sometimes already a decimal (0.25) or percent-like
    if iv > 3:
        iv = iv / 100.0
    if iv <= 0:
        iv = 0.35
    return black_scholes_gamma(spot, strike, _years_to_expiry(expiry), iv)


def _contract_gex(gamma: float, open_interest: int, spot: float, sign: float) -> float:
    # Common retail approx: gamma * OI * 100 * spot^2 * 0.01
    return sign * gamma * open_interest * 100.0 * (spot ** 2) * 0.01


def _flip_strike(levels: list[StrikeGex]) -> float | None:
    if not levels:
        return None
    ordered = sorted(levels, key=lambda x: x.strike)
    for left, right in zip(ordered, ordered[1:]):
        if left.net_gex == 0:
            return left.strike
        if left.net_gex * right.net_gex < 0:
            # linear interpolation
            span = right.net_gex - left.net_gex
            if span == 0:
                return right.strike
            frac = -left.net_gex / span
            return round(left.strike + frac * (right.strike - left.strike), 2)
    return None


def compute_gex(ticker: str, max_expiries: int = 1) -> GexSnapshot:
    from scanner import MarketDataError, _friendly_market_error, _ticker

    symbol = ticker.strip().upper()
    stock = _ticker(symbol)
    try:
        expiries = list(stock.options or [])
    except Exception as exc:
        raise _friendly_market_error(symbol, exc) from exc
    if not expiries:
        raise MarketDataError(f"No options found for {symbol}")

    spot = _safe_float(getattr(stock.fast_info, "last_price", None))
    if spot <= 0:
        hist = stock.history(period="1d")
        if hist.empty:
            raise ValueError(f"Could not fetch spot for {symbol}")
        spot = _safe_float(hist["Close"].iloc[-1])

    expiry = expiries[0] if max_expiries >= 1 else expiries[0]
    # Aggregate nearest N expiries into one strike map
    by_strike: dict[float, dict[str, float]] = {}

    for exp in expiries[: max(1, max_expiries)]:
        try:
            chain = stock.option_chain(exp)
        except Exception:
            continue

        for option_type, frame, sign in (
            ("call", chain.calls, 1.0),
            ("put", chain.puts, -1.0),
        ):
            if frame is None or frame.empty:
                continue
            for _, row in frame.iterrows():
                strike = _safe_float(row.get("strike"))
                oi = _safe_int(row.get("openInterest"))
                if strike <= 0 or oi <= 0:
                    continue
                gamma = _row_gamma(row, spot, strike, exp)
                gex = _contract_gex(gamma, oi, spot, sign)
                bucket = by_strike.setdefault(
                    strike,
                    {"call_gex": 0.0, "put_gex": 0.0, "call_oi": 0, "put_oi": 0},
                )
                if option_type == "call":
                    bucket["call_gex"] += gex
                    bucket["call_oi"] += oi
                else:
                    bucket["put_gex"] += gex
                    bucket["put_oi"] += oi

    levels = [
        StrikeGex(
            strike=strike,
            call_gex=round(vals["call_gex"], 2),
            put_gex=round(vals["put_gex"], 2),
            net_gex=round(vals["call_gex"] + vals["put_gex"], 2),
            call_oi=int(vals["call_oi"]),
            put_oi=int(vals["put_oi"]),
        )
        for strike, vals in sorted(by_strike.items())
    ]

    # Keep strikes near spot for a readable scanner
    near = [lvl for lvl in levels if spot * 0.85 <= lvl.strike <= spot * 1.15]
    if len(near) >= 5:
        levels = near

    call_total = sum(l.call_gex for l in levels)
    put_total = sum(l.put_gex for l in levels)
    net_total = call_total + put_total

    max_pos = max(levels, key=lambda l: l.net_gex, default=None)
    max_neg = min(levels, key=lambda l: l.net_gex, default=None)

    return GexSnapshot(
        ticker=symbol,
        spot=round(spot, 2),
        expiry=expiry if max_expiries == 1 else f"{expiry}+{max_expiries - 1}",
        as_of=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        net_gex=round(net_total, 2),
        call_gex=round(call_total, 2),
        put_gex=round(put_total, 2),
        flip_strike=_flip_strike(levels),
        max_positive_strike=max_pos.strike if max_pos else None,
        max_negative_strike=max_neg.strike if max_neg else None,
        strikes=levels,
    )


def format_gex_text(snap: GexSnapshot, top_n: int = 8) -> str:
    bias = "POSITIVE (pin / mean-revert bias)" if snap.net_gex >= 0 else "NEGATIVE (trendier bias)"
    lines = [
        f"{snap.ticker} GEX scanner",
        f"Spot ${snap.spot:.2f} | Exp {snap.expiry}",
        f"Net GEX: {snap.net_gex:,.0f} → {bias}",
        f"Call GEX: {snap.call_gex:,.0f} | Put GEX: {snap.put_gex:,.0f}",
    ]
    if snap.flip_strike is not None:
        lines.append(f"Flip / zero-gamma ≈ ${snap.flip_strike:g}")
    if snap.max_positive_strike is not None:
        lines.append(f"Largest +GEX strike: ${snap.max_positive_strike:g}")
    if snap.max_negative_strike is not None:
        lines.append(f"Largest -GEX strike: ${snap.max_negative_strike:g}")

    ranked = sorted(snap.strikes, key=lambda s: abs(s.net_gex), reverse=True)[:top_n]
    lines.append("")
    lines.append("Top strikes by |GEX|:")
    for s in ranked:
        sign = "+" if s.net_gex >= 0 else ""
        lines.append(
            f"${s.strike:g}: {sign}{s.net_gex:,.0f}  (C OI {s.call_oi:,} / P OI {s.put_oi:,})"
        )
    lines.append("")
    lines.append(f"As of {snap.as_of}")
    return "\n".join(lines)


def demo_gex(ticker: str = "SPY") -> GexSnapshot:
    levels = [
        StrikeGex(560, 1.2e9, -0.4e9, 0.8e9, 12000, 4000),
        StrikeGex(565, 2.1e9, -0.6e9, 1.5e9, 18000, 5000),
        StrikeGex(570, 0.3e9, -1.8e9, -1.5e9, 8000, 16000),
        StrikeGex(575, 0.2e9, -2.4e9, -2.2e9, 6000, 21000),
        StrikeGex(580, 0.1e9, -1.1e9, -1.0e9, 4000, 12000),
    ]
    return GexSnapshot(
        ticker=ticker.upper(),
        spot=568.4,
        expiry="demo",
        as_of="demo",
        net_gex=sum(l.net_gex for l in levels),
        call_gex=sum(l.call_gex for l in levels),
        put_gex=sum(l.put_gex for l in levels),
        flip_strike=567.5,
        max_positive_strike=565,
        max_negative_strike=575,
        strikes=levels,
    )
