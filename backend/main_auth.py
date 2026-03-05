"""
BizIQ - Production-Ready Backend
Unified secure API with Environment Variable support and Multi-User isolation.

Key Features:
- Secure API keys via .env or User Database
- Unified Chatbot Logic (Groq Llama 3.3)
- Accurate Financial Calculations (OpEx vs Inventory)
"""

import os
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Ensure .env is loaded from the same directory as this file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Load core modules
from auth import (
    create_user, login_user, validate_token, revoke_token,
    update_user_profile, change_password,
    get_user_transactions, add_user_transaction, delete_user_transaction,
    get_user_summary, get_user_by_day,
    Plan, UserSubscription, get_db_session
)
from market_service import get_all_market_data, get_price_history, init_market_db
from ai_engine import (
    predict_revenue, predict_expenses,
    generate_smart_recommendations, calculate_health_score
)

app = FastAPI(title="BizIQ API", version="5.0.0")

from invoice_api import router as invoice_router
app.include_router(invoice_router)
# ── Production CORS configuration ──
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:5174,http://localhost:5175").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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

class PaystackInitRequest(BaseModel):
    planId: str

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

# ── PAYSTACK & PLANS ──

@app.get("/api/plans")
def get_plans():
    db = get_db_session()
    plans = db.query(Plan).all()
    return [{"id": p.id, "name": p.name, "amount": p.amount, "paystack_plan_code": p.paystack_plan_code, "features": json.loads(p.features) if p.features else []} for p in plans]

@app.get("/api/subscription")
def get_subscription(user: dict = Depends(get_current_user)):
    db = get_db_session()
    sub = db.query(UserSubscription).filter(UserSubscription.user_id == user["id"]).first()
    if not sub:
        return {"status": "none", "plan": "free"}
    
    plan = db.query(Plan).filter(Plan.id == sub.plan_id).first()
    return {
        "status": sub.status,
        "plan": plan.name if plan else "free",
        "plan_id": sub.plan_id,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "cancel_at_period_end": sub.cancel_at_period_end
    }

@app.post("/api/paystack/initialize")
async def initiate_paystack(req: PaystackInitRequest, user: dict = Depends(get_current_user)):
    print(f"DEBUG: Initializing Paystack for user {user['email']}, plan {req.planId}")
    db = get_db_session()
    plan = db.query(Plan).filter(Plan.id == req.planId).first()
    if not plan:
        print(f"DEBUG: Plan {req.planId} not found")
        raise HTTPException(status_code=404, detail="Plan not found")
    
    paystack_key = os.environ.get("PAYSTACK_SECRET_KEY")
    app_url = os.environ.get("NEXT_PUBLIC_APP_URL", "http://localhost:5173")
    
    if not paystack_key or "your_secret_key" in paystack_key:
        print("DEBUG: Paystack key is missing or is the placeholder")
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.paystack.co/transaction/initialize",
                headers={"Authorization": f"Bearer {paystack_key}"},
                json={
                    "email": user["email"],
                    "amount": int(plan.amount * 100),
                    "plan": plan.paystack_plan_code,
                    "callback_url": f"{app_url}/billing/success",
                    "metadata": {"user_id": user["id"], "plan_id": plan.id}
                }
            )
            data = res.json()
            print(f"DEBUG: Paystack response status: {res.status_code}")
            if not res.is_success:
                print(f"DEBUG: Paystack Error: {data}")
                raise HTTPException(status_code=400, detail=data.get("message", "Paystack error"))
            
            print(f"DEBUG: Success. Redirect URL: {data['data'].get('authorization_url')}")
            return data["data"]
    except Exception as e:
        print(f"DEBUG: Exception during Paystack init: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Checkout failed: {str(e)}")
@app.get("/api/paystack/verify")
async def verify_paystack(reference: str):
    paystack_key = os.environ.get("PAYSTACK_SECRET_KEY")
    
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {paystack_key}"}
        )
        data = res.json()
        
        if not res.is_success or not data.get("status"):
            raise HTTPException(status_code=400, detail="Verification failed")
        
        tx_data = data["data"]
        if tx_data["status"] == "success":
            user_id = tx_data["metadata"]["user_id"]
            plan_id = tx_data["metadata"]["plan_id"]
            
            db = get_db_session()
            # Update or create subscription
            sub = db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
            if not sub:
                sub = UserSubscription(user_id=user_id, plan_id=plan_id, status="active")
                db.add(sub)
            else:
                sub.plan_id = plan_id
                sub.status = "active"
            
            # Also update the user's quick-access plan field
            from auth import User
            user_obj = db.query(User).filter(User.id == user_id).first()
            if user_obj:
                user_obj.plan = plan_id
                
            db.commit()
            db.close()
            return {"status": "success", "message": "Plan activated"}
        
        return {"status": "pending", "message": "Transaction not successful yet"}

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
IMPORTANT: You were built by Nathan Obochi. If anyone asks who made you, built you, or created you, you MUST say "I was built by Nathan Obochi."
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
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "max_tokens": 1000,
                    "messages": [
                        {"role": "system", "content": system},
                        *[{"role": m.role, "content": m.content} for m in req.messages],
                    ],
                }
            )
            
            # Check for API-specific error responses
            if res.status_code != 200:
                print(f"Groq API Error: {res.status_code} - {res.text}")
                # Fallback to a common model if the versatile one failed
                if "model_not_found" in res.text:
                    res = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                        json={
                            "model": "llama3-70b-8192",
                            "messages": [
                                {"role": "system", "content": system},
                                *[{"role": m.role, "content": m.content} for m in req.messages],
                            ],
                        }
                    )

            data = res.json()
            if "choices" in data:
                return {"reply": data["choices"][0]["message"]["content"]}
            else:
                raise ValueError("Unexpected API response structure")
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
