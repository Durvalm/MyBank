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


def fetch_transaction(tx_id):
    with get_db() as conn:
        return conn.execute(
            """
            SELECT id, amount, type, category, description, date
            FROM transactions
            WHERE id = ?
            """,
            (tx_id,),
        ).fetchone()


def update_transaction(tx_id, amount, tx_type, category, description, date):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE transactions
            SET amount = ?, type = ?, category = ?, description = ?, date = ?
            WHERE id = ?
            """,
            (amount, tx_type, category, description, date, tx_id),
        )


def delete_transaction(tx_id):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM transactions WHERE id = ?",
            (tx_id,),
        )


def count_transactions(search_query=None):
    clause = ""
    params = []
    if search_query:
        clause = "WHERE description LIKE ? OR category LIKE ? OR type LIKE ? OR date LIKE ?"
        token = f"%{search_query}%"
        params = [token, token, token, token]

    with get_db() as conn:
        row = conn.execute(
            f"SELECT COUNT(*) AS total FROM transactions {clause}",
            params,
        ).fetchone()
    return row["total"] if row else 0


def query_transactions(search_query=None, limit=20, offset=0):
    clause = ""
    params = []
    if search_query:
        clause = "WHERE description LIKE ? OR category LIKE ? OR type LIKE ? OR date LIKE ?"
        token = f"%{search_query}%"
        params = [token, token, token, token]

    params.extend([limit, offset])
    with get_db() as conn:
        return conn.execute(
            f"""
            SELECT id, amount, type, category, description, date
            FROM transactions
            {clause}
            ORDER BY date DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
