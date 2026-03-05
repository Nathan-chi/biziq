import hashlib
import secrets
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, ForeignKey, DateTime, text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()

# ─────────────────────────────────────────────────────────
# CONFIG & DATABASE (SUPABASE / POSTGRES)
# ─────────────────────────────────────────────────────────

SECRET_KEY = os.environ.get("BIZIQ_SECRET_KEY", "biziq-default-secret-key-12345")
DATABASE_URL = os.environ.get("DATABASE_URL")

# If no Cloud DB is found, fallback to local SQLite (for local testing)
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./biziq.db"
# Fix for Render (Postgres URL must start with postgresql://)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

TOKEN_EXPIRE_DAYS = 30

# ─────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    business_name = Column(String, nullable=False)
    industry = Column(String, default="Retail")
    location = Column(String, default="Nigeria")
    currency = Column(String, default="NGN")
    plan = Column(String, default="free")
    ai_api_key = Column(String, nullable=True)
    phone = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

class UserSession(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Transaction(Base):
    __tablename__ = "transactions_v3" # New version for Postgres
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False) # sales | expense | inventory
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(String, nullable=False) # YYYY-MM-DD
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Plan(Base):
    __tablename__ = "plans"
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    amount = Column(Float, nullable=False) # In Naira (convert to kobo for Paystack)
    paystack_plan_code = Column(String, nullable=True)
    features = Column(Text, nullable=True) # JSON features list

class UserSubscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    plan_id = Column(String, ForeignKey("plans.id"), nullable=False)
    status = Column(String, nullable=False) # active | attention | non_renewing | cancelled
    paystack_subscription_code = Column(String, nullable=True)
    paystack_email_token = Column(String, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)

# ─────────────────────────────────────────────────────────
# INITIALIZATION
# ─────────────────────────────────────────────────────────

def init_auth_db():
    Base.metadata.create_all(bind=engine)
    
    # Seed plans if empty
    db = SessionLocal()
    if db.query(Plan).count() == 0:
        plans = [
            Plan(id="pro", name="Pro", amount=3000, features=json.dumps(["Daily AI Advice", "Advanced Analytics", "Live Market Data"])),
            Plan(id="business", name="Business", amount=8000, features=json.dumps(["Custom AI Models", "Unlimited Transactions", "Business Health Score"]))
        ]
        db.add_all(plans)
        db.commit()
    db.close()

def get_db():
    """Return a new DB session. Caller is responsible for closing it."""
    return SessionLocal()

# Alias for external use from main_auth.py
get_db_session = get_db

# Initialize tables immediately
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
    expires_at = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)

    db = get_db()
    # Clean up old tokens first
    db.query(UserSession).filter(UserSession.user_id == user_id, UserSession.expires_at < datetime.utcnow()).delete()
    
    new_session = UserSession(user_id=user_id, token=token, expires_at=expires_at)
    db.add(new_session)
    db.commit()
    db.close()
    return token

def validate_token(token: str) -> Optional[dict]:
    """Validate a token and return the user if valid."""
    if not token: return None
    db = get_db()
    session = db.query(UserSession).filter(UserSession.token == token, UserSession.expires_at > datetime.utcnow()).first()
    if not session:
        db.close()
        return None
    
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        db.close()
        return None
    
    # Convert SQLAlchemy object to dict
    user_dict = {c.name: getattr(user, c.name) for c in user.__table__.columns}
    user_dict.pop("password_hash", None)
    db.close()
    return user_dict

def revoke_token(token: str):
    """Logout — delete the session token."""
    db = get_db()
    db.query(UserSession).filter(UserSession.token == token).delete()
    db.commit()
    db.close()


# ─────────────────────────────────────────────────────────
# USER MANAGEMENT
# ─────────────────────────────────────────────────────────

def create_user(email: str, password: str, full_name: str, business_name: str,
                industry: str = "Retail", location: str = "Nigeria") -> dict:
    if len(password) < 8: raise ValueError("Password must be at least 8 characters")
    db = get_db()
    existing = db.query(User).filter(User.email == email.lower()).first()
    if existing:
        db.close()
        raise ValueError("An account with this email already exists")

    pw_hash = make_password_hash(password)
    new_user = User(email=email.lower(), password_hash=pw_hash, full_name=full_name, business_name=business_name, industry=industry, location=location)
    db.add(new_user)
    db.commit()
    user_id = new_user.id
    db.close()
    return get_user_by_id(user_id)

def login_user(email: str, password: str) -> Optional[dict]:
    db = get_db()
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user or not verify_password(password, user.password_hash):
        db.close()
        return None

    user.last_login = datetime.utcnow()
    db.commit()
    
    token = create_token(user.id)
    user_dict = {c.name: getattr(user, c.name) for c in user.__table__.columns}
    user_dict.pop("password_hash", None)
    db.close()
    return {"user": user_dict, "token": token}


def get_user_by_id(user_id: int) -> Optional[dict]:
    db = get_db()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        db.close()
        return None
    user_dict = {c.name: getattr(user, c.name) for c in user.__table__.columns}
    user_dict.pop("password_hash", None)
    db.close()
    return user_dict

def get_user_by_phone(phone: str) -> Optional[dict]:
    db = get_db()
    # Normalize phone: remove + if present
    phone = phone.replace("+", "")
    user = db.query(User).filter(User.phone == phone).first()
    if not user:
        # Try with + just in case
        user = db.query(User).filter(User.phone == f"+{phone}").first()
        
    if not user:
        db.close()
        return None
        
    user_dict = {c.name: getattr(user, c.name) for c in user.__table__.columns}
    user_dict.pop("password_hash", None)
    db.close()
    return user_dict

def update_user_profile(user_id: int, business_name: str, industry: str,
                         location: str, currency: str, full_name: str, ai_api_key: Optional[str] = None) -> dict:
    db = get_db()
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.business_name = business_name
        user.industry = industry
        user.location = location
        user.currency = currency
        user.full_name = full_name
        if ai_api_key: user.ai_api_key = ai_api_key
        db.commit()
    db.close()
    return get_user_by_id(user_id)

def change_password(user_id: int, current_password: str, new_password: str) -> bool:
    db = get_db()
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not verify_password(current_password, user.password_hash):
        db.close()
        return False
    
    user.password_hash = make_password_hash(new_password)
    db.commit()
    db.close()
    return True


# ─────────────────────────────────────────────────────────
# PER-USER TRANSACTIONS
# ─────────────────────────────────────────────────────────

def get_user_transactions(user_id: int, limit: int = 50, type_filter: Optional[str] = None) -> list:
    db = get_db()
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    if type_filter:
        query = query.filter(Transaction.type == type_filter)
    rows = query.order_by(Transaction.date.desc()).limit(limit).all()
    results = [{c.name: getattr(r, c.name) for c in r.__table__.columns} for r in rows]
    db.close()
    return results

def add_user_transaction(user_id: int, type_: str, description: str,
                          amount: float, date: str, category: Optional[str]) -> int:
    db = get_db()
    new_txn = Transaction(user_id=user_id, type=type_, description=description, amount=amount, date=date, category=category)
    db.add(new_txn)
    db.commit()
    txn_id = new_txn.id
    db.close()
    return txn_id

def delete_user_transaction(user_id: int, transaction_id: int) -> bool:
    db = get_db()
    deleted = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == user_id).delete()
    db.commit()
    db.close()
    return deleted > 0


def get_user_summary(user_id: int) -> dict:
    db = get_db()
    m = datetime.now().strftime("%Y-%m")
    
    # Simple aggregates using SQLAlchemy
    revenue = db.query(text("SUM(amount)")).select_from(Transaction).filter(Transaction.user_id == user_id, Transaction.type == 'sales', Transaction.date.like(f"{m}%")).scalar() or 0
    op_expenses = db.query(text("SUM(amount)")).select_from(Transaction).filter(Transaction.user_id == user_id, Transaction.type == 'expense', Transaction.date.like(f"{m}%")).scalar() or 0
    inv_purchases = db.query(text("SUM(amount)")).select_from(Transaction).filter(Transaction.user_id == user_id, Transaction.type == 'inventory', Transaction.date.like(f"{m}%")).scalar() or 0
    total_inv_value = db.query(text("SUM(amount)")).select_from(Transaction).filter(Transaction.user_id == user_id, Transaction.type == 'inventory').scalar() or 0
    
    db.close()
    total_outflow = float(op_expenses) + float(inv_purchases)
    net = float(revenue) - total_outflow
    margin = round((net / float(revenue) * 100), 1) if float(revenue) > 0 else 0
    
    return {
        "monthly_revenue": float(revenue),
        "operating_expenses": float(op_expenses),
        "inventory_purchases": float(inv_purchases),
        "monthly_expenses": total_outflow,
        "net_profit": net, 
        "inventory_value": float(total_inv_value), 
        "profit_margin": margin
    }

def get_user_by_day(user_id: int, days: int = 7) -> list:
    db = get_db()
    # Complex query translated to SQL text for ease of transition
    query = text("""
        SELECT date,
               SUM(CASE WHEN type='sales' THEN amount ELSE 0 END) as revenue,
               SUM(CASE WHEN type='expense' OR type='inventory' THEN amount ELSE 0 END) as expenses
        FROM transactions_v3 WHERE user_id = :uid
        GROUP BY date ORDER BY date DESC LIMIT :lim
    """)
    rows = db.execute(query, {"uid": user_id, "lim": days}).fetchall()
    db.close()
    return [dict(r._mapping) for r in rows]


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
        INSERT INTO transactions_v3 (user_id, type, description, amount, date, category)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [(user_id, *row) for row in sample])
    conn.commit()
