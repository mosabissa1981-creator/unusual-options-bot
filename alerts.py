"""Optional Discord alerts."""

from __future__ import annotations

import requests

from scanner import UnusualAlert


def format_alert(alert: UnusualAlert) -> str:
    side = alert.option_type.upper()
    reasons = ", ".join(alert.reasons)
    return (
        f"**{alert.ticker} {side} ${alert.strike:g}** exp {alert.expiry}\n"
        f"Vol {alert.volume:,} | OI {alert.open_interest:,} | Vol/OI {alert.vol_oi_ratio}x\n"
        f"Last ${alert.last_price:.2f} | Premium ${alert.premium:,.0f} | Spot ${alert.spot:.2f}\n"
        f"Score {alert.score} — {reasons}"
    )


def send_discord(webhook_url: str, alerts: list[UnusualAlert], limit: int = 10) -> None:
    if not webhook_url:
        return

    if not alerts:
        requests.post(
            webhook_url,
            json={"content": "Unusual options scan finished — no alerts matched."},
            timeout=15,
        )
        return

    lines = ["**Unusual options alerts**", ""]
    for alert in alerts[:limit]:
        lines.append(format_alert(alert))
        lines.append("")

    # Discord message limit is 2000 chars
    content = "\n".join(lines)[:1900]
    response = requests.post(webhook_url, json={"content": content}, timeout=15)
    response.raise_for_status()
