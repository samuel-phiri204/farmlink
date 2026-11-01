import hmac
import os
import sqlite3
from functools import wraps
from flask import (Flask, Response, abort, jsonify, render_template_string,
                   request, send_from_directory)

app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "farmlink.db")

# Only these file types can be opened from the browser,
# so app.py and farmlink.db stay private.
ALLOWED = (".html", ".css", ".js", ".jpg", ".jpeg", ".png", ".webp", ".svg", ".ico")
FARMING_TYPES = ("Crop Farming", "Livestock Farming", "Mixed Farming")
PAY_METHODS = ("mtn_momo", "airtel_money", "cash")
SUBJECTS = ("Membership", "Farm Inputs", "Farm Products", "General Inquiry")


@app.route("/")
def home():
    return send_from_directory(BASE, "index.html")


@app.route("/<path:filename>")
def pages(filename):
    if not filename.lower().endswith(ALLOWED):
        abort(404)
    return send_from_directory(BASE, filename)


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    location = (data.get("location") or "").strip()
    farming_type = (data.get("farming_type") or "").strip()

    if not (name and email and location and farming_type):
        return jsonify(error="Please fill in all fields."), 400
    if "@" not in email:
        return jsonify(error="Please enter a valid email address."), 400
    if farming_type not in FARMING_TYPES:
        return jsonify(error="Please choose a farming type."), 400

    conn = sqlite3.connect(DB)
    try:
        conn.execute(
            "INSERT INTO members (full_name, email, location, farming_type) "
            "VALUES (?, ?, ?, ?)",
            (name, email, location, farming_type),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="This email is already registered."), 409
    finally:
        conn.close()

    return jsonify(message="Thank you! Your interest has been registered."), 201


@app.route("/api/order", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    method = data.get("method")
    items = data.get("items")

    if not name or len(phone) < 9:
        return jsonify(error="Please enter your name and phone number."), 400
    if method not in PAY_METHODS:
        return jsonify(error="Please choose a payment method."), 400
    if not isinstance(items, list) or not items:
        return jsonify(error="Your cart is empty."), 400

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        lines, total = [], 0
        for it in items:
            try:
                pid, qty = int(it["id"]), int(it["qty"])
            except (KeyError, TypeError, ValueError):
                return jsonify(error="Invalid cart."), 400
            if not 1 <= qty <= 100:
                return jsonify(error="Invalid quantity."), 400
            row = conn.execute(
                "SELECT price FROM products WHERE id = ? AND in_stock = 1", (pid,)
            ).fetchone()
            if row is None:
                return jsonify(error="A product in your cart is unavailable."), 400
            lines.append((pid, qty, row["price"]))
            total += qty * row["price"]

        cur = conn.execute(
            "INSERT INTO orders (customer_name, customer_phone, total) VALUES (?, ?, ?)",
            (name, phone, total),
        )
        order_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price) "
            "VALUES (?, ?, ?, ?)",
            [(order_id, pid, qty, price) for pid, qty, price in lines],
        )
        conn.execute(
            "INSERT INTO payments (order_id, method, amount) VALUES (?, ?, ?)",
            (order_id, method, total),
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify(order_id=order_id, total=total), 201


@app.route("/api/contact", methods=["POST"])
def contact():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()

    if not (name and email and subject and message):
        return jsonify(error="Please fill in all fields."), 400
    if "@" not in email:
        return jsonify(error="Please enter a valid email address."), 400
    if subject not in SUBJECTS:
        return jsonify(error="Please choose a subject."), 400
    if len(message) > 2000 or len(name) > 100:
        return jsonify(error="Your message is too long."), 400

    conn = sqlite3.connect(DB)
    try:
        conn.execute(
            "INSERT INTO messages (full_name, email, subject, message) "
            "VALUES (?, ?, ?, ?)",
            (name, email, subject, message),
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify(message="Thank you! We have received your message."), 201


# ---------- Admin (read-only) ----------

def get_admins():
    users = {}
    for pair in os.environ.get("ADMIN_USERS", "").split(","):
        if ":" in pair:
            u, p = pair.split(":", 1)
            users[u.strip()] = p.strip()
    return users


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        admins = get_admins()
        ok = (
            auth is not None
            and auth.username in admins
            and hmac.compare_digest(
                (auth.password or "").encode(), admins[auth.username].encode()
            )
        )
        if not ok:
            return Response(
                "Login required", 401,
                {"WWW-Authenticate": 'Basic realm="FarmLink Admin"'},
            )
        return view(*args, **kwargs)
    return wrapper


ADMIN_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex">
  <title>FarmLink Admin</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; color: #263b2b; }
    h1, h2 { color: #1f4d33; }
    .wrap { overflow-x: auto; }
    table { border-collapse: collapse; width: 100%; margin-bottom: 30px; }
    th, td { border: 1px solid #ccc; padding: 8px; text-align: left; font-size: 14px; vertical-align: top; }
    th { background: #1f4d33; color: #fff; }
  </style>
</head>
<body>
  <h1>FarmLink Admin</h1>

  <h2>Members ({{ members|length }})</h2>
  <div class="wrap"><table>
    <tr><th>ID</th><th>Name</th><th>Email</th><th>Location</th><th>Farming</th><th>Status</th><th>Date</th></tr>
    {% for m in members %}
    <tr><td>{{ m.id }}</td><td>{{ m.full_name }}</td><td>{{ m.email }}</td>
        <td>{{ m.location }}</td><td>{{ m.farming_type }}</td><td>{{ m.status }}</td><td>{{ m.created_at }}</td></tr>
    {% endfor %}
  </table></div>

  <h2>Orders ({{ orders|length }})</h2>
  <div class="wrap"><table>
    <tr><th>ID</th><th>Name</th><th>Phone</th><th>Total (K)</th><th>Method</th><th>Payment</th><th>Date</th></tr>
    {% for o in orders %}
    <tr><td>{{ o.id }}</td><td>{{ o.customer_name }}</td><td>{{ o.customer_phone }}</td>
        <td>{{ o.total }}</td><td>{{ o.method }}</td><td>{{ o.pay_status }}</td><td>{{ o.created_at }}</td></tr>
    {% endfor %}
  </table></div>

  <h2>Messages ({{ messages|length }})</h2>
  <div class="wrap"><table>
    <tr><th>ID</th><th>Name</th><th>Email</th><th>Subject</th><th>Message</th><th>Date</th></tr>
    {% for g in messages %}
    <tr><td>{{ g.id }}</td><td>{{ g.full_name }}</td><td>{{ g.email }}</td>
        <td>{{ g.subject }}</td><td>{{ g.message }}</td><td>{{ g.created_at }}</td></tr>
    {% endfor %}
  </table></div>
</body>
</html>
"""


@app.route("/admin")
@require_admin
def admin():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    members = conn.execute(
        "SELECT id, full_name, email, location, farming_type, status, created_at "
        "FROM members ORDER BY id DESC"
    ).fetchall()
    orders = conn.execute(
        "SELECT o.id, o.customer_name, o.customer_phone, o.total, o.created_at, "
        "p.method, p.status AS pay_status "
        "FROM orders o LEFT JOIN payments p ON p.order_id = o.id "
        "ORDER BY o.id DESC"
    ).fetchall()
    messages = conn.execute(
        "SELECT id, full_name, email, subject, message, created_at "
        "FROM messages ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return render_template_string(
        ADMIN_PAGE, members=members, orders=orders, messages=messages
    )


if __name__ == "__main__":
    app.run(debug=True)