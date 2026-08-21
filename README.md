# Unusual Options Bot (iPhone-ready)

Free unusual-options + GEX scanner.

## Use on iPhone (permanent)

`127.0.0.1` **never works on iPhone**. You need a public HTTPS link.

### Easiest permanent host: Streamlit Community Cloud (free)

1. Open: https://share.streamlit.io/
2. Sign in with GitHub (`mosabissa1981-creator`)
3. **New app** → repo: `unusual-options-bot`
4. Main file: `streamlit_app.py`
5. Deploy
6. Open the `*.streamlit.app` link in iPhone Chrome
7. Optional: Share → Add to Home Screen

### Other hosts
- **Render**: connect this repo (uses `Dockerfile` / `render.yaml`)
- **Railway / Fly.io**: deploy the Docker image

## Run on your computer

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Phone-friendly UI (recommended)
streamlit run streamlit_app.py

# Or classic HTML UI
python webapp.py
```

Computer only: http://127.0.0.1:8501 (Streamlit) or :8080 (webapp)

## Telegram (also great on iPhone)

1. Create a bot with `@BotFather`
2. Put token in `.env` as `TELEGRAM_BOT_TOKEN=...`
3. `python telegram_bot.py`
4. Send `/scan NVDA` or `/gex SPY`

## Notes
- Free delayed Yahoo Finance data
- Not Unusual Whales / paid flow
- GEX is an approximation
