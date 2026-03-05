import sqlite3
from datetime import datetime

db = sqlite3.connect(r"c:\Users\TFC\ai\backend\biziq.db")
db.row_factory = sqlite3.Row

# Check user ID for this phone
user = db.execute("SELECT id, email, phone FROM users WHERE phone='2348077299974'").fetchone()
if user:
    print(f"User found: ID={user['id']}, email={user['email']}, phone={user['phone']}")
    
    # Get their recent transactions
    txns = db.execute(
        "SELECT * FROM transactions_v3 WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
        (user['id'],)
    ).fetchall()
    
    print(f"\nRecent transactions ({len(txns)} found):")
    for t in txns:
        # Use 'N' for Naira to avoid encoding issues
        print(f"  {t['date']} | {t['type']} | {t['description']} | N{t['amount']:,.0f}")
else:
    print("No user found with phone 2348077299974")

db.close()
