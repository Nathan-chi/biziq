import sqlite3
import json

def check_db():
    conn = sqlite3.connect('biziq.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM plans')
    plans = cursor.fetchall()
    print(f"Total plans: {len(plans)}")
    for p in plans:
        print(f"ID: {p[0]}, Name: {p[1]}, Amount: {p[2]}")
        try:
            features = json.loads(p[4]) if p[4] else []
            print(f"  Features: {features}")
        except Exception as e:
            print(f"  Features parsing error: {e} | Raw: {p[4]}")
    conn.close()

if __name__ == "__main__":
    check_db()
