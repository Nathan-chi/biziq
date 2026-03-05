import sqlite3
db = sqlite3.connect(r"c:\Users\TFC\ai\backend\biziq.db")
db.execute("UPDATE users SET phone='2348077299974' WHERE email='nathanojaobochi234@gmail.com'")
db.commit()
rows = db.execute("SELECT id, email, phone FROM users").fetchall()
for r in rows:
    print(r)
db.close()
print("Done!")
