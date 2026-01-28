# MyBank 

## Check Stats
<img width="1512" height="902" alt="Screenshot 2026-01-28 at 12 47 50 PM" src="https://github.com/user-attachments/assets/fa7ff566-eccf-494e-8b9b-5f0156312390" />

## Add Transactions
<img width="1511" height="901" alt="Screenshot 2026-01-28 at 12 48 02 PM" src="https://github.com/user-attachments/assets/d9896761-2470-415c-ae8a-951787adf224" />

## Web app (mobile-friendly)

Tiny Flask web UI backed by SQLite.

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
