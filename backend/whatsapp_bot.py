"""
BizIQ WhatsApp Bot
==================
Business owners can manage their business by sending WhatsApp messages.

Commands they can send:
  "sales 50000"              → Log ₦50,000 in sales
  "expense 20000 flour"      → Log ₦20,000 expense (flour)
  "report"                   → Get today's summary
  "market"                   → Get live commodity prices
  "balance"                  → Get this month's profit
  "help"                     → See all commands
  Any question               → AI chatbot answers it

Setup:
  1. Create Meta Developer account at developers.facebook.com
  2. Create an App → Add WhatsApp product
  3. Get your Phone Number ID and Access Token
  4. Set webhook URL to: https://your-backend.onrender.com/whatsapp
  5. Set VERIFY_TOKEN to any secret string you choose
  6. Add env variables to Render (or .env file locally)

Run with: uvicorn whatsapp_bot:app --reload
"""

import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from datetime import datetime
from typing import Optional

# ── Import from existing BizIQ backend ──
# These functions already exist in your auth.py and ai_engine.py
try:
    from auth import (
        get_user_by_phone, add_user_transaction,
        get_user_summary, get_user_transactions
    )
    from ai_engine import generate_smart_recommendations
    from market_service import get_all_market_data
    BIZIQ_AVAILABLE = True
except ImportError:
    BIZIQ_AVAILABLE = False
    print("WARNING: Running in standalone mode (BizIQ modules not found)")

app = FastAPI(title="BizIQ WhatsApp Bot")

# ── Config from environment variables ──
WHATSAPP_TOKEN   = os.environ.get("WHATSAPP_TOKEN", "")       # Meta access token
PHONE_NUMBER_ID  = os.environ.get("PHONE_NUMBER_ID", "")      # Your WhatsApp phone number ID
VERIFY_TOKEN     = os.environ.get("WA_VERIFY_TOKEN", "biziq_secret_2024")  # Your chosen verify token
GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")

WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"


# ─────────────────────────────────────────────
# SEND MESSAGE
# ─────────────────────────────────────────────

async def send_message(to: str, text: str):
    """Send a WhatsApp message to a phone number."""
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print(f"[DEMO MODE] Would send to {to}:\n{text}")
        return

    async with httpx.AsyncClient() as client:
        await client.post(
            WHATSAPP_API_URL,
            headers={
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text}
            }
        )


async def send_buttons(to: str, body: str, buttons: list):
    """Send a message with quick-reply buttons (max 3)."""
    if not WHATSAPP_TOKEN:
        print(f"[DEMO MODE] Buttons to {to}: {body}")
        return

    async with httpx.AsyncClient() as client:
        await client.post(
            WHATSAPP_API_URL,
            headers={
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": body},
                    "action": {
                        "buttons": [
                            {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                            for b in buttons[:3]
                        ]
                    }
                }
            }
        )


# ─────────────────────────────────────────────
# MESSAGE PARSER
# ─────────────────────────────────────────────

def parse_command(text: str) -> dict:
    """
    Parse an incoming WhatsApp message into a command.
    Returns {"command": str, "amount": float, "description": str}
    """
    text = text.strip().lower()
    parts = text.split()
    
    if not parts:
        return {"command": "help"}

    # sales 50000
    # sales 50000 "product name"
    if parts[0] in ("sales", "sale", "s", "sold"):
        try:
            amount = float(parts[1].replace(",", "").replace("₦", ""))
            desc   = " ".join(parts[2:]) if len(parts) > 2 else "Sales"
            return {"command": "sales", "amount": amount, "description": desc or "Daily sales"}
        except (IndexError, ValueError):
            return {"command": "sales_help"}

    # expense 20000 flour
    if parts[0] in ("expense", "exp", "spent", "cost", "e"):
        try:
            amount = float(parts[1].replace(",", "").replace("₦", ""))
            desc   = " ".join(parts[2:]) if len(parts) > 2 else "Expense"
            return {"command": "expense", "amount": amount, "description": desc or "Expense"}
        except (IndexError, ValueError):
            return {"command": "expense_help"}

    # report / summary
    if parts[0] in ("report", "summary", "today", "r"):
        return {"command": "report"}

    # balance / profit
    if parts[0] in ("balance", "profit", "money", "b", "p"):
        return {"command": "balance"}

    # market prices
    if parts[0] in ("market", "prices", "price", "m"):
        return {"command": "market"}

    # help
    if parts[0] in ("help", "h", "commands", "menu", "start"):
        return {"command": "help"}

    # list recent transactions
    if parts[0] in ("history", "list", "transactions"):
        return {"command": "history"}

    # ai / ask
    return {"command": "ai", "question": text}


# ─────────────────────────────────────────────
# COMMAND HANDLERS
# ─────────────────────────────────────────────

async def handle_sales(phone: str, amount: float, description: str):
    today = datetime.now().strftime("%Y-%m-%d")

    print(f"DEBUG: handle_sales called for {phone} with amount {amount}")
    if BIZIQ_AVAILABLE:
        user = get_user_by_phone(phone)
        if user:
            print(f"DEBUG: User found: {user['id']}. Saving transaction.")
            add_user_transaction(user["id"], "sales", description, amount, today, "Revenue")
        else:
            print(f"DEBUG: No user found for phone {phone}")
    else:
        print("DEBUG: BIZIQ_AVAILABLE is False")

    reply = (
        f"✅ *Sales recorded!*\n\n"
        f"💰 Amount: ₦{amount:,.0f}\n"
        f"📝 Description: {description}\n"
        f"📅 Date: {today}\n\n"
        f"Type *report* to see today's summary."
    )
    await send_message(phone, reply)


async def handle_expense(phone: str, amount: float, description: str):
    today = datetime.now().strftime("%Y-%m-%d")

    if BIZIQ_AVAILABLE:
        user = get_user_by_phone(phone)
        if user:
            add_user_transaction(user["id"], "expense", description, amount, today, "Operations")

    reply = (
        f"✅ *Expense recorded!*\n\n"
        f"💸 Amount: ₦{amount:,.0f}\n"
        f"📝 Description: {description}\n"
        f"📅 Date: {today}\n\n"
        f"Type *balance* to check your profit."
    )
    await send_message(phone, reply)


async def handle_report(phone: str):
    if BIZIQ_AVAILABLE:
        user = get_user_by_phone(phone)
        if user:
            s = get_user_summary(user["id"])
            reply = (
                f"📊 *Your Business Report*\n"
                f"{'─'*25}\n\n"
                f"💰 Revenue this month:  ₦{s['monthly_revenue']:,.0f}\n"
                f"💸 Expenses this month: ₦{s['monthly_expenses']:,.0f}\n"
                f"✅ Net Profit:          ₦{s['net_profit']:,.0f}\n"
                f"📈 Profit Margin:       {s['profit_margin']}%\n\n"
                f"{'🟢' if s['net_profit'] > 0 else '🔴'} "
                f"{'Business is profitable!' if s['net_profit'] > 0 else 'Expenses are higher than revenue!'}\n\n"
                f"Type *market* for live commodity prices."
            )
            await send_message(phone, reply)
            return

    # Demo response when no real data
    await send_message(phone,
        "📊 *Demo Report*\n\n"
        "💰 Revenue: ₦450,000\n"
        "💸 Expenses: ₦320,000\n"
        "✅ Profit: ₦130,000\n"
        "📈 Margin: 28.9%\n\n"
        "Connect your BizIQ account to see real data."
    )


async def handle_balance(phone: str):
    if BIZIQ_AVAILABLE:
        user = get_user_by_phone(phone)
        if user:
            s = get_user_summary(user["id"])
            net = s["net_profit"]
            emoji = "🟢" if net > 0 else "🔴"
            reply = (
                f"{emoji} *Your Balance*\n\n"
                f"This month you have made:\n"
                f"*₦{net:,.0f}* profit\n\n"
                f"Revenue: ₦{s['monthly_revenue']:,.0f}\n"
                f"Expenses: ₦{s['monthly_expenses']:,.0f}"
            )
            await send_message(phone, reply)
            return

    await send_message(phone, "💰 Connect your BizIQ account to see your real balance.")


async def handle_market(phone: str):
    try:
        if BIZIQ_AVAILABLE:
            data = await get_all_market_data()
            if data:
                lines = ["🌍 *Live Market Prices*\n"]
                for item in data[:6]:
                    arrow = "📈" if item["trend"] > 0 else "📉"
                    lines.append(
                        f"{arrow} *{item['item']}*\n"
                        f"   ₦{item['price_ngn']:,.0f}  ({'+' if item['trend']>0 else ''}{item['trend']}%)\n"
                        f"   💡 _{item['advice']}_\n"
                    )
                await send_message(phone, "\n".join(lines))
                return
    except Exception:
        pass

    await send_message(phone,
        "🌍 *Market Prices*\n\n"
        "📈 Flour (50kg): ₦42,000 (+3.2%)\n"
        "   💡 Prices rising — stock up now\n\n"
        "📉 Sugar (50kg): ₦28,500 (-1.1%)\n"
        "   💡 Good time to buy\n\n"
        "📈 Palm Oil (25L): ₦18,200 (+5.4%)\n"
        "   💡 Buy in bulk this week\n\n"
        "Type *report* to see your business summary."
    )


async def handle_history(phone: str):
    if BIZIQ_AVAILABLE:
        user = get_user_by_phone(phone)
        if user:
            txns = get_user_transactions(user["id"], limit=5)
            if txns:
                lines = ["📋 *Last 5 Transactions*\n"]
                for t in txns:
                    sign  = "+" if t["type"] == "sales" else "-"
                    emoji = "💰" if t["type"] == "sales" else "💸"
                    lines.append(f"{emoji} {t['date']}  {sign}₦{t['amount']:,.0f}  _{t['description']}_")
                await send_message(phone, "\n".join(lines))
                return

    await send_message(phone, "📋 No transactions yet. Send *sales 50000* to log your first sale!")


async def handle_ai(phone: str, question: str):
    """Send question to Groq AI with business context."""
    if not GROQ_API_KEY:
        await send_message(phone,
            "🤖 AI assistant is not configured yet.\n"
            "Type *help* to see available commands."
        )
        return

    # Build context
    context = ""
    if BIZIQ_AVAILABLE:
        try:
            user = get_user_by_phone(phone)
            if user:
                s = get_user_summary(user["id"])
                context = (
                    f"Business: {user.get('business_name', 'Unknown')}\n"
                    f"Revenue: ₦{s['monthly_revenue']:,.0f}\n"
                    f"Expenses: ₦{s['monthly_expenses']:,.0f}\n"
                    f"Profit: ₦{s['net_profit']:,.0f}\n"
                    f"Margin: {s['profit_margin']}%"
                )
        except Exception:
            pass

    system = f"""You are BizIQ WhatsApp assistant. Answer in simple, plain English.
Keep answers SHORT — max 5 sentences. Use emojis. No markdown bold (*text*) except for numbers.
This is WhatsApp so keep formatting simple.
{f'Business data: {context}' if context else ''}"""

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "max_tokens": 300,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": question}
                    ]
                }
            )
            data = res.json()
            reply = data["choices"][0]["message"]["content"]
            await send_message(phone, f"🤖 {reply}")
    except Exception as e:
        await send_message(phone, "🤖 Sorry, AI is busy right now. Try again in a moment!")


async def handle_help(phone: str):
    await send_message(phone,
        "👋 *Welcome to BizIQ!*\n\n"
        "Here's what you can do:\n\n"
        "💰 *Log a sale:*\n"
        "   sales 50000\n"
        "   sales 120000 bread\n\n"
        "💸 *Log an expense:*\n"
        "   expense 30000 flour\n"
        "   expense 15000 transport\n\n"
        "📊 *See your report:*\n"
        "   report\n\n"
        "💵 *Check your profit:*\n"
        "   balance\n\n"
        "🌍 *Live market prices:*\n"
        "   market\n\n"
        "📋 *Recent transactions:*\n"
        "   history\n\n"
        "🤖 *Ask AI anything:*\n"
        "   should i buy sugar now?\n"
        "   what does profit margin mean?\n\n"
        "_Powered by BizIQ_ 🚀"
    )


# ─────────────────────────────────────────────
# WEBHOOK — Meta sends all messages here
# ─────────────────────────────────────────────

@app.get("/whatsapp")
async def verify_webhook(request: Request):
    """
    Meta calls this once to verify your webhook URL.
    It sends a challenge token — you return it to confirm.
    """
    params = dict(request.query_params)
    mode      = params.get("hub.mode")
    token     = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("SUCCESS: Webhook verified!")
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/whatsapp")
async def receive_message(request: Request):
    """
    Meta sends every incoming WhatsApp message here as a POST request.
    We parse it and route to the right handler.
    """
    body = await request.json()

    try:
        # Extract message from Meta's payload structure
        entry   = body["entry"][0]
        changes = entry["changes"][0]
        value   = changes["value"]

        # Ignore delivery receipts and status updates
        if "messages" not in value:
            return {"status": "ok"}

        message = value["messages"][0]
        phone   = message["from"]               # sender's phone number
        msg_type = message.get("type", "")

        # Handle text messages
        if msg_type == "text":
            text = message["text"]["body"].strip()
            print(f"PHONE MESSAGE from {phone}: {text}")
            await route_message(phone, text)

        # Handle button replies
        elif msg_type == "interactive":
            button_id = message["interactive"]["button_reply"]["id"]
            await route_message(phone, button_id)

        # Handle image (for receipt scanner — future feature)
        elif msg_type == "image":
            await send_message(phone,
                "📸 Receipt scanning is coming soon!\n"
                "For now, type: expense 50000 flour"
            )

    except (KeyError, IndexError) as e:
        print(f"WARNING: Could not parse message: {e}")

    # Always return 200 — Meta will retry if you don't
    return {"status": "ok"}


async def route_message(phone: str, text: str):
    """Parse the message and call the right handler."""
    cmd = parse_command(text)
    c   = cmd["command"]

    if c == "sales":
        await handle_sales(phone, cmd["amount"], cmd["description"])
    elif c == "sales_help":
        await send_message(phone, "💰 To log a sale, type:\n*sales 50000*\nor\n*sales 120000 bread*")
    elif c == "expense":
        await handle_expense(phone, cmd["amount"], cmd["description"])
    elif c == "expense_help":
        await send_message(phone, "💸 To log an expense, type:\n*expense 30000 flour*\nor\n*expense 15000 transport*")
    elif c == "report":
        await handle_report(phone)
    elif c == "balance":
        await handle_balance(phone)
    elif c == "market":
        await handle_market(phone)
    elif c == "history":
        await handle_history(phone)
    elif c == "help":
        await handle_help(phone)
    elif c == "ai":
        await handle_ai(phone, cmd["question"])
    else:
        await handle_help(phone)


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "app": "BizIQ WhatsApp Bot",
        "status": "running",
        "webhook": "/whatsapp",
        "configured": bool(WHATSAPP_TOKEN and PHONE_NUMBER_ID)
    }
