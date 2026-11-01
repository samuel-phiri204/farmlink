import sqlite3

conn = sqlite3.connect("farmlink.db")
conn.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name   TEXT NOT NULL,
    email       TEXT NOT NULL,
    subject     TEXT NOT NULL,
    message     TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()
conn.close()
print("Messages table ready")