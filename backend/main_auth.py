"""
BizIQ - Production-Ready Backend
Unified secure API with Environment Variable support and Multi-User isolation.

Key Features:
- Secure API keys via .env or User Database
- Unified Chatbot Logic (Groq Llama 3.3)
- Accurate Financial Calculations (OpEx vs Inventory)
"""

import os
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

load_dotenv()

# Load core modules
from auth import (
    create_user, login_user, validate_token, revoke_token,
    update_user_profile, change_password,
    get_user_transactions, add_user_transaction, delete_user_transaction,
    get_user_summary, get_user_by_day,
)
from market_service import get_all_market_data, get_price_history, init_market_db
from ai_engine import (
    predict_revenue, predict_expenses,
    generate_smart_recommendations, calculate_health_score
)

app = FastAPI(title="BizIQ API", version="5.0.0")

# ── Production CORS configuration ──
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_market_db()

# ─────────────────────────────────────────────
# AUTH DEPENDENCY
# ─────────────────────────────────────────────

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Please log in to continue")
    token = authorization.split(" ")[1]
    user = validate_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    return user

# ─────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    business_name: str
    industry: Optional[str] = "Retail"
    location: Optional[str] = "Nigeria"

class LoginRequest(BaseModel):
    email: str
    password: str

class TransactionCreate(BaseModel):
    type: str
    description: str
    amount: float
    date: str
    category: Optional[str] = None

class ProfileUpdate(BaseModel):
    full_name: str
    business_name: str
    industry: Optional[str] = "Retail"
    location: Optional[str] = "Nigeria"
    currency: Optional[str] = "NGN"
    ai_api_key: Optional[str] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {"app": "BizIQ", "version": "5.0.0", "status": "live"}

@app.post("/auth/register")
def register(req: RegisterRequest):
    try:
        create_user(req.email, req.password, req.full_name, req.business_name, req.industry, req.location)
        result = login_user(req.email, req.password)
        return {"success": True, "user": result["user"], "token": result["token"]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/login")
def login(req: LoginRequest):
    result = login_user(req.email, req.password)
    if not result:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"success": True, "user": result["user"], "token": result["token"]}

@app.post("/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        revoke_token(authorization.split(" ")[1])
    return {"success": True}

@app.get("/auth/me")
def get_me(user: dict = Depends(get_current_user)):
    return user

@app.put("/auth/profile")
def update_profile(req: ProfileUpdate, user: dict = Depends(get_current_user)):
    updated = update_user_profile(user["id"], req.business_name, req.industry, req.location, req.currency, req.full_name, req.ai_api_key)
    return {"success": True, "user": updated}

@app.get("/transactions")
def get_transactions(limit: int = 50, type: Optional[str] = None, user: dict = Depends(get_current_user)):
    return get_user_transactions(user["id"], limit, type)

@app.post("/transactions")
def create_transaction(t: TransactionCreate, user: dict = Depends(get_current_user)):
    new_id = add_user_transaction(user["id"], t.type, t.description, t.amount, t.date, t.category)
    return {"success": True, "id": new_id}

@app.delete("/transactions/{tid}")
def delete_transaction(tid: int, user: dict = Depends(get_current_user)):
    deleted = delete_user_transaction(user["id"], tid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"success": True}

@app.get("/analytics/summary")
def get_summary(user: dict = Depends(get_current_user)):
    return get_user_summary(user["id"])

@app.get("/analytics/by-day")
def get_by_day(days: int = 7, user: dict = Depends(get_current_user)):
    return get_user_by_day(user["id"], days)

@app.get("/market/trends")
async def get_market_trends(user: dict = Depends(get_current_user)):
    try:
        data = await get_all_market_data(location=user.get("location", "Nigeria"))
        return {"status": "live", "fetched_at": datetime.now().isoformat(), "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── AI Insights ──

@app.get("/ai/recommendations")
def get_recommendations(user: dict = Depends(get_current_user)):
    return generate_smart_recommendations(user_id=user["id"])

@app.get("/ai/health-score")
def get_health_score(user: dict = Depends(get_current_user)):
    return calculate_health_score(user_id=user["id"])

@app.get("/ai/predict/revenue")
def predict_rev(user: dict = Depends(get_current_user)):
    return predict_revenue(30, user_id=user["id"])

@app.get("/ai/predict/expenses")
def predict_exp(user: dict = Depends(get_current_user)):
    return predict_expenses(30, user_id=user["id"])

@app.get("/ai/advice")
def get_advice(user: dict = Depends(get_current_user)):
    recs = generate_smart_recommendations(user_id=user["id"])
    return [{"icon": r["icon"], "type": r["priority"], "title": r["title"], "text": r["detail"], "color": r["color"]} for r in recs]

# ── Chatbot (Consolidated) ──

@app.post("/chat/message")
async def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    # Use user's private key OR fall back to system-wide GROQ_API_KEY
    groq_key = user.get("ai_api_key") or os.environ.get("GROQ_API_KEY")
    if not groq_key:
        raise HTTPException(status_code=500, detail="AI Brain key not found. Please set it in Settings.")

    summary = get_user_summary(user["id"])
    recent = get_user_transactions(user["id"], limit=5)
    margin = summary.get("profit_margin", 0)

    system = f"""You are BizIQ Assistant for {user.get('business_name')} owned by {user.get('full_name')}.
Explain business data in simple, plain English. Short sentences. Nigerian examples. Use emojis 😊.
Never use business jargon without explaining it simply. End every reply with one clear action.

THEIR DATA:
- Revenue this month: ₦{summary.get('monthly_revenue', 0):,.0f}
- Op. Expenses (Bills/Wages): ₦{summary.get('operating_expenses', 0):,.0f}
- Inventory Investment: ₦{summary.get('inventory_purchases', 0):,.0f}
- Net Profit: ₦{summary.get('net_profit', 0):,.0f}
- Profit Margin: {margin}% (you keep ₦{margin} from every ₦100 earned)
- Recent: {', '.join([t['description'] for t in recent[:3]])}"""

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "max_tokens": 500,
                    "messages": [
                        {"role": "system", "content": system},
                        *[{"role": m.role, "content": m.content} for m in req.messages],
                    ],
                }
            )
            data = res.json()
            return {"reply": data["choices"][0]["message"]["content"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Connecting to AI brain failed. Check your data link! 📡")

# ─────────────────────────────────────────────
# ADMIN
# ─────────────────────────────────────────────

@app.get("/admin/stats")
def admin_stats():
    import sqlite3
    conn = sqlite3.connect("biziq.db")
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_txns  = conn.execute("SELECT COUNT(*) FROM transactions_v2").fetchone()[0]
    conn.close()
    return {"total_businesses": total_users, "total_transactions": total_txns, "as_of": datetime.now().isoformat()}
