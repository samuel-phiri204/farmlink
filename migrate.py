import sqlite3

conn = sqlite3.connect("farmlink.db")
conn.execute("ALTER TABLE orders ADD COLUMN customer_name TEXT")
conn.execute("ALTER TABLE orders ADD COLUMN customer_phone TEXT")
conn.commit()
conn.close()
print("Orders table updated")