# Unusual Options + GEX Scanner (Chrome web app)

Free unusual-options scanner you open in **Google Chrome** (phone or computer), built the same way as the GEX web page.

## Open in Chrome (easy)

### 1) Start the website on your computer
```bash
cd unusual-options-bot
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python webapp.py
```

### 2) Open Chrome
Go to:

**http://127.0.0.1:8080**

### 3) Use the tabs
- **Unusual** — scan one ticker (NVDA, TSLA, …)
- **Watchlist** — scan SPY/QQQ/AAPL/NVDA/TSLA/AMZN/META/MSFT
- **GEX** — gamma exposure for one ticker
- **Demo** — sample unusual alerts (no live data)

Tap a green chip (SPY, NVDA, …) or type a ticker and hit **Scan**.

### Phone Chrome (same Wi‑Fi)
1. Find your computer’s IP (example `192.168.1.20`)
2. On phone Chrome open: `http://192.168.1.20:8080`
3. Keep `python webapp.py` running on the computer

---

## Optional: terminal / Telegram

```bash
python main.py                 # unusual options in terminal
python main.py --gex SPY       # GEX in terminal
python telegram_bot.py         # iPhone Telegram commands
```

## Notes
- Free delayed Yahoo Finance data
- Not Unusual Whales / Barchart paid flow
- GEX is an approximation from option chains
