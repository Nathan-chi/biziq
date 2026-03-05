import { useState, useEffect, useCallback } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const fmt = n => "₦" + Number(n || 0).toLocaleString();

const Card = ({ children, style = {} }) => (
    <div style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 12, padding: 20, ...style }}>
        {children}
    </div>
);

const Label = ({ children }) => (
    <div style={{ fontSize: 11, color: "#484f58", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6, fontWeight: 600 }}>
        {children}
    </div>
);

const inputStyle = {
    width: "100%", background: "#0d1117", border: "1.5px solid #21262d",
    borderRadius: 8, padding: "10px 14px", color: "#e6edf3", fontSize: 13,
    outline: "none", boxSizing: "border-box", fontFamily: "inherit", transition: "border 0.2s",
};
const focusIn = e => { e.target.style.borderColor = "#00d4aa"; };
const focusOut = e => { e.target.style.borderColor = "#21262d"; };

const Field = ({ label, value, onChange, placeholder = "", type = "text" }) => (
    <div style={{ marginBottom: 14 }}>
        {label && <Label>{label}</Label>}
        <input type={type} value={value} placeholder={placeholder}
            onChange={e => onChange(e.target.value)}
            style={inputStyle} onFocus={focusIn} onBlur={focusOut} />
    </div>
);

const EMPTY_CUSTOMER = { name: "", address: "", phone: "", email: "" };
const EMPTY_ITEM = { description: "", qty: 1, unit_price: "" };

export default function InvoiceGenerator({ token }) {
    const [view, setView] = useState("list");
    const [invoices, setInvoices] = useState([]);
    const [loading, setLoading] = useState(false);
    const [flash, setFlash] = useState(null);

    const [customer, setCustomer] = useState({ ...EMPTY_CUSTOMER });
    const [items, setItems] = useState([{ ...EMPTY_ITEM }]);
    const [taxPct, setTaxPct] = useState(0);
    const [dueDays, setDueDays] = useState(14);
    const [notes, setNotes] = useState("");
    const [saving, setSaving] = useState(false);

    const showFlash = (msg, ok = true) => {
        setFlash({ msg, ok });
        setTimeout(() => setFlash(null), 3000);
    };

    const apiFetch = useCallback(async (url, opts = {}) => {
        const res = await fetch(`${API}${url}`, {
            ...opts,
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, ...opts.headers },
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Error ${res.status}`);
        }
        return res.json();
    }, [token]);

    const loadInvoices = useCallback(async () => {
        setLoading(true);
        try {
            const data = await apiFetch("/invoices/list");
            setInvoices(Array.isArray(data) ? data : []);
        } catch (e) {
            showFlash("Could not load invoices: " + e.message, false);
        } finally {
            setLoading(false);
        }
    }, [apiFetch]);

    useEffect(() => { loadInvoices(); }, [loadInvoices]);

    const resetForm = () => {
        setCustomer({ ...EMPTY_CUSTOMER });
        setItems([{ ...EMPTY_ITEM }]);
        setTaxPct(0); setDueDays(14); setNotes("");
    };

    const addItem = () => setItems(p => [...p, { ...EMPTY_ITEM }]);
    const removeItem = idx => setItems(p => p.filter((_, i) => i !== idx));
    const updateItem = (idx, field, val) =>
        setItems(p => p.map((item, i) => i === idx ? { ...item, [field]: val } : item));

    const subtotal = items.reduce((s, i) => s + (parseFloat(i.qty) || 0) * (parseFloat(i.unit_price) || 0), 0);
    const taxAmt = subtotal * (parseFloat(taxPct) || 0) / 100;
    const total = subtotal + taxAmt;

    const createInvoice = async () => {
        if (!customer.name.trim())
            return showFlash("Please enter a customer name", false);
        if (items.some(i => !i.description.trim() || !i.unit_price))
            return showFlash("Fill in all item descriptions and prices", false);
        if (total <= 0)
            return showFlash("Total must be greater than zero", false);

        setSaving(true);
        try {
            const res = await apiFetch("/invoices/create", {
                method: "POST",
                body: JSON.stringify({
                    customer,
                    items: items.map(i => ({
                        description: i.description,
                        qty: parseFloat(i.qty) || 1,
                        unit_price: parseFloat(i.unit_price) || 0,
                    })),
                    tax_percent: parseFloat(taxPct) || 0,
                    due_days: parseInt(dueDays) || 14,
                    notes,
                }),
            });
            showFlash(`${res.invoice_number} created!`);
            resetForm();
            setView("list");
            loadInvoices();
        } catch (e) {
            showFlash("Failed: " + e.message, false);
        } finally {
            setSaving(false);
        }
    };

    const downloadPDF = async (invId, invNumber) => {
        try {
            const res = await fetch(`${API}/invoices/download/${invId}`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) throw new Error("Download failed");
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = Object.assign(document.createElement("a"), { href: url, download: `${invNumber}.pdf` });
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (e) {
            showFlash("PDF download failed: " + e.message, false);
        }
    };

    const deleteInvoice = async (id) => {
        if (!window.confirm("Delete this invoice?")) return;
        try {
            await apiFetch(`/invoices/${id}`, { method: "DELETE" });
            showFlash("Invoice deleted");
            loadInvoices();
        } catch (e) {
            showFlash("Delete failed: " + e.message, false);
        }
    };

    const statusColor = s => s === "paid" ? "#00d4aa" : s === "overdue" ? "#ff4444" : "#f5a623";

    return (
        <div style={{ fontFamily: "'DM Sans','Segoe UI',sans-serif", color: "#e6edf3" }}>

            {flash && (
                <div style={{
                    position: "fixed", top: 20, right: 20, zIndex: 9999,
                    background: flash.ok ? "#00d4aa" : "#ff4444", color: "#0d1117",
                    borderRadius: 8, padding: "10px 18px", fontSize: 13, fontWeight: 700,
                    boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
                }}>{flash.msg}</div>
            )}

            {/* Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
                <div>
                    <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>
                        {view === "list" ? "🧾 Invoices" : "➕ New Invoice"}
                    </h2>
                    <div style={{ fontSize: 12, color: "#484f58", marginTop: 3 }}>
                        {view === "list"
                            ? `${invoices.length} invoice${invoices.length !== 1 ? "s" : ""}`
                            : "Fill in the details below"}
                    </div>
                </div>
                <div style={{ display: "flex", gap: 10 }}>
                    {view === "create" && (
                        <div onClick={() => { setView("list"); resetForm(); }} style={{
                            background: "#21262d", border: "1px solid #30363d", borderRadius: 8,
                            padding: "9px 16px", fontSize: 13, color: "#8b949e", cursor: "pointer",
                        }}>← Back</div>
                    )}
                    {view === "list" && (
                        <div onClick={() => setView("create")} style={{
                            background: "linear-gradient(135deg,#00d4aa,#4a9eff)", borderRadius: 8,
                            padding: "9px 18px", fontSize: 13, fontWeight: 700, color: "#0d1117", cursor: "pointer",
                        }}>+ New Invoice</div>
                    )}
                </div>
            </div>

            {/* ── LIST ── */}
            {view === "list" && (
                <div>
                    {loading && <div style={{ color: "#484f58", textAlign: "center", padding: 48 }}>Loading...</div>}

                    {!loading && invoices.length === 0 && (
                        <Card style={{ textAlign: "center", padding: "56px 24px" }}>
                            <div style={{ fontSize: 52, marginBottom: 14 }}>🧾</div>
                            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>No invoices yet</div>
                            <div style={{ fontSize: 13, color: "#484f58", marginBottom: 28 }}>
                                Create your first invoice to send to a customer
                            </div>
                            <div onClick={() => setView("create")} style={{
                                display: "inline-block",
                                background: "linear-gradient(135deg,#00d4aa,#4a9eff)",
                                borderRadius: 8, padding: "11px 28px",
                                fontWeight: 700, fontSize: 13, color: "#0d1117", cursor: "pointer",
                            }}>+ Create Invoice</div>
                        </Card>
                    )}

                    {invoices.map(inv => (
                        <Card key={inv.id} style={{ marginBottom: 10, display: "flex", alignItems: "center", gap: 16 }}>
                            <div style={{ width: 44, height: 44, borderRadius: 10, background: "rgba(0,212,170,0.1)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, flexShrink: 0 }}>🧾</div>
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
                                    <div style={{ fontSize: 14, fontWeight: 700 }}>{inv.invoice_number}</div>
                                    <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", background: `${statusColor(inv.status)}22`, color: statusColor(inv.status), borderRadius: 20, padding: "2px 10px" }}>
                                        {inv.status}
                                    </div>
                                </div>
                                <div style={{ fontSize: 13, color: "#8b949e" }}>{inv.customer_name}</div>
                                <div style={{ fontSize: 11, color: "#484f58", marginTop: 2 }}>
                                    Issued: {inv.issue_date} · Due: {inv.due_date}
                                </div>
                            </div>
                            <div style={{ textAlign: "right", flexShrink: 0 }}>
                                <div style={{ fontSize: 18, fontWeight: 800, color: "#00d4aa" }}>{fmt(inv.total)}</div>
                                <div style={{ display: "flex", gap: 8, marginTop: 8, justifyContent: "flex-end" }}>
                                    <div onClick={() => downloadPDF(inv.id, inv.invoice_number)} style={{ background: "#21262d", border: "1px solid #30363d", borderRadius: 6, padding: "5px 12px", fontSize: 12, color: "#8b949e", cursor: "pointer" }}>
                                        ⬇ PDF
                                    </div>
                                    <div onClick={() => deleteInvoice(inv.id)} style={{ background: "rgba(255,68,68,0.08)", border: "1px solid rgba(255,68,68,0.2)", borderRadius: 6, padding: "5px 10px", fontSize: 12, color: "#ff4444", cursor: "pointer" }}>
                                        ✕
                                    </div>
                                </div>
                            </div>
                        </Card>
                    ))}
                </div>
            )}

            {/* ── CREATE ── */}
            {view === "create" && (
                <div className="grid-mobile-stack" style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 20 }}>

                    <div>
                        {/* Customer */}
                        <Card style={{ marginBottom: 16 }}>
                            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 16 }}>👤 Customer Details</div>
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 16px" }}>
                                <Field label="Name *" value={customer.name} onChange={v => setCustomer(c => ({ ...c, name: v }))} placeholder="Ade Foods Ltd" />
                                <Field label="Email" value={customer.email} onChange={v => setCustomer(c => ({ ...c, email: v }))} placeholder="customer@example.com" type="email" />
                                <Field label="Phone" value={customer.phone} onChange={v => setCustomer(c => ({ ...c, phone: v }))} placeholder="+234 801 234 5678" />
                                <Field label="Address" value={customer.address} onChange={v => setCustomer(c => ({ ...c, address: v }))} placeholder="City, State" />
                            </div>
                        </Card>

                        {/* Items */}
                        <Card style={{ marginBottom: 16 }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                                <div style={{ fontSize: 13, fontWeight: 700 }}>🛒 Items</div>
                                <div onClick={addItem} style={{ fontSize: 12, color: "#00d4aa", cursor: "pointer", fontWeight: 600 }}>+ Add Item</div>
                            </div>
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 70px 120px 32px", gap: 8, marginBottom: 8 }}>
                                {["Description", "Qty", "Unit Price (₦)", ""].map((h, i) => (
                                    <div key={i} style={{ fontSize: 10, color: "#484f58", textTransform: "uppercase", letterSpacing: 0.5, fontWeight: 600 }}>{h}</div>
                                ))}
                            </div>
                            {items.map((item, idx) => (
                                <div key={idx} style={{ display: "grid", gridTemplateColumns: "1fr 70px 120px 32px", gap: 8, marginBottom: 8, alignItems: "center" }}>
                                    <input value={item.description} placeholder="e.g. Rice (50kg)" onChange={e => updateItem(idx, "description", e.target.value)} style={{ ...inputStyle, padding: "9px 12px" }} onFocus={focusIn} onBlur={focusOut} />
                                    <input type="number" min="1" value={item.qty} onChange={e => updateItem(idx, "qty", e.target.value)} style={{ ...inputStyle, padding: "9px 10px" }} onFocus={focusIn} onBlur={focusOut} />
                                    <input type="number" min="0" value={item.unit_price} placeholder="45000" onChange={e => updateItem(idx, "unit_price", e.target.value)} style={{ ...inputStyle, padding: "9px 10px" }} onFocus={focusIn} onBlur={focusOut} />
                                    <div onClick={() => items.length > 1 && removeItem(idx)} style={{ color: "#ff4444", cursor: items.length > 1 ? "pointer" : "default", fontSize: 16, textAlign: "center", opacity: items.length > 1 ? 1 : 0.25 }}>✕</div>
                                </div>
                            ))}
                        </Card>

                        {/* Options */}
                        <Card>
                            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 16 }}>⚙️ Options</div>
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 16px", marginBottom: 14 }}>
                                <div>
                                    <Label>Tax %</Label>
                                    <input type="number" min="0" max="100" value={taxPct} onChange={e => setTaxPct(e.target.value)} style={inputStyle} onFocus={focusIn} onBlur={focusOut} />
                                </div>
                                <div>
                                    <Label>Due in (days)</Label>
                                    <input type="number" min="1" value={dueDays} onChange={e => setDueDays(e.target.value)} style={inputStyle} onFocus={focusIn} onBlur={focusOut} />
                                </div>
                            </div>
                            <Label>Notes / Payment Instructions</Label>
                            <textarea value={notes} rows={3} onChange={e => setNotes(e.target.value)}
                                placeholder="e.g. Bank: GTBank  Acc: 0123456789  Name: Musa Store"
                                style={{ ...inputStyle, resize: "vertical" }} onFocus={focusIn} onBlur={focusOut} />
                        </Card>
                    </div>

                    {/* Summary */}
                    <div>
                        <Card style={{ position: "sticky", top: 20 }}>
                            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 16 }}>📋 Summary</div>
                            {items.map((item, i) => {
                                const amt = (parseFloat(item.qty) || 0) * (parseFloat(item.unit_price) || 0);
                                if (!amt) return null;
                                return (
                                    <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 8, paddingBottom: 8, borderBottom: "1px solid #21262d" }}>
                                        <span style={{ color: "#8b949e", marginRight: 8, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                            {item.description || `Item ${i + 1}`} ×{item.qty}
                                        </span>
                                        <span style={{ flexShrink: 0 }}>{fmt(amt)}</span>
                                    </div>
                                );
                            })}
                            <div style={{ marginTop: 12 }}>
                                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 8 }}>
                                    <span style={{ color: "#8b949e" }}>Subtotal</span>
                                    <span>{fmt(subtotal)}</span>
                                </div>
                                {parseFloat(taxPct) > 0 && (
                                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 8 }}>
                                        <span style={{ color: "#8b949e" }}>Tax ({taxPct}%)</span>
                                        <span>{fmt(taxAmt)}</span>
                                    </div>
                                )}
                                <div style={{ background: "#0d1117", borderRadius: 10, padding: "14px 16px", marginTop: 10 }}>
                                    <div style={{ fontSize: 10, color: "#484f58", textTransform: "uppercase", letterSpacing: 1 }}>Total Due</div>
                                    <div style={{ fontSize: 26, fontWeight: 800, color: "#00d4aa", marginTop: 4 }}>{fmt(total)}</div>
                                </div>
                            </div>
                            <div onClick={!saving ? createInvoice : undefined} style={{
                                marginTop: 20, borderRadius: 10, padding: "13px", textAlign: "center",
                                fontWeight: 700, fontSize: 14, transition: "all 0.2s",
                                background: saving ? "#21262d" : "linear-gradient(135deg,#00d4aa,#4a9eff)",
                                color: saving ? "#484f58" : "#0d1117",
                                cursor: saving ? "not-allowed" : "pointer",
                            }}>
                                {saving ? "Creating..." : "🧾 Create Invoice"}
                            </div>
                            <div style={{ fontSize: 11, color: "#484f58", textAlign: "center", marginTop: 10 }}>
                                PDF ready to download instantly
                            </div>
                        </Card>
                    </div>

                </div>
            )}
        </div>
    );
}
