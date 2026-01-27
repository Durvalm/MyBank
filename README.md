# MyBank

## Web app (mobile-friendly)

This adds a tiny Flask web UI backed by SQLite.

### Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

### Auth

Create an account at `/signup` and then log in at `/login`. The CLI now prompts for the same email/password.
