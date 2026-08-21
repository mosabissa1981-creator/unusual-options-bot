# Unusual Options Bot (iPhone-ready)

Free unusual-options + GEX scanner.

## Important Streamlit Cloud note

`runtime.txt` is **ignored** by Streamlit Community Cloud.
You must set Python in the Streamlit UI:

1. Open your app → **Manage app** → **Settings**
2. Set **Python version = 3.11**
3. Make the app **Public**
4. **Reboot** the app

If Python stays on 3.14, Pillow/pandas fail to install.

## Use on iPhone

1. Deploy from GitHub at https://share.streamlit.io/
2. Repo: `unusual-options-bot`
3. Main file: `streamlit_app.py`
4. Advanced settings: **Python 3.11**
5. Open the `*.streamlit.app` link in iPhone Chrome

## Run on computer

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```
