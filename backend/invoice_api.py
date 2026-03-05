"""
BizIQ — Invoice API Endpoint
Add to main_auth.py:
    from invoice_api import router as invoice_router
    app.include_router(invoice_router)

Install: pip install reportlab
"""

import sqlite3
import json
import os
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta

from invoice_generator import generate_invoice

router = APIRouter(prefix="/invoices", tags=["invoices"])

# Use env var so this works on Render (use /tmp for free tier or a mounted disk path)
DB_PATH = os.environ.get("DB_PATH", "biziq.db")


# ── Auth helper ──
def get_current_user(authorization: Optional[str] = Header(None)):
    try:
        from auth import validate_token
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Please log in")
        user = validate_token(authorization.split(" ")[1])
        if not user:
            raise HTTPException(status_code=401, detail="Session expired")
        return user
    except ImportError:
        return {"id": 1, "full_name": "Demo", "business_name": "Demo Business",
                "location": "Nigeria", "email": "demo@biziq.app"}


# ── DB setup ──
def init_invoice_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            invoice_number TEXT NOT NULL,
            customer_name  TEXT NOT NULL,
            customer_data  TEXT,
            items          TEXT,
            subtotal       REAL,
            tax_percent    REAL DEFAULT 0,
            total          REAL,
            status         TEXT DEFAULT 'draft',
            issue_date     TEXT,
            due_date       TEXT,
            notes          TEXT,
            created_at     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_invoice_db()


# ── Models ──
class InvoiceItem(BaseModel):
    description: str
    qty:         float
    unit_price:  float

class CustomerInfo(BaseModel):
    name:    str
    address: Optional[str] = ""
    phone:   Optional[str] = ""
    email:   Optional[str] = ""

class InvoiceCreate(BaseModel):
    customer:    CustomerInfo
    items:       List[InvoiceItem]
    tax_percent: Optional[float] = 0
    due_days:    Optional[int]   = 14
    notes:       Optional[str]   = ""


# ── Helpers ──
def next_invoice_number(user_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM invoices WHERE user_id=?", (user_id,)).fetchone()[0]
    conn.close()
    return f"INV-{str(count + 1).zfill(3)}"


# ── Endpoints ──

@router.post("/create")
def create_invoice(req: InvoiceCreate, user=Depends(get_current_user)):
    """Create and save a new invoice, return its ID."""
    issue_date = datetime.now().strftime("%Y-%m-%d")
    due_date   = (datetime.now() + timedelta(days=req.due_days)).strftime("%Y-%m-%d")
    inv_number = next_invoice_number(user["id"])

    subtotal = sum(i.qty * i.unit_price for i in req.items)
    tax_amt  = subtotal * req.tax_percent / 100
    total    = subtotal + tax_amt

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO invoices
          (user_id, invoice_number, customer_name, customer_data, items,
           subtotal, tax_percent, total, issue_date, due_date, notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        user["id"], inv_number, req.customer.name,
        json.dumps(req.customer.dict()),
        json.dumps([i.dict() for i in req.items]),
        subtotal, req.tax_percent, total,
        issue_date, due_date, req.notes
    ))
    conn.commit()
    inv_id = cur.lastrowid
    conn.close()

    return {"success": True, "id": inv_id, "invoice_number": inv_number, "total": total}


@router.get("/download/{inv_id}")
def download_invoice(inv_id: int, user=Depends(get_current_user)):
    """Generate and download a PDF invoice."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM invoices WHERE id=? AND user_id=?",
                       (inv_id, user["id"])).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")

    customer = json.loads(row["customer_data"])
    items    = json.loads(row["items"])

    data = {
        "invoice_number": row["invoice_number"],
        "issue_date":     row["issue_date"],
        "due_date":       row["due_date"],
        "business": {
            "name":    user.get("business_name", "My Business"),
            "address": user.get("location", "Nigeria"),
            "phone":   user.get("phone", ""),
            "email":   user.get("email", ""),
        },
        "customer":    customer,
        "items":       items,
        "tax_percent": row["tax_percent"],
        "notes":       row["notes"] or "",
    }

    pdf_bytes = generate_invoice(data)
    filename  = f"{row['invoice_number']}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/list")
def list_invoices(user=Depends(get_current_user)):
    """List all invoices for the logged-in user."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id, invoice_number, customer_name, total, status, issue_date, due_date
        FROM invoices WHERE user_id=? ORDER BY created_at DESC
    """, (user["id"],)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.delete("/{inv_id}")
def delete_invoice(inv_id: int, user=Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM invoices WHERE id=? AND user_id=?", (inv_id, user["id"]))
    conn.commit()
    conn.close()
    return {"success": True}
