import os
import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash

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
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                date TEXT NOT NULL,
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        columns = conn.execute("PRAGMA table_info(transactions)").fetchall()
        column_names = {col["name"] for col in columns}
        if "user_id" not in column_names:
            conn.execute("ALTER TABLE transactions ADD COLUMN user_id INTEGER")


def create_user(email, password):
    password_hash = generate_password_hash(password)
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO users (email, password_hash, created_at)
            VALUES (?, ?, datetime('now'))
            """,
            (email.lower(), password_hash),
        )
        user_id = cursor.lastrowid
        conn.execute(
            "UPDATE transactions SET user_id = ? WHERE user_id IS NULL",
            (user_id,),
        )
    return user_id


def get_user_by_email(email):
    with get_db() as conn:
        return conn.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email.lower(),),
        ).fetchone()


def authenticate_user(email, password):
    user = get_user_by_email(email)
    if not user:
        return None
    if not check_password_hash(user["password_hash"], password):
        return None
    return user


def insert_transaction(user_id, amount, tx_type, category, description, date):
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO transactions (amount, type, category, description, date, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (amount, tx_type, category, description, date, user_id),
        )


def fetch_transaction(tx_id, user_id):
    with get_db() as conn:
        return conn.execute(
            """
            SELECT id, amount, type, category, description, date
            FROM transactions
            WHERE id = ? AND user_id = ?
            """,
            (tx_id, user_id),
        ).fetchone()


def update_transaction(tx_id, user_id, amount, tx_type, category, description, date):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE transactions
            SET amount = ?, type = ?, category = ?, description = ?, date = ?
            WHERE id = ? AND user_id = ?
            """,
            (amount, tx_type, category, description, date, tx_id, user_id),
        )


def delete_transaction(tx_id, user_id):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM transactions WHERE id = ? AND user_id = ?",
            (tx_id, user_id),
        )


def count_transactions(user_id, search_query=None, category=None, tx_type=None):
    clauses = []
    params = []
    clauses.append("user_id = ?")
    params.append(user_id)
    if search_query:
        clauses.append("(description LIKE ? OR category LIKE ? OR type LIKE ? OR date LIKE ?)")
        token = f"%{search_query}%"
        params.extend([token, token, token, token])
    if category:
        clauses.append("category = ?")
        params.append(category)
    if tx_type:
        clauses.append("type = ?")
        params.append(tx_type)

    clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with get_db() as conn:
        row = conn.execute(
            f"SELECT COUNT(*) AS total FROM transactions {clause}",
            params,
        ).fetchone()
    return row["total"] if row else 0


def query_transactions(user_id, search_query=None, category=None, tx_type=None, limit=20, offset=0):
    clauses = []
    params = []
    clauses.append("user_id = ?")
    params.append(user_id)
    if search_query:
        clauses.append("(description LIKE ? OR category LIKE ? OR type LIKE ? OR date LIKE ?)")
        token = f"%{search_query}%"
        params.extend([token, token, token, token])
    if category:
        clauses.append("category = ?")
        params.append(category)
    if tx_type:
        clauses.append("type = ?")
        params.append(tx_type)

    clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
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
