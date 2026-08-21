# Unusual Options + GEX Scanner

Free prototype that scans unusual options and approximates **GEX (gamma exposure)** by strike.

## Easiest on iPhone: Telegram

1. On iPhone, install **Telegram**
2. Open Telegram → search **@BotFather** → Start
3. Send `/newbot`, pick a name (e.g. `My GEX Scanner`) and username
4. Copy the **token** BotFather gives you
5. On your computer:

```bash
cd unusual-options-bot
source .venv/bin/activate   # Windows: .venv\Scripts\activate
cp .env.example .env
```

6. Edit `.env` and paste:
```
TELEGRAM_BOT_TOKEN=123456:ABC-your-token
```

7. Start the bot (keep this running on your computer/VPS):
```bash
python telegram_bot.py
```

8. On iPhone Telegram, open **your bot** → Start, then try:
- `/gex SPY`
- `/scan NVDA`
- `/demo`

That’s the easiest phone workflow: tap commands, get GEX levels back as messages.

---

## Mobile web (Safari / Home Screen)

```bash
source .venv/bin/activate
python webapp.py
```

- On the same computer: open `http://127.0.0.1:8080`
- On iPhone (same Wi‑Fi): open `http://YOUR_COMPUTER_IP:8080`
- In Safari: Share → **Add to Home Screen**

Buttons: **GEX**, **Unusual**, quick tickers SPY/QQQ/NVDA/TSLA.

---

## Laptop terminal (original)

```bash
python main.py --demo
python main.py
python main.py --gex SPY
```

---

## What GEX numbers mean (simple)

- **Net GEX positive**: dealers often dampen moves (pin / choppier)
- **Net GEX negative**: moves can extend more easily
- **Flip / zero-gamma**: area where GEX sign changes
- **Large +/− GEX strikes**: magnets / walls traders watch

This is an **approximation** from free Yahoo chains (OI + gamma), not SpotGamma/Unusual Whales dealer GEX.

## Install (first time)

```bash
cd unusual-options-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
