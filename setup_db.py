import sqlite3

conn = sqlite3.connect("farmlink.db")
cur = conn.cursor()

cur.executescript("""
CREATE TABLE IF NOT EXISTS members (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    location      TEXT NOT NULL,
    farming_type  TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name      TEXT NOT NULL UNIQUE,
    price     INTEGER NOT NULL,
    in_stock  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id   INTEGER REFERENCES members(id),
    total       INTEGER NOT NULL,
    status      TEXT NOT NULL DEFAULT 'unpaid',
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL REFERENCES orders(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL,
    unit_price  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      INTEGER NOT NULL REFERENCES orders(id),
    method        TEXT NOT NULL,
    amount        INTEGER NOT NULL,
    provider_ref  TEXT,
    status        TEXT NOT NULL DEFAULT 'pending',
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
""")

products = [
    ("Maize Seeds (5kg bag)", 150),
    ("Vegetable Seeds (packet)", 30),
    ("Fertilizer - Compound D (50kg)", 650),
    ("Fertilizer - Urea (50kg)", 600),
    ("Slasher", 50),
]

cur.executemany(
    "INSERT OR IGNORE INTO products (name, price) VALUES (?, ?)",
    products
)

conn.commit()
conn.close()
print("Database ready: farmlink.db")