# MyBank

## Web app (mobile-friendly)

This adds a tiny Flask web UI backed by SQLite. You can export a backup to the local `data.txt` any time.

### Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

### Export backup

Use the **Export Backup** link in the UI. It writes `data.txt` and keeps the previous version as `data.txt.bak`.
