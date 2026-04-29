import os
import sqlite3
from calendar import monthrange
from datetime import date

from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("MYBANK_DB_PATH", os.path.join(BASE_DIR, "mybank.db"))

INCOME_CATEGORIES = ["work", "business", "financial_aid", "family", "investments", "sell", "other"]
SPENDING_CATEGORIES = [
    "transportation",
    "personal_care",
    "business",
    "groceries",
    "eating_out",
    "travel",
    "shopping",
    "gift_donation",
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recurring_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                billing_day INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                last_charged_date TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
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


def get_user_by_id(user_id):
    with get_db() as conn:
        return conn.execute(
            "SELECT id, email FROM users WHERE id = ?",
            (user_id,),
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


def insert_recurring_expense(user_id, amount, category, description, billing_day, start_date, active=1):
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO recurring_expenses (
                amount, category, description, billing_day, start_date, active, user_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (amount, category, description, billing_day, start_date, int(active), user_id),
        )
    return cursor.lastrowid


def list_recurring_expenses(user_id):
    with get_db() as conn:
        return conn.execute(
            """
            SELECT id, amount, category, description, billing_day, start_date, last_charged_date, active
            FROM recurring_expenses
            WHERE user_id = ?
            ORDER BY active DESC, billing_day ASC, description ASC
            """,
            (user_id,),
        ).fetchall()


def fetch_recurring_expense(recurring_id, user_id):
    with get_db() as conn:
        return conn.execute(
            """
            SELECT id, amount, category, description, billing_day, start_date, last_charged_date, active
            FROM recurring_expenses
            WHERE id = ? AND user_id = ?
            """,
            (recurring_id, user_id),
        ).fetchone()


def update_recurring_expense(
    recurring_id, user_id, amount, category, description, billing_day, start_date, active
):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE recurring_expenses
            SET amount = ?, category = ?, description = ?, billing_day = ?, start_date = ?, active = ?
            WHERE id = ? AND user_id = ?
            """,
            (amount, category, description, billing_day, start_date, int(active), recurring_id, user_id),
        )


def set_recurring_expense_active(recurring_id, user_id, active):
    with get_db() as conn:
        conn.execute(
            """
            UPDATE recurring_expenses
            SET active = ?
            WHERE id = ? AND user_id = ?
            """,
            (int(active), recurring_id, user_id),
        )


def delete_recurring_expense(recurring_id, user_id):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM recurring_expenses WHERE id = ? AND user_id = ?",
            (recurring_id, user_id),
        )


def _add_month(dt):
    if dt.month == 12:
        return date(dt.year + 1, 1, 1)
    return date(dt.year, dt.month + 1, 1)


def _charge_date_for_month(year, month, billing_day):
    last_day = monthrange(year, month)[1]
    return date(year, month, min(billing_day, last_day))


def process_due_recurring_expenses(user_id, today=None):
    today = today or date.today()
    if isinstance(today, str):
        today = date.fromisoformat(today)

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, amount, category, description, billing_day, start_date, last_charged_date
            FROM recurring_expenses
            WHERE user_id = ? AND active = 1 AND start_date <= ?
            ORDER BY id ASC
            """,
            (user_id, today.isoformat()),
        ).fetchall()

        created = 0
        for row in rows:
            start_date = date.fromisoformat(row["start_date"])
            last_charged_date = (
                date.fromisoformat(row["last_charged_date"]) if row["last_charged_date"] else None
            )
            cursor_month = date(start_date.year, start_date.month, 1)
            latest_charge_date = last_charged_date

            while cursor_month <= today:
                charge_date = _charge_date_for_month(
                    cursor_month.year, cursor_month.month, row["billing_day"]
                )
                should_charge = charge_date >= start_date and charge_date <= today
                if last_charged_date:
                    should_charge = should_charge and charge_date > last_charged_date

                if should_charge:
                    conn.execute(
                        """
                        INSERT INTO transactions (amount, type, category, description, date, user_id)
                        VALUES (?, 'spending', ?, ?, ?, ?)
                        """,
                        (
                            row["amount"],
                            row["category"],
                            row["description"],
                            charge_date.isoformat(),
                            user_id,
                        ),
                    )
                    created += 1
                    latest_charge_date = charge_date

                cursor_month = _add_month(cursor_month)

            if latest_charge_date and latest_charge_date != last_charged_date:
                conn.execute(
                    """
                    UPDATE recurring_expenses
                    SET last_charged_date = ?
                    WHERE id = ? AND user_id = ?
                    """,
                    (latest_charge_date.isoformat(), row["id"], user_id),
                )

    return created


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
