#!/usr/bin/env python3
"""Free Unusual Options scanner — open in Chrome (desktop or phone)."""

from __future__ import annotations

import html as html_lib
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

from gex import compute_gex, demo_gex, format_gex_text
from scanner import demo_alerts, scan_ticker, scan_watchlist


DEFAULT_WATCHLIST = ["SPY", "QQQ", "AAPL", "NVDA", "TSLA", "AMZN", "META", "MSFT"]


def _esc(value: object) -> str:
    return html_lib.escape(str(value), quote=True)


def render_unusual_cards(alerts, title: str) -> str:
    if not alerts:
        return f"<p class='empty'>No unusual contracts matched for {_esc(title)}.</p>"

    cards = []
    for a in alerts[:20]:
        side = a.option_type.upper()
        side_class = "call" if a.option_type == "call" else "put"
        reasons = ", ".join(a.reasons)
        cards.append(
            f"""
            <article class="card {side_class}">
              <header>
                <div class="sym">{_esc(a.ticker)} <span>{_esc(side)}</span></div>
                <div class="score">Score {_esc(a.score)}</div>
              </header>
              <div class="strike">${_esc(f"{a.strike:g}")} · exp {_esc(a.expiry)}</div>
              <div class="metrics">
                <div><b>Vol</b><span>{a.volume:,}</span></div>
                <div><b>OI</b><span>{a.open_interest:,}</span></div>
                <div><b>Vol/OI</b><span>{_esc(a.vol_oi_ratio)}x</span></div>
                <div><b>Premium</b><span>${a.premium:,.0f}</span></div>
              </div>
              <div class="meta">Last ${a.last_price:.2f} · Spot ${a.spot:.2f}<br/>{_esc(reasons)}</div>
            </article>
            """
        )
    return (
        f"<p class='count'>Found <b>{len(alerts)}</b> unusual contracts "
        f"(showing top {min(20, len(alerts))})</p>"
        + "<div class='grid'>"
        + "".join(cards)
        + "</div>"
    )


def page(*, title: str, mode: str, ticker: str, content: str) -> bytes:
    active = {
        "scan": "active" if mode == "scan" else "",
        "watch": "active" if mode == "watch" else "",
        "gex": "active" if mode == "gex" else "",
        "demo": "active" if mode == "demo" else "",
    }
    chips = "".join(
        f'<a class="chip" href="/?mode=scan&ticker={t}">{t}</a>' for t in DEFAULT_WATCHLIST
    )
    doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="theme-color" content="#10160f" />
  <title>{_esc(title)}</title>
  <style>
    :root {{
      --bg: #10160f;
      --panel: rgba(255,255,255,.04);
      --ink: #eef5ee;
      --muted: #9aaf9d;
      --line: rgba(238,245,238,.12);
      --accent: #58c27d;
      --call: #3dba7c;
      --put: #d27b5a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
      background:
        radial-gradient(900px 420px at 0% 0%, #243528 0%, transparent 60%),
        radial-gradient(700px 380px at 100% 10%, #2b2416 0%, transparent 55%),
        linear-gradient(180deg, #0c120c, var(--bg));
      min-height: 100vh;
    }}
    main {{ max-width: 920px; margin: 0 auto; padding: 1.1rem 1rem 2.5rem; }}
    h1 {{
      margin: 0;
      font-size: clamp(1.7rem, 5vw, 2.35rem);
      letter-spacing: -.03em;
      font-family: "IBM Plex Serif", Georgia, serif;
    }}
    .sub {{ color: var(--muted); margin: .35rem 0 1rem; line-height: 1.4; }}
    .tabs {{
      display: flex; gap: .45rem; flex-wrap: wrap; margin-bottom: .9rem;
    }}
    .tabs a {{
      text-decoration: none; color: var(--ink);
      border: 1px solid var(--line); border-radius: 999px;
      padding: .55rem .9rem; background: transparent; font-weight: 600;
    }}
    .tabs a.active {{ background: var(--accent); color: #062214; border-color: transparent; }}
    form.bar {{
      display: grid; grid-template-columns: 1fr auto; gap: .55rem; margin-bottom: .75rem;
    }}
    input, button {{
      font: inherit; border-radius: 12px; border: 1px solid var(--line);
      padding: .85rem 1rem;
    }}
    input {{ width: 100%; background: var(--panel); color: var(--ink); }}
    button {{
      background: var(--accent); color: #062214; font-weight: 700; cursor: pointer;
    }}
    .chips {{ display: flex; gap: .4rem; flex-wrap: wrap; margin-bottom: 1rem; }}
    .chip {{
      text-decoration: none; color: var(--ink); border: 1px solid var(--line);
      border-radius: 999px; padding: .4rem .7rem; font-size: .92rem;
    }}
    .count {{ color: var(--muted); margin: 0 0 .8rem; }}
    .grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: .75rem;
    }}
    .card {{
      background: var(--panel); border: 1px solid var(--line);
      border-radius: 16px; padding: .9rem 1rem;
      border-top: 3px solid var(--accent);
    }}
    .card.put {{ border-top-color: var(--put); }}
    .card.call {{ border-top-color: var(--call); }}
    .card header {{ display: flex; justify-content: space-between; gap: .5rem; }}
    .sym {{ font-weight: 700; font-size: 1.05rem; }}
    .sym span {{ color: var(--muted); font-weight: 600; margin-left: .25rem; }}
    .score {{ color: var(--accent); font-weight: 700; }}
    .strike {{ margin: .35rem 0 .55rem; color: var(--ink); }}
    .metrics {{
      display: grid; grid-template-columns: 1fr 1fr; gap: .35rem .6rem; margin-bottom: .55rem;
    }}
    .metrics b {{ display: block; color: var(--muted); font-size: .75rem; font-weight: 600; }}
    .metrics span {{ font-variant-numeric: tabular-nums; }}
    .meta {{ color: var(--muted); font-size: .86rem; line-height: 1.35; }}
    .panel {{
      background: var(--panel); border: 1px solid var(--line);
      border-radius: 16px; padding: 1rem; overflow: auto;
    }}
    pre {{ margin: 0; white-space: pre-wrap; font-family: ui-monospace, Menlo, monospace; line-height: 1.45; }}
    .empty {{ color: var(--muted); }}
    .hint {{ color: var(--muted); font-size: .88rem; margin-top: 1rem; }}
    @media (max-width: 560px) {{
      .metrics {{ grid-template-columns: 1fr 1fr; }}
    }}
  </style>
</head>
<body>
  <main>
    <h1>Unusual Options</h1>
    <p class="sub">Free browser scanner — same style as the GEX page. Open in Chrome on phone or computer.</p>

    <nav class="tabs">
      <a class="{active['scan']}" href="/?mode=scan&ticker={_esc(ticker)}">Unusual</a>
      <a class="{active['watch']}" href="/?mode=watch">Watchlist</a>
      <a class="{active['gex']}" href="/?mode=gex&ticker={_esc(ticker)}">GEX</a>
      <a class="{active['demo']}" href="/?mode=demo">Demo</a>
    </nav>

    <form class="bar" method="GET" action="/">
      <input type="hidden" name="mode" value="{_esc(mode if mode in ('scan','gex') else 'scan')}" />
      <input name="ticker" value="{_esc(ticker)}" placeholder="Ticker e.g. NVDA" maxlength="12" />
      <button type="submit">Scan</button>
    </form>

    <div class="chips">{chips}</div>
    {content}
    <p class="hint">Free delayed Yahoo data. Not Unusual Whales flow. Run on your computer, then open this page in Chrome.</p>
  </main>
</body>
</html>"""
    return doc.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path not in ("/", "/index.html"):
            self.send_error(404)
            return

        qs = parse_qs(parsed.query)
        ticker = (qs.get("ticker", ["NVDA"])[0] or "NVDA").upper().strip()
        mode = (qs.get("mode", ["scan"])[0] or "scan").lower()

        try:
            if mode == "demo":
                content = render_unusual_cards(demo_alerts(), "demo")
                title = "Unusual Options Demo"
            elif mode == "watch":
                alerts = scan_watchlist(
                    DEFAULT_WATCHLIST,
                    max_expiries=2,
                    min_volume=500,
                    min_open_interest=100,
                    min_vol_oi_ratio=3.0,
                    min_premium=100_000,
                )
                content = render_unusual_cards(alerts, "watchlist")
                title = "Unusual Options Watchlist"
            elif mode == "gex":
                text = format_gex_text(compute_gex(ticker, max_expiries=2))
                content = f"<div class='panel'><pre>{_esc(text)}</pre></div>"
                title = f"{ticker} GEX"
            else:
                alerts = scan_ticker(
                    ticker,
                    max_expiries=2,
                    min_volume=500,
                    min_open_interest=100,
                    min_vol_oi_ratio=3.0,
                    min_premium=100_000,
                )
                content = render_unusual_cards(alerts, ticker)
                title = f"{ticker} Unusual Options"
                mode = "scan"
        except Exception as exc:
            content = f"<p class='empty'>Error: {_esc(exc)}</p>"
            title = "Scanner error"

        body = page(title=title, mode=mode, ticker=ticker, content=content)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))


def main() -> None:
    load_dotenv()
    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_PORT", "8080"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Open in Chrome: http://127.0.0.1:{port}")
    print("Tabs: Unusual | Watchlist | GEX | Demo")
    server.serve_forever()


if __name__ == "__main__":
    main()
