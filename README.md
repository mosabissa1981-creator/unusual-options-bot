# Unusual Options Bot

A simple starter bot that scans a stock watchlist for **unusual options activity** and prints (or Discord-posts) the top hits.

## How it works

1. Pulls option chains for tickers you choose (free Yahoo Finance data via `yfinance`)
2. Scores contracts that look unusual:
   - high **volume vs open interest**
   - large estimated **premium** (`volume × price × 100`)
   - mildly out-of-the-money near-term contracts
3. Ranks by score and alerts you

This is a learning prototype. It is **not** Unusual Whales-quality full-market flow.

## Quick start

```bash
cd unusual-options-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# See sample output instantly
python main.py --demo

# Live scan (delayed free data)
python main.py

# Keep scanning every 5 minutes
python main.py --loop --interval 300
```

## Optional Discord alerts

1. In Discord: channel settings → Integrations → Webhooks → New Webhook
2. Paste the URL into `.env`:

```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

3. Run `python main.py` (or `--demo`)

## Tune sensitivity

Edit `.env`:

- `WATCHLIST` — tickers to scan
- `MIN_VOLUME` — ignore tiny prints
- `MIN_VOL_OI_RATIO` — e.g. `2.0` means volume at least 2× open interest
- `MIN_PREMIUM` — minimum notional interest in dollars
- `MAX_EXPIRIES` — how many nearest expirations to check

## Limits of this free version

- Delayed / incomplete data vs paid flow vendors
- Watchlist only (not every ticker in the market)
- No sweep/block/ask-side aggression tags like Unusual Whales
- Yahoo data can fail or rate-limit

## Next upgrades

1. Broker API (Tradier) for cleaner chains
2. Unusual Whales API for true flow alerts (~$150/mo)
3. Host on a cheap VPS / GitHub Actions cron to run during market hours
