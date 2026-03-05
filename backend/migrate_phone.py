import sqlite3

db_path = r'c:\Users\TFC\ai\backend\biziq.db'
conn = sqlite3.connect(db_path)

# Add phone column if it doesn't exist
try:
    conn.execute('ALTER TABLE users ADD COLUMN phone TEXT')
    conn.commit()
    print('Column "phone" added.')
except sqlite3.OperationalError:
    print('Column "phone" already exists.')

# Link real WhatsApp number to the main account
conn.execute(
    "UPDATE users SET phone = '2348077299974' WHERE email = 'nathanojaobochi234@gmail.com'"
)
conn.commit()

# Confirm
cursor = conn.cursor()
cursor.execute("SELECT id, email, full_name, phone FROM users")
print("\nCurrent users:")
for row in cursor.fetchall():
    print(f"  ID={row[0]}  email={row[1]}  name={row[2]}  phone={row[3]}")

conn.close()
print("\nDone!")
