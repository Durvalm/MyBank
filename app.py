import datetime
import json
import os
import shutil

from flask import Flask, flash, redirect, render_template, request, url_for

from storage import (
    DATA_TXT_PATH,
    INCOME_CATEGORIES,
    SPENDING_CATEGORIES,
    ensure_seeded_from_txt,
    get_db,
    init_db,
    insert_transaction,
)

app = Flask(__name__)
app.secret_key = os.environ.get("MYBANK_SECRET", "dev-secret")
_db_initialized = False


@app.before_request
def setup_db_once():
    global _db_initialized
    if not _db_initialized:
        init_db()
        ensure_seeded_from_txt()
        _db_initialized = True


def valid_category(tx_type, category):
    if tx_type == "income":
        return category in INCOME_CATEGORIES
    if tx_type == "spending":
        return category in SPENDING_CATEGORIES
    return False


def parse_amount(raw):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


@app.route("/")
def index():
    today = datetime.date.today().isoformat()
    return render_template(
        "index.html",
        income_categories=INCOME_CATEGORIES,
        spending_categories=SPENDING_CATEGORIES,
        today=today,
    )


@app.route("/add", methods=["POST"])
def add():
    amount = parse_amount(request.form.get("amount"))
    tx_type = (request.form.get("type") or "").lower()
    category = (request.form.get("category") or "").lower()
    description = request.form.get("description") or ""
    date = request.form.get("date") or datetime.date.today().isoformat()

    if amount is None or amount <= 0:
        flash("Amount must be a positive number.")
        return redirect(url_for("index"))

    if tx_type not in ("income", "spending"):
        flash("Type must be income or spending.")
        return redirect(url_for("index"))

    if not valid_category(tx_type, category):
        flash("Please pick a valid category.")
        return redirect(url_for("index"))

    if not description.strip():
        description = "(no description)"

    insert_transaction(amount, tx_type, category, description, date)

    flash("Transaction added.")
    return redirect(url_for("index"))


def totals_for_period(conn, start_date):
    rows = conn.execute(
        """
        SELECT type, COALESCE(SUM(amount), 0) AS total
        FROM transactions
        WHERE date >= ?
        GROUP BY type
        """,
        (start_date,),
    ).fetchall()

    totals = {"income": 0, "spending": 0}
    for row in rows:
        totals[row["type"]] = round(row["total"], 2)
    return totals


@app.route("/stats")
def stats():
    with get_db() as conn:
        all_time = totals_for_period(conn, "0000-01-01")

        periods = []
        for days in (30, 90, 120, 360):
            start_date = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
            totals = totals_for_period(conn, start_date)
            periods.append({"days": days, "totals": totals})

        recent = conn.execute(
            """
            SELECT amount, type, category, description, date
            FROM transactions
            ORDER BY date DESC, id DESC
            LIMIT 20
            """
        ).fetchall()

    return render_template(
        "stats.html",
        all_time=all_time,
        periods=periods,
        recent=recent,
    )


@app.route("/export")
def export_data():
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT amount, type, category, description, date
            FROM transactions
            ORDER BY date ASC, id ASC
            """
        ).fetchall()

    if os.path.exists(DATA_TXT_PATH):
        shutil.copyfile(DATA_TXT_PATH, DATA_TXT_PATH + ".bak")

    with open(DATA_TXT_PATH, "w") as file:
        for row in rows:
            payload = {
                "amount": row["amount"],
                "type": row["type"],
                "date": row["date"],
                "category": row["category"],
                "description": row["description"],
            }
            file.write(json.dumps(payload) + "\n")

    flash("Exported backup to data.txt (previous file saved as data.txt.bak).")
    return redirect(url_for("stats"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
