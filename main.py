#!/usr/bin/env python3
"""Unusual options activity bot — free prototype using Yahoo Finance chains."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from alerts import format_alert, send_discord
from scanner import demo_alerts, scan_watchlist


def load_settings() -> dict:
    load_dotenv()
    watchlist = [
        t.strip().upper()
        for t in os.getenv("WATCHLIST", "SPY,QQQ,AAPL,NVDA,TSLA").split(",")
        if t.strip()
    ]
    return {
        "watchlist": watchlist,
        "discord_webhook_url": os.getenv("DISCORD_WEBHOOK_URL", "").strip(),
        "min_volume": int(os.getenv("MIN_VOLUME", "500")),
        "min_open_interest": int(os.getenv("MIN_OPEN_INTEREST", "100")),
        "min_vol_oi_ratio": float(os.getenv("MIN_VOL_OI_RATIO", "3.0")),
        "min_premium": float(os.getenv("MIN_PREMIUM", "100000")),
        "max_expiries": int(os.getenv("MAX_EXPIRIES", "3")),
    }


def print_alerts(alerts, limit: int) -> None:
    if not alerts:
        print("No unusual contracts matched your thresholds.")
        return

    print(f"\nFound {len(alerts)} unusual contracts (showing top {min(limit, len(alerts))}):\n")
    for i, alert in enumerate(alerts[:limit], start=1):
        print(f"{i}. {format_alert(alert).replace('**', '')}")
        print("-" * 60)


def run_once(args: argparse.Namespace, settings: dict) -> list:
    if args.demo:
        print("Running DEMO mode with sample alerts...")
        return demo_alerts()

    print(f"Scanning {', '.join(settings['watchlist'])} ...")
    return scan_watchlist(
        settings["watchlist"],
        max_expiries=settings["max_expiries"],
        min_volume=settings["min_volume"],
        min_open_interest=settings["min_open_interest"],
        min_vol_oi_ratio=settings["min_vol_oi_ratio"],
        min_premium=settings["min_premium"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Unusual options activity bot")
    parser.add_argument("--demo", action="store_true", help="Use sample alerts (no market data)")
    parser.add_argument("--loop", action="store_true", help="Rescan forever")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between scans in --loop")
    parser.add_argument("--limit", type=int, default=15, help="Max alerts to print/send")
    parser.add_argument("--json", type=Path, help="Write full results to a JSON file")
    args = parser.parse_args()

    settings = load_settings()

    while True:
        started = time.time()
        alerts = run_once(args, settings)
        print_alerts(alerts, args.limit)

        if args.json:
            args.json.write_text(
                json.dumps([a.to_dict() for a in alerts], indent=2),
                encoding="utf-8",
            )
            print(f"Wrote {args.json}")

        if settings["discord_webhook_url"]:
            try:
                send_discord(settings["discord_webhook_url"], alerts, limit=args.limit)
                print("Sent Discord webhook.")
            except Exception as exc:
                print(f"[warn] Discord webhook failed: {exc}")

        elapsed = time.time() - started
        print(f"Scan finished in {elapsed:.1f}s")

        if not args.loop:
            break

        sleep_for = max(args.interval - int(elapsed), 5)
        print(f"Sleeping {sleep_for}s ...")
        time.sleep(sleep_for)


if __name__ == "__main__":
    main()
