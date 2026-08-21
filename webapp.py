#!/usr/bin/env python3
"""Mobile-friendly GEX scanner web app (open in iPhone Safari)."""

from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

from gex import compute_gex, demo_gex, format_gex_text
from scanner import scan_ticker


def page(title: str, body: str, ticker: str) -> bytes:
    safe_ticker = (
        ticker.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
    )
    safe_body = (
        body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <title>{title}</title>
  <style>
    :root {{
      --bg0: #0f1412;
      --bg1: #18201c;
      --ink: #e8f0ea;
      --muted: #9bb0a3;
      --accent: #3dba7c;
      --line: rgba(232,240,234,.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(1200px 600px at 10% -10%, #1f3a2d 0%, transparent 55%),
        radial-gradient(900px 500px at 100% 0%, #2a2418 0%, transparent 50%),
        linear-gradient(180deg, var(--bg0), var(--bg1));
    }}
    main {{
      max-width: 720px;
      margin: 0 auto;
      padding: 1.25rem 1rem 3rem;
    }}
    h1 {{
      font-size: clamp(1.8rem, 7vw, 2.4rem);
      letter-spacing: -0.03em;
      margin: 0 0 .35rem;
    }}
    .sub {{ color: var(--muted); margin: 0 0 1.25rem; line-height: 1.4; }}
    form {{
      display: grid;
      grid-template-columns: 1fr auto auto;
      gap: .6rem;
      margin-bottom: 1rem;
    }}
    input, button, a.btn {{
      font: inherit;
      border-radius: 12px;
      border: 1px solid var(--line);
      padding: .85rem 1rem;
    }}
    input {{
      background: rgba(255,255,255,.04);
      color: var(--ink);
      width: 100%;
    }}
    button, a.btn {{
      background: var(--accent);
      color: #062214;
      font-weight: 700;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      white-space: nowrap;
    }}
    button.secondary, a.btn.secondary {{ background: transparent; color: var(--ink); }}
    .panel {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 1rem;
      background: rgba(0,0,0,.22);
      overflow: auto;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: .92rem;
      line-height: 1.45;
    }}
    .hint {{ color: var(--muted); font-size: .9rem; margin-top: 1rem; }}
    .row {{ display: flex; gap: .5rem; flex-wrap: wrap; margin: .75rem 0 0; }}
    @media (max-width: 560px) {{
      form {{ grid-template-columns: 1fr 1fr; }}
      form input {{ grid-column: 1 / -1; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>GEX Scanner</h1>
    <p class="sub">Mobile scanner for gamma exposure + unusual options. Add to iPhone Home Screen from Safari Share.</p>
    <form method="GET" action="/">
      <input name="ticker" value="{safe_ticker}" placeholder="Ticker e.g. SPY" maxlength="12" autocapitalize="characters" />
      <button type="submit" name="mode" value="gex">GEX</button>
      <button class="secondary" type="submit" name="mode" value="scan">Unusual</button>
    </form>
    <div class="row">
      <a class="btn secondary" href="/?ticker=SPY&mode=gex">SPY</a>
      <a class="btn secondary" href="/?ticker=QQQ&mode=gex">QQQ</a>
      <a class="btn secondary" href="/?ticker=NVDA&mode=gex">NVDA</a>
      <a class="btn secondary" href="/?ticker=TSLA&mode=gex">TSLA</a>
      <a class="btn secondary" href="/?mode=demo">Demo</a>
    </div>
    <div class="panel" style="margin-top:1rem"><pre>{safe_body}</pre></div>
    <p class="hint">Free delayed data approx. Not dealer-exact GEX. For phone push alerts, run the Telegram bot.</p>
  </main>
</body>
</html>"""
    return html.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path not in ("/", "/index.html"):
            self.send_response(404)
            self.end_headers()
            return

        qs = parse_qs(parsed.query)
        ticker = (qs.get("ticker", ["SPY"])[0] or "SPY").upper().strip()
        mode = (qs.get("mode", ["gex"])[0] or "gex").lower()

        try:
            if mode == "demo":
                text = format_gex_text(demo_gex(ticker))
            elif mode == "scan":
                alerts = scan_ticker(
                    ticker,
                    max_expiries=2,
                    min_volume=500,
                    min_open_interest=100,
                    min_vol_oi_ratio=3.0,
                    min_premium=100_000,
                )
                if not alerts:
                    text = f"No unusual contracts for {ticker}."
                else:
                    lines = [f"Unusual options — {ticker}", ""]
                    for a in alerts[:10]:
                        lines.append(
                            f"{a.option_type.upper()} ${a.strike:g} {a.expiry}\n"
                            f"Vol {a.volume:,} | OI {a.open_interest:,} | Vol/OI {a.vol_oi_ratio}x\n"
                            f"Premium ${a.premium:,.0f} | Score {a.score}"
                        )
                        lines.append("")
                    text = "\n".join(lines)
            else:
                text = format_gex_text(compute_gex(ticker, max_expiries=2))
        except Exception as exc:
            text = f"Error: {exc}"

        html = page("GEX Scanner", text, ticker)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(html)

    def log_message(self, fmt, *args):  # quieter logs
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def main() -> None:
    load_dotenv()
    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_PORT", "8080"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"GEX web scanner: http://127.0.0.1:{port}")
    print("On iPhone (same Wi-Fi): http://YOUR_COMPUTER_IP:8080")
    print("Or use Telegram bot for the easiest phone experience.")
    server.serve_forever()


if __name__ == "__main__":
    main()
