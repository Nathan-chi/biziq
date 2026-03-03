"""
BizIQ - Complete Backend (All 4 Stages)
Stage 1: Core API & Database
Stage 2: Business Analytics
Stage 3: Live Market Data
Stage 4: AI Predictions & ML Engine

Run with: uvicorn main:app --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import sqlite3

from market_service import get_all_market_data, get_price_history, init_market_db
from ai_engine import (
    predict_revenue, predict_expenses, predict_commodity_price,
    generate_smart_recommendations, calculate_health_score
)

app = FastAPI(title="BizIQ API — Full Stack", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect("biziq.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            category TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            industry TEXT,
            location TEXT,
            currency TEXT DEFAULT 'NGN'
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM business_profile")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO business_profile (name, industry, location, currency) VALUES ('My Business', 'Retail', 'Nigeria', 'NGN')")

    cursor.execute("SELECT COUNT(*) FROM transactions")
    if cursor.fetchone()[0] == 0:
        sample = [
            ("sales",    "Daily sales revenue",   142000, "2026-03-03", "Revenue"),
            ("expense",  "Flour purchase (50kg)", 285000, "2026-03-03", "Inventory"),
            ("sales",    "Daily sales revenue",   118500, "2026-03-02", "Revenue"),
            ("expense",  "Staff wages",            95000, "2026-03-02", "Operations"),
            ("expense",  "Inventory restock",     320000, "2026-03-01", "Inventory"),
            ("sales",    "Daily sales revenue",   134000, "2026-03-01", "Revenue"),
            ("expense",  "Electricity bill",       18000, "2026-02-28", "Utilities"),
            ("sales",    "Daily sales revenue",   187000, "2026-02-28", "Revenue"),
            ("sales",    "Daily sales revenue",   156000, "2026-02-27", "Revenue"),
            ("expense",  "Transport costs",        22000, "2026-02-27", "Operations"),
            ("sales",    "Daily sales revenue",   198000, "2026-02-26", "Revenue"),
            ("expense",  "Packaging materials",    35000, "2026-02-26", "Operations"),
        ]
        cursor.executemany("INSERT INTO transactions (type, description, amount, date, category) VALUES (?,?,?,?,?)", sample)

    conn.commit()
    conn.close()
    init_market_db()


init_db()


# ─────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────

class TransactionCreate(BaseModel):
    type: str
    description: str
    amount: float
    date: str
    category: Optional[str] = None

class BusinessProfileUpdate(BaseModel):
    name: str
    industry: Optional[str] = None
    location: Optional[str] = None
    currency: Optional[str] = "NGN"


# ─────────────────────────────────────────────
# STAGE 1 & 2: CORE ROUTES
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "BizIQ v4.0 — All stages active", "docs": "/docs"}


@app.get("/transactions")
def get_transactions(limit: int = 50, type: Optional[str] = None):
    conn = get_db()
    if type:
        rows = conn.execute("SELECT * FROM transactions WHERE type=? ORDER BY date DESC LIMIT ?", (type, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM transactions ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/transactions")
def create_transaction(t: TransactionCreate):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO transactions (type, description, amount, date, category) VALUES (?,?,?,?,?)",
                (t.type, t.description, t.amount, t.date, t.category))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"success": True, "id": new_id}


@app.delete("/transactions/{tid}")
def delete_transaction(tid: int):
    conn = get_db()
    conn.execute("DELETE FROM transactions WHERE id=?", (tid,))
    conn.commit()
    conn.close()
    return {"success": True}


@app.get("/analytics/summary")
def get_summary():
    conn = get_db()
    m = datetime.now().strftime("%Y-%m")
    revenue  = conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='sales'   AND date LIKE ?", (f"{m}%",)).fetchone()[0]
    expenses = conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='expense' AND date LIKE ?", (f"{m}%",)).fetchone()[0]
    inventory = conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE type='inventory'").fetchone()[0]
    conn.close()
    net = revenue - expenses
    margin = round((net / revenue * 100), 1) if revenue > 0 else 0
    return {"monthly_revenue": revenue, "monthly_expenses": expenses, "net_profit": net, "inventory_value": inventory, "profit_margin": margin}


@app.get("/analytics/by-day")
def get_by_day(days: int = 7):
    conn = get_db()
    rows = conn.execute("""
        SELECT date,
               SUM(CASE WHEN type='sales'   THEN amount ELSE 0 END) as revenue,
               SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as expenses
        FROM transactions GROUP BY date ORDER BY date DESC LIMIT ?
    """, (days,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/analytics/by-category")
def get_by_category():
    conn = get_db()
    rows = conn.execute("""
        SELECT category, SUM(amount) as total FROM transactions
        WHERE type='expense' AND category IS NOT NULL
        GROUP BY category ORDER BY total DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/profile")
def get_profile():
    conn = get_db()
    row = conn.execute("SELECT * FROM business_profile LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else {}


@app.put("/profile")
def update_profile(p: BusinessProfileUpdate):
    conn = get_db()
    conn.execute("UPDATE business_profile SET name=?, industry=?, location=?, currency=? WHERE id=1",
                 (p.name, p.industry, p.location, p.currency))
    conn.commit()
    conn.close()
    return {"success": True}


# ─────────────────────────────────────────────
# STAGE 3: MARKET DATA
# ─────────────────────────────────────────────

@app.get("/market/trends")
async def get_market_trends():
    try:
        data = await get_all_market_data()
        return {"status": "live", "fetched_at": datetime.now().isoformat(), "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/market/history/{symbol}")
def get_market_history(symbol: str, days: int = 30):
    return {"symbol": symbol, "history": get_price_history(symbol, days)}


# ─────────────────────────────────────────────
# STAGE 4: AI PREDICTIONS
# ─────────────────────────────────────────────

@app.get("/ai/predict/revenue")
def predict_revenue_endpoint(days: int = 30):
    """Predict future revenue using ML regression on your sales history"""
    return predict_revenue(days)


@app.get("/ai/predict/expenses")
def predict_expenses_endpoint(days: int = 30):
    """Predict future expenses using ML regression"""
    return predict_expenses(days)


@app.get("/ai/predict/commodity/{symbol}")
def predict_commodity_endpoint(symbol: str, days: int = 30):
    """Predict future price of a commodity (e.g. WHEAT, SUGAR)"""
    return predict_commodity_price(symbol, days)


@app.get("/ai/recommendations")
def get_recommendations():
    """
    Smart AI recommendations combining your business data + market forecasts.
    This is the brain of BizIQ.
    """
    return generate_smart_recommendations()


@app.get("/ai/health-score")
def get_health_score():
    """
    Calculate your business health score (0-100).
    Combines profitability, consistency, and data completeness.
    """
    return calculate_health_score()


@app.get("/ai/advice")
def get_ai_advice():
    """Combined advice endpoint (backward compatible)"""
    recs = generate_smart_recommendations()
    # Convert to simple advice format for dashboard
    return [
        {
            "icon": r["icon"],
            "type": r["priority"],
            "title": r["title"],
            "text": r["detail"],
            "color": r["color"],
        }
        for r in recs
    ]
