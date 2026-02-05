import datetime
import os
from functools import wraps

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for

from storage import (
    INCOME_CATEGORIES,
    SPENDING_CATEGORIES,
    authenticate_user,
    count_transactions,
    create_user,
    delete_transaction,
    fetch_transaction,
    get_user_by_email,
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


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def api_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "auth_required"}), 401
        return view(*args, **kwargs)

    return wrapped


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
@login_required
def index():
    today = datetime.date.today().isoformat()
    return render_template(
        "index.html",
        income_categories=INCOME_CATEGORIES,
        spending_categories=SPENDING_CATEGORIES,
        today=today,
    )


@app.route("/add", methods=["POST"])
@login_required
def add():
    payload, error = normalize_transaction(request.form)
    if error:
        flash(error)
        return redirect(url_for("index"))

    user_id = session["user_id"]
    insert_transaction(
        user_id,
        payload["amount"],
        payload["type"],
        payload["category"],
        payload["description"],
        payload["date"],
    )

    flash("Transaction added.")
    return redirect(url_for("index"))


def totals_for_period(conn, user_id, start_date):
    rows = conn.execute(
        """
        SELECT type, COALESCE(SUM(amount), 0) AS total
        FROM transactions
        WHERE date >= ? AND user_id = ?
        GROUP BY type
        """,
        (start_date, user_id),
    ).fetchall()

    totals = {"income": 0, "spending": 0}
    for row in rows:
        totals[row["type"]] = round(row["total"], 2)
    return totals


@app.route("/stats")
@login_required
def stats():
    user_id = session["user_id"]
    month_param = request.args.get("month")
    with get_db() as conn:
        all_time = totals_for_period(conn, user_id, "0000-01-01")

        periods = []
        for days in (30, 90, 120, 360):
            start_date = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
            totals = totals_for_period(conn, user_id, start_date)
            periods.append({"days": days, "totals": totals})

        recent = conn.execute(
            """
            SELECT amount, type, category, description, date
            FROM transactions
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            LIMIT 5
            """
        , (user_id,)).fetchall()

        month_rows = conn.execute(
            """
            SELECT strftime('%Y-%m', date) AS month
            FROM transactions
            WHERE user_id = ?
            GROUP BY month
            ORDER BY month DESC
            """
        , (user_id,)).fetchall()

        available_months = [row["month"] for row in month_rows]
        if month_param in available_months:
            selected_month = month_param
        else:
            selected_month = available_months[0] if available_months else datetime.date.today().strftime("%Y-%m")

        monthly_totals = conn.execute(
            """
            SELECT type, COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE strftime('%Y-%m', date) = ? AND user_id = ?
            GROUP BY type
            """,
            (selected_month, user_id),
        ).fetchall()

        monthly_by_type = {"income": 0, "spending": 0}
        for row in monthly_totals:
            monthly_by_type[row["type"]] = round(row["total"], 2)

        category_rows = conn.execute(
            """
            SELECT category, type, COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE strftime('%Y-%m', date) = ? AND user_id = ?
            GROUP BY type, category
            ORDER BY type ASC, total DESC
            """,
            (selected_month, user_id),
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


@app.route("/transactions")
@login_required
def transactions():
    user_id = session["user_id"]
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
        user_id,
        query if query else None,
        category if category else None,
        tx_type if tx_type else None,
    )
    total_pages = max((total + page_size - 1) // page_size, 1)
    if page > total_pages:
        page = total_pages

    rows = query_transactions(
        user_id,
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
@login_required
def edit_transaction(tx_id):
    user_id = session["user_id"]
    tx = fetch_transaction(tx_id, user_id)
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
            user_id,
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
@login_required
def remove_transaction(tx_id):
    user_id = session["user_id"]
    delete_transaction(tx_id, user_id)
    flash("Transaction deleted.")
    return redirect(url_for("transactions"))


@app.route("/transactions/filter")
@login_required
def transactions_filter():
    user_id = session["user_id"]
    month = (request.args.get("month") or "").strip()
    tx_type = (request.args.get("type") or "").strip().lower()
    category = (request.args.get("category") or "").strip().lower()

    clauses = ["user_id = ?"]
    params = [user_id]
    if month:
        clauses.append("strftime('%Y-%m', date) = ?")
        params.append(month)
    if tx_type:
        clauses.append("type = ?")
        params.append(tx_type)
    if category:
        clauses.append("category = ?")
        params.append(category)

    where_clause = f"WHERE {' AND '.join(clauses)}"

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


@app.route("/api/login", methods=["POST"])
def api_login():
    payload = request.get_json(silent=True) or request.form
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    user = authenticate_user(email, password)
    if not user:
        return jsonify({"error": "invalid_credentials"}), 401
    session["user_id"] = user["id"]
    session["user_email"] = user["email"]
    return jsonify({"ok": True, "user": {"id": user["id"], "email": user["email"]}})


@app.route("/api/transactions", methods=["GET", "POST"])
@api_login_required
def api_transactions():
    user_id = session["user_id"]
    if request.method == "POST":
        payload = request.get_json(silent=True) or request.form
        tx, error = normalize_transaction(payload)
        if error:
            return jsonify({"error": error}), 400
        insert_transaction(
            user_id,
            tx["amount"],
            tx["type"],
            tx["category"],
            tx["description"],
            tx["date"],
        )
        return jsonify({"ok": True, "transaction": tx}), 201

    try:
        limit = max(int(request.args.get("limit", "200")), 1)
    except ValueError:
        limit = 200
    try:
        offset = max(int(request.args.get("offset", "0")), 0)
    except ValueError:
        offset = 0

    rows = query_transactions(user_id, limit=limit, offset=offset)
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


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = authenticate_user(email, password)
        if not user:
            flash("Invalid email or password.")
            return redirect(url_for("login"))
        session["user_id"] = user["id"]
        session["user_email"] = user["email"]
        return redirect(url_for("stats"))
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        if not email or "@" not in email:
            flash("Please enter a valid email.")
            return redirect(url_for("signup"))
        if len(password) < 8:
            flash("Password must be at least 8 characters.")
            return redirect(url_for("signup"))

        if get_user_by_email(email):
            flash("Account already exists. Please log in.")
            return redirect(url_for("login"))
        try:
            user_id = create_user(email, password)
        except Exception:
            flash("Email already in use.")
            return redirect(url_for("signup"))

        session["user_id"] = user_id
        session["user_email"] = email
        return redirect(url_for("stats"))

    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
