"""
BizIQ - Authentication System
Handles user registration, login, and JWT token security
"""

import sqlite3
import hashlib
import secrets
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Optional

load_dotenv()

# ─────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────

SECRET_KEY = os.environ.get("BIZIQ_SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)  # Fallback if not set in .env

TOKEN_EXPIRE_DAYS = 30


# ─────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect("biziq.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            business_name TEXT NOT NULL,
            industry TEXT DEFAULT 'Retail',
            location TEXT DEFAULT 'Nigeria',
            currency TEXT DEFAULT 'NGN',
            plan TEXT DEFAULT 'free',        -- free / pro / enterprise
            ai_api_key TEXT,                 -- User's own AI brain key (Groq/Anthropic)
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        )
    """)

    # Sessions / tokens table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Update transactions to be per-user
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            category TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


init_auth_db()


# ─────────────────────────────────────────────────────────
# PASSWORD HASHING
# ─────────────────────────────────────────────────────────

def hash_password(password: str, salt: Optional[str] = None) -> tuple:
    """Hash a password with a random salt. Returns (hash, salt)."""
    if salt is None:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=260000  # NIST recommended minimum
    ).hex()
    return pw_hash, salt


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash:salt string."""
    try:
        pw_hash, salt = stored_hash.split(":")
        computed, _ = hash_password(password, salt)
        return secrets.compare_digest(computed, pw_hash)  # Timing-safe comparison
    except Exception:
        return False


def make_password_hash(password: str) -> str:
    """Create a storable hash:salt string from a plain password."""
    pw_hash, salt = hash_password(password)
    return f"{pw_hash}:{salt}"


# ─────────────────────────────────────────────────────────
# TOKEN MANAGEMENT
# ─────────────────────────────────────────────────────────

def create_token(user_id: int) -> str:
    """Generate a secure session token and store it."""
    token = secrets.token_urlsafe(48)
    expires_at = (datetime.now() + timedelta(days=TOKEN_EXPIRE_DAYS)).isoformat()

    conn = get_db()
    # Clean up old tokens for this user first
    conn.execute("DELETE FROM sessions WHERE user_id = ? AND expires_at < ?", (user_id, datetime.now().isoformat()))
    conn.execute("INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)", (user_id, token, expires_at))
    conn.commit()
    conn.close()
    return token


def validate_token(token: str) -> Optional[dict]:
    """Validate a token and return the user if valid."""
    if not token:
        return None
    conn = get_db()
    row = conn.execute("""
        SELECT u.*, s.expires_at FROM users u
        JOIN sessions s ON u.id = s.user_id
        WHERE s.token = ? AND s.expires_at > ?
    """, (token, datetime.now().isoformat())).fetchone()
    conn.close()
    return dict(row) if row else None


def revoke_token(token: str):
    """Logout — delete the session token."""
    conn = get_db()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────
# USER MANAGEMENT
# ─────────────────────────────────────────────────────────

def create_user(email: str, password: str, full_name: str, business_name: str,
                industry: str = "Retail", location: str = "Nigeria") -> dict:
    """Register a new user. Returns user dict or raises ValueError."""
    # Validate
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if "@" not in email:
        raise ValueError("Invalid email address")

    conn = get_db()

    # Check if email already exists
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email.lower(),)).fetchone()
    if existing:
        conn.close()
        raise ValueError("An account with this email already exists")

    pw_hash = make_password_hash(password)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (email, password_hash, full_name, business_name, industry, location)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (email.lower(), pw_hash, full_name, business_name, industry, location))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    return get_user_by_id(user_id)


def login_user(email: str, password: str) -> Optional[dict]:
    """Authenticate a user. Returns user dict + token or None."""
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
    conn.close()

    if not row:
        return None
    user = dict(row)

    if not verify_password(password, user["password_hash"]):
        return None

    # Update last login
    conn = get_db()
    conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.now().isoformat(), user["id"]))
    conn.commit()
    conn.close()

    token = create_token(user["id"])
    user.pop("password_hash", None)  # Never return password hash
    return {"user": user, "token": token}


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return None
    user = dict(row)
    user.pop("password_hash", None)
    return user


def update_user_profile(user_id: int, business_name: str, industry: str,
                         location: str, currency: str, full_name: str, ai_api_key: Optional[str] = None) -> dict:
    conn = get_db()
    conn.execute("""
        UPDATE users SET business_name=?, industry=?, location=?, currency=?, full_name=?, ai_api_key=?
        WHERE id=?
    """, (business_name, industry, location, currency, full_name, ai_api_key, user_id))
    conn.commit()
    conn.close()
    return get_user_by_id(user_id)


def change_password(user_id: int, current_password: str, new_password: str) -> bool:
    """Change a user's password after verifying current one."""
    conn = get_db()
    row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    if not row or not verify_password(current_password, row["password_hash"]):
        return False

    if len(new_password) < 8:
        raise ValueError("New password must be at least 8 characters")

    new_hash = make_password_hash(new_password)
    conn = get_db()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
    conn.commit()
    conn.close()
    return True


# ─────────────────────────────────────────────────────────
# PER-USER TRANSACTIONS
# ─────────────────────────────────────────────────────────

def get_user_transactions(user_id: int, limit: int = 50, type_filter: Optional[str] = None) -> list:
    conn = get_db()
    if type_filter:
        rows = conn.execute("""
            SELECT * FROM transactions_v2 WHERE user_id=? AND type=?
            ORDER BY date DESC LIMIT ?
        """, (user_id, type_filter, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM transactions_v2 WHERE user_id=?
            ORDER BY date DESC LIMIT ?
        """, (user_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_user_transaction(user_id: int, type_: str, description: str,
                          amount: float, date: str, category: Optional[str]) -> int:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO transactions_v2 (user_id, type, description, amount, date, category)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, type_, description, amount, date, category))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def delete_user_transaction(user_id: int, transaction_id: int) -> bool:
    """Only delete if the transaction belongs to this user."""
    conn = get_db()
    result = conn.execute("""
        DELETE FROM transactions_v2 WHERE id=? AND user_id=?
    """, (transaction_id, user_id))
    conn.commit()
    deleted = result.rowcount > 0
    conn.close()
    return deleted


def get_user_summary(user_id: int) -> dict:
    conn = get_db()
    m = datetime.now().strftime("%Y-%m")
    # Monthly Revenue
    revenue = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions_v2 WHERE user_id=? AND type='sales' AND date LIKE ?",
        (user_id, f"{m}%")
    ).fetchone()[0]

    # Operating Expenses (Rent, Staff, Fuel - money that is 'gone')
    op_expenses = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions_v2 WHERE user_id=? AND type='expense' AND date LIKE ?",
        (user_id, f"{m}%")
    ).fetchone()[0]
    
    # Inventory Purchases (Buying stock - money spent but value remains in shop)
    inv_purchases = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions_v2 WHERE user_id=? AND type='inventory' AND date LIKE ?",
        (user_id, f"{m}%")
    ).fetchone()[0]

    # Total stock value (ever recorded as inventory)
    total_inv_value = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions_v2 WHERE user_id=? AND type='inventory'",
        (user_id,)
    ).fetchone()[0]
    conn.close()

    # Calculation logic for simple dashboard:
    # Net Profit = Revenue - Operating Expenses (Staff, Rent) - Inventory Purchase (Cost of Stock)
    total_outflow = op_expenses + inv_purchases
    net = revenue - total_outflow
    margin = round((net / revenue * 100), 1) if revenue > 0 else 0
    
    return {
        "monthly_revenue": revenue,
        "operating_expenses": op_expenses,
        "inventory_purchases": inv_purchases,
        "monthly_expenses": total_outflow, # For old chart compatibility
        "net_profit": net, 
        "inventory_value": total_inv_value, 
        "profit_margin": margin
    }


def get_user_by_day(user_id: int, days: int = 7) -> list:
    conn = get_db()
    rows = conn.execute("""
        SELECT date,
               SUM(CASE WHEN type='sales'   THEN amount ELSE 0 END) as revenue,
               SUM(CASE WHEN type='expense' OR type='inventory' THEN amount ELSE 0 END) as expenses
        FROM transactions_v2 WHERE user_id=?
        GROUP BY date ORDER BY date DESC LIMIT ?
    """, (user_id, days)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────
# SEED DATA
# ─────────────────────────────────────────────────────────

def _seed_sample_data(conn, user_id: int):
    """Give new users some sample transactions to explore the app."""
    sample = [
        ("sales",   "Daily sales revenue",    142000, "2026-03-03", "Revenue"),
        ("expense", "Flour purchase (50kg)",  285000, "2026-03-03", "Inventory"),
        ("sales",   "Daily sales revenue",    118500, "2026-03-02", "Revenue"),
        ("expense", "Staff wages",             95000, "2026-03-02", "Operations"),
        ("expense", "Inventory restock",      320000, "2026-03-01", "Inventory"),
        ("sales",   "Daily sales revenue",    134000, "2026-03-01", "Revenue"),
        ("expense", "Electricity bill",        18000, "2026-02-28", "Utilities"),
        ("sales",   "Daily sales revenue",    187000, "2026-02-28", "Revenue"),
        ("sales",   "Daily sales revenue",    156000, "2026-02-27", "Revenue"),
        ("expense", "Transport costs",         22000, "2026-02-27", "Operations"),
        ("sales",   "Daily sales revenue",    198000, "2026-02-26", "Revenue"),
        ("expense", "Packaging materials",     35000, "2026-02-26", "Operations"),
    ]
    conn.executemany("""
        INSERT INTO transactions_v2 (user_id, type, description, amount, date, category)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [(user_id, *row) for row in sample])
    conn.commit()
