import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "mybank.db")

INCOME_CATEGORIES = ["work", "financial_aid", "family", "sell", "other"]
SPENDING_CATEGORIES = [
    "transportation",
    "personal_care",
    "groceries",
    "eating_out",
    "travel",
    "shopping",
    "app_subscriptions",
    "education",
    "utilities",
    "rent",
    "cellphone",
    "hobbies",
    "fitness",
    "medical",
    "other",
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                date TEXT NOT NULL
            )
            """
        )


def insert_transaction(amount, tx_type, category, description, date):
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO transactions (amount, type, category, description, date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (amount, tx_type, category, description, date),
        )
