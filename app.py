import datetime
import os

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from storage import (
    INCOME_CATEGORIES,
    SPENDING_CATEGORIES,
    count_transactions,
    delete_transaction,
    fetch_transaction,
    get_db,
    init_db,
    insert_transaction,
    query_transactions,
    update_transaction,
)

app = Flask(__name__)
app.secret_key = os.environ.get("MYBANK_SECRET", "dev-secret")
_db_initialized = False


@app.before_request
def setup_db_once():
    global _db_initialized
    if not _db_initialized:
        init_db()
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


def normalize_transaction(form):
    amount = parse_amount(form.get("amount"))
    tx_type = (form.get("type") or "").lower()
    category = (form.get("category") or "").lower()
    description = form.get("description") or ""
    date = form.get("date") or datetime.date.today().isoformat()

    if amount is None or amount <= 0:
        return None, "Amount must be a positive number."

    if tx_type not in ("income", "spending"):
        return None, "Type must be income or spending."

    if not valid_category(tx_type, category):
        return None, "Please pick a valid category."

    if not description.strip():
        description = "(no description)"

    return {
        "amount": amount,
        "type": tx_type,
        "category": category,
        "description": description,
        "date": date,
    }, None


@app.template_filter("currency")
def currency_filter(value):
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def build_pagination(current_page, total_pages, window=2):
    if total_pages <= 1:
        return []
    pages = []
    start = max(1, current_page - window)
    end = min(total_pages, current_page + window)

    if start > 1:
        pages.append(1)
        if start > 2:
            pages.append(None)

    pages.extend(range(start, end + 1))

    if end < total_pages:
        if end < total_pages - 1:
            pages.append(None)
        pages.append(total_pages)

    return pages


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
    payload, error = normalize_transaction(request.form)
    if error:
        flash(error)
        return redirect(url_for("index"))

    insert_transaction(
        payload["amount"],
        payload["type"],
        payload["category"],
        payload["description"],
        payload["date"],
    )

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
    month_param = request.args.get("month")
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
            LIMIT 5
            """
        ).fetchall()

        month_rows = conn.execute(
            """
            SELECT strftime('%Y-%m', date) AS month
            FROM transactions
            GROUP BY month
            ORDER BY month DESC
            """
        ).fetchall()

        available_months = [row["month"] for row in month_rows]
        if month_param in available_months:
            selected_month = month_param
        else:
            selected_month = available_months[0] if available_months else datetime.date.today().strftime("%Y-%m")

        monthly_totals = conn.execute(
            """
            SELECT type, COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE strftime('%Y-%m', date) = ?
            GROUP BY type
            """,
            (selected_month,),
        ).fetchall()

        monthly_by_type = {"income": 0, "spending": 0}
        for row in monthly_totals:
            monthly_by_type[row["type"]] = round(row["total"], 2)

        category_rows = conn.execute(
            """
            SELECT category, type, COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE strftime('%Y-%m', date) = ?
            GROUP BY type, category
            ORDER BY type ASC, total DESC
            """,
            (selected_month,),
        ).fetchall()

        category_breakdown = {"income": [], "spending": []}
        for row in category_rows:
            category_breakdown[row["type"]].append(
                {"category": row["category"], "total": round(row["total"], 2)}
            )

    return render_template(
        "stats.html",
        all_time=all_time,
        periods=periods,
        recent=recent,
        available_months=available_months,
        selected_month=selected_month,
        monthly_by_type=monthly_by_type,
        category_breakdown=category_breakdown,
    )


@app.route("/transactions/filter")
def transactions_filter():
    month = (request.args.get("month") or "").strip()
    tx_type = (request.args.get("type") or "").strip().lower()
    category = (request.args.get("category") or "").strip().lower()

    clauses = []
    params = []
    if month:
        clauses.append("strftime('%Y-%m', date) = ?")
        params.append(month)
    if tx_type:
        clauses.append("type = ?")
        params.append(tx_type)
    if category:
        clauses.append("category = ?")
        params.append(category)

    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT id, amount, type, category, description, date
            FROM transactions
            {where_clause}
            ORDER BY date DESC, id DESC
            """,
            params,
        ).fetchall()

    payload = [
        {
            "id": row["id"],
            "amount": row["amount"],
            "type": row["type"],
            "category": row["category"],
            "description": row["description"],
            "date": row["date"],
        }
        for row in rows
    ]

    return jsonify(payload)


@app.route("/transactions")
def transactions():
    query = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip().lower()
    tx_type = (request.args.get("type") or "").strip().lower()
    page = request.args.get("page", "1")
    try:
        page = max(int(page), 1)
    except ValueError:
        page = 1

    page_size = 20
    total = count_transactions(
        query if query else None,
        category if category else None,
        tx_type if tx_type else None,
    )
    total_pages = max((total + page_size - 1) // page_size, 1)
    if page > total_pages:
        page = total_pages

    rows = query_transactions(
        query if query else None,
        category if category else None,
        tx_type if tx_type else None,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    pages = build_pagination(page, total_pages)

    return render_template(
        "transactions.html",
        rows=rows,
        query=query,
        selected_category=category,
        selected_type=tx_type,
        page=page,
        total_pages=total_pages,
        total=total,
        pages=pages,
        income_categories=INCOME_CATEGORIES,
        spending_categories=SPENDING_CATEGORIES,
    )


@app.route("/transactions/<int:tx_id>/edit", methods=["GET", "POST"])
def edit_transaction(tx_id):
    tx = fetch_transaction(tx_id)
    if not tx:
        flash("Transaction not found.")
        return redirect(url_for("transactions"))

    if request.method == "POST":
        payload, error = normalize_transaction(request.form)
        if error:
            flash(error)
            return redirect(url_for("edit_transaction", tx_id=tx_id))

        update_transaction(
            tx_id,
            payload["amount"],
            payload["type"],
            payload["category"],
            payload["description"],
            payload["date"],
        )
        flash("Transaction updated.")
        return redirect(url_for("transactions"))

    return render_template(
        "edit.html",
        tx=tx,
        income_categories=INCOME_CATEGORIES,
        spending_categories=SPENDING_CATEGORIES,
    )


@app.route("/transactions/<int:tx_id>/delete", methods=["POST"])
def remove_transaction(tx_id):
    delete_transaction(tx_id)
    flash("Transaction deleted.")
    return redirect(url_for("transactions"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
