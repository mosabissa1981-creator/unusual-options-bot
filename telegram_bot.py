#!/usr/bin/env python3
"""Telegram GEX + unusual-options bot — easiest way to use on iPhone."""

from __future__ import annotations

import os
import time

import requests
from dotenv import load_dotenv

from gex import compute_gex, demo_gex, format_gex_text
from scanner import scan_ticker
from alerts import format_alert


API = "https://api.telegram.org/bot{token}/{method}"


def tg(token: str, method: str, **payload):
    url = API.format(token=token, method=method)
    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data)
    return data["result"]


def send(token: str, chat_id: int, text: str) -> None:
    # Telegram hard limit 4096
    chunk = text[:4000]
    tg(token, "sendMessage", chat_id=chat_id, text=chunk)


def handle(token: str, chat_id: int, text: str) -> None:
    parts = (text or "").strip().split()
    if not parts:
        return
    cmd = parts[0].split("@")[0].lower()
    arg = parts[1].upper() if len(parts) > 1 else "SPY"

    if cmd in ("/start", "/help"):
        send(
            token,
            chat_id,
            "GEX Scanner bot (iPhone-friendly)\n\n"
            "Commands:\n"
            "/gex SPY — gamma exposure scanner\n"
            "/scan NVDA — unusual options on one ticker\n"
            "/demo — sample GEX without live data\n"
            "/help — this message\n\n"
            "Tip: tap a command, add a ticker if you want.",
        )
        return

    if cmd == "/demo":
        send(token, chat_id, format_gex_text(demo_gex(arg)))
        return

    if cmd == "/gex":
        send(token, chat_id, f"Scanning GEX for {arg}…")
        try:
            snap = compute_gex(arg, max_expiries=2)
            send(token, chat_id, format_gex_text(snap))
        except Exception as exc:
            send(token, chat_id, f"GEX failed for {arg}: {exc}")
        return

    if cmd == "/scan":
        send(token, chat_id, f"Scanning unusual options for {arg}…")
        try:
            alerts = scan_ticker(
                arg,
                max_expiries=2,
                min_volume=500,
                min_open_interest=100,
                min_vol_oi_ratio=3.0,
                min_premium=100_000,
            )
            if not alerts:
                send(token, chat_id, f"No unusual contracts for {arg}.")
                return
            lines = [f"Unusual options — {arg}", ""]
            for alert in alerts[:8]:
                lines.append(format_alert(alert).replace("**", ""))
                lines.append("")
            send(token, chat_id, "\n".join(lines))
        except Exception as exc:
            send(token, chat_id, f"Scan failed for {arg}: {exc}")
        return

    send(token, chat_id, "Unknown command. Try /help")


def main() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "Missing TELEGRAM_BOT_TOKEN in .env\n"
            "Create a bot with @BotFather on iPhone Telegram, then paste the token."
        )

    print("Telegram GEX bot running. Open Telegram on your iPhone and message your bot.")
    offset = None
    while True:
        try:
            updates = tg(
                token,
                "getUpdates",
                timeout=30,
                offset=offset,
                allowed_updates=["message"],
            )
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message") or {}
                chat = message.get("chat") or {}
                chat_id = chat.get("id")
                text = message.get("text") or ""
                if chat_id and text:
                    handle(token, chat_id, text)
        except KeyboardInterrupt:
            print("Stopped.")
            break
        except Exception as exc:
            print(f"[warn] {exc}")
            time.sleep(3)


if __name__ == "__main__":
    main()
