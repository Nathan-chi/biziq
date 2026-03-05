"""
BizIQ Invoice Generator
Generates a professional PDF invoice using reportlab.
Zero external APIs needed — 100% free.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from datetime import datetime
import io
import os

W, H = A4  # 210 x 297 mm

# Colour palette matching BizIQ
DARK    = colors.HexColor("#0f0f0f")
ACCENT  = colors.HexColor("#00d4aa")
LIGHT   = colors.HexColor("#f8f7f4")
MUTED   = colors.HexColor("#6b7280")
WHITE   = colors.white
BORDER  = colors.HexColor("#e5e2dc")
NEG     = colors.HexColor("#ff4444")


def fmt_ngn(amount):
    return f"N{float(amount):,.2f}"   # N = Naira (plain ASCII for PDF safety)


def generate_invoice(data: dict) -> bytes:
    """
    Generate a PDF invoice and return the bytes.

    data = {
        "invoice_number":  "INV-001",
        "issue_date":      "2026-03-05",
        "due_date":        "2026-03-19",
        "business": {
            "name":    "Musa's Store",
            "address": "12 Market Street, Abuja",
            "phone":   "+234 801 234 5678",
            "email":   "musa@example.com",
        },
        "customer": {
            "name":    "Ade Foods Ltd",
            "address": "45 Ring Road, Lagos",
            "phone":   "+234 802 345 6789",
            "email":   "ade@example.com",
        },
        "items": [
            {"description": "Rice (50kg bag)", "qty": 10, "unit_price": 45000},
            {"description": "Flour (50kg bag)", "qty": 5,  "unit_price": 42000},
        ],
        "tax_percent": 7.5,   # set 0 for no tax
        "notes": "Thank you for your business!",
    }
    """
    buf = io.BytesIO()
    c   = canvas.Canvas(buf, pagesize=A4)

    # ── HEADER BAND ──
    c.setFillColor(DARK)
    c.rect(0, H - 55*mm, W, 55*mm, fill=1, stroke=0)

    # Logo / business name
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(15*mm, H - 22*mm, "BizIQ")
    c.setFillColor(WHITE)
    c.setFont("Helvetica", 10)
    c.drawString(15*mm, H - 30*mm, str(data["business"].get("name", "BizIQ User")))

    # INVOICE label
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 36)
    c.drawRightString(W - 15*mm, H - 24*mm, "INVOICE")
    c.setFillColor(WHITE)
    c.setFont("Helvetica", 10)
    c.drawRightString(W - 15*mm, H - 32*mm, f"# {str(data.get('invoice_number', '000'))}")

    # ── INVOICE META (Issue / Due) ──
    y = H - 65*mm
    for label, value in [
        ("Issue Date", data["issue_date"]),
        ("Due Date",   data["due_date"]),
    ]:
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 8)
        c.drawString(15*mm, y, label.upper())
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(15*mm, y - 5*mm, value)
        y -= 14*mm

    # ── FROM / TO ──
    y = H - 65*mm
    for col_x, section, info in [
        (W/2 - 20*mm, "FROM",    data["business"]),
        (W/2 + 40*mm, "BILL TO", data["customer"]),
    ]:
        c.setFillColor(ACCENT)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(col_x, y, section)
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(col_x, y - 6*mm, str(info.get("name", "")))
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 9)
        c.drawString(col_x, y - 12*mm, str(info.get("address", "")))
        c.drawString(col_x, y - 18*mm, str(info.get("phone", "")))
        c.drawString(col_x, y - 24*mm, str(info.get("email", "")))

    # ── DIVIDER ──
    y_table_top = H - 105*mm
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.5)
    c.line(15*mm, y_table_top, W - 15*mm, y_table_top)

    # ── ITEMS TABLE ──
    items = data.get("items", [])
    tax_pct = float(data.get("tax_percent", 0))

    subtotal = sum(float(i["qty"]) * float(i["unit_price"]) for i in items)
    tax_amt  = subtotal * tax_pct / 100
    total    = subtotal + tax_amt

    # Table data
    table_data = [["DESCRIPTION", "QTY", "UNIT PRICE", "AMOUNT"]]
    for item in items:
        amt = float(item["qty"]) * float(item["unit_price"])
        table_data.append([
            str(item.get("description", "")),
            str(item.get("qty", 0)),
            fmt_ngn(item.get("unit_price", 0)),
            fmt_ngn(amt),
        ])

    col_widths = [90*mm, 20*mm, 35*mm, 35*mm]
    t = Table(table_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",  (0,0), (-1,0),  DARK),
        ("TEXTCOLOR",   (0,0), (-1,0),  ACCENT),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,0),  8),
        ("TOPPADDING",  (0,0), (-1,0),  6),
        ("BOTTOMPADDING",(0,0),(-1,0),  6),
        # Data rows
        ("FONTNAME",    (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",    (0,1), (-1,-1), 9),
        ("TOPPADDING",  (0,1), (-1,-1), 7),
        ("BOTTOMPADDING",(0,1),(-1,-1), 7),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, colors.HexColor("#f9f9f9")]),
        # Alignment
        ("ALIGN",       (1,0), (-1,-1), "CENTER"),
        ("ALIGN",       (2,0), (-1,-1), "RIGHT"),
        ("ALIGN",       (3,0), (-1,-1), "RIGHT"),
        # Grid
        ("LINEBELOW",   (0,0), (-1,-1), 0.3, BORDER),
        ("LEFTPADDING", (0,0), (0,-1),  0),
        ("RIGHTPADDING",(-1,0),(-1,-1), 0),
    ]))

    t.wrapOn(c, W - 30*mm, H)
    t_h = t._height
    t.drawOn(c, 15*mm, y_table_top - t_h - 4*mm)

    # ── TOTALS BOX ──
    y_totals = y_table_top - t_h - 20*mm
    box_x    = W - 90*mm
    box_w    = 75*mm

    def total_row(label, value, bold=False, accent=False):
        nonlocal y_totals
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 10 if bold else 9)
        c.setFillColor(DARK if not accent else ACCENT)
        c.drawString(box_x, y_totals, label)
        c.drawRightString(box_x + box_w, y_totals, value)
        y_totals -= 8*mm

    total_row("Subtotal",              fmt_ngn(subtotal))
    if tax_pct > 0:
        total_row(f"Tax ({tax_pct}%)", fmt_ngn(tax_amt))

    y_totals -= 6*mm  # Add extra spacing before the Total box

    # Total band
    c.setFillColor(DARK)
    c.rect(box_x - 3*mm, y_totals - 4*mm, box_w + 6*mm, 12*mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(box_x, y_totals + 2*mm, "TOTAL DUE")
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(box_x + box_w, y_totals + 2*mm, fmt_ngn(total))
    y_totals -= 14*mm

    # ── NOTES ──
    notes = data.get("notes", "")
    if notes:
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(15*mm, y_totals, "NOTES")
        c.setFillColor(DARK)
        c.setFont("Helvetica", 9)
        c.drawString(15*mm, y_totals - 6*mm, str(notes))

    # ── FOOTER ──
    c.setFillColor(DARK)
    c.rect(0, 0, W, 18*mm, fill=1, stroke=0)
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(W/2, 10*mm, "Thank you for your business!")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawCentredString(W/2, 5*mm, f"Generated by BizIQ  •  {str(data['business'].get('email',''))}  •  {str(data['business'].get('phone',''))}")

    c.save()
    return buf.getvalue()


# ── Quick test ──
if __name__ == "__main__":
    sample = {
        "invoice_number": "INV-001",
        "issue_date":     "2026-03-05",
        "due_date":       "2026-03-19",
        "business": {
            "name":    "Musa's Store",
            "address": "12 Market Street, Abuja, Nigeria",
            "phone":   "+234 801 234 5678",
            "email":   "musa@biziq.app",
        },
        "customer": {
            "name":    "Ade Foods Ltd",
            "address": "45 Ring Road, Lagos, Nigeria",
            "phone":   "+234 802 345 6789",
            "email":   "ade@adefoods.com",
        },
        "items": [
            {"description": "Rice (50kg bag)",        "qty": 10, "unit_price": 45000},
            {"description": "Flour (50kg bag)",       "qty": 5,  "unit_price": 42000},
            {"description": "Palm Oil (25 litre)",    "qty": 8,  "unit_price": 18500},
            {"description": "Sugar (50kg bag)",       "qty": 3,  "unit_price": 28000},
        ],
        "tax_percent": 7.5,
        "notes": "Payment due within 14 days. Bank: GTBank  Acc: 0123456789  Name: Musa Store",
    }
    pdf_bytes = generate_invoice(sample)
    with open("sample_invoice.pdf", "wb") as f:
        f.write(pdf_bytes)
    print(f"Done — {len(pdf_bytes):,} bytes")
