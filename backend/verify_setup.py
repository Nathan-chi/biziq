import sqlite3
import os

db_path = 'biziq.db'
conn = sqlite3.connect(db_path)
try:
    # Double check nathan's phone
    email = 'nathanojaobochi234@gmail.com'
    phone = '2348077299974'
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET phone = ? WHERE email = ?", (phone, email))
    conn.commit()
    print(f"Update done for {email}: {phone}")
    
    # Show all linked phones
    cursor.execute("SELECT email, phone FROM users WHERE phone IS NOT NULL")
    for row in cursor.fetchall():
        print(f"Linked: {row[0]} -> {row[1]}")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
