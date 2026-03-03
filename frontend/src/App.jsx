import { useState, useEffect } from "react";
import BizIQChatbot from "./components/Chatbot";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ── API helpers (attach token automatically) ──
const authFetch = (url, options = {}, token) => {
  return fetch(`${API}${url}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  }).then(r => r.json());
};

const NAV = ["Dashboard", "AI Predictions", "Data Entry", "Market Trends", "Reports", "Settings"];
const fmt = (n) => "₦" + Number(n || 0).toLocaleString();

// ──────────────────────────────────────────────
// AUTH INPUT — defined outside AuthScreen to prevent remount on every keystroke
// ──────────────────────────────────────────────

const AuthInput = ({ label, field, type = "text", placeholder = "", value, onChange }) => (
  <div style={{ marginBottom: 16 }}>
    <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 6, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5 }}>{label}</div>
    <input type={type} value={value} onChange={onChange} placeholder={placeholder}
      style={{ width: "100%", background: "#0d1117", border: "1px solid #30363d", borderRadius: 8, padding: "11px 14px", color: "#e6edf3", fontSize: 14, outline: "none", boxSizing: "border-box", transition: "border 0.2s" }}
      onFocus={e => e.target.style.borderColor = "#00d4aa"}
      onBlur={e => e.target.style.borderColor = "#30363d"}
    />
  </div>
);

// ──────────────────────────────────────────────
// AUTH SCREENS
// ──────────────────────────────────────────────

function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState("login"); // login | register
  const [form, setForm] = useState({ email: "", password: "", full_name: "", business_name: "", industry: "Retail", location: "Nigeria" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const f = (k) => (e) => setForm(prev => ({ ...prev, [k]: e.target.value }));

  const submit = async () => {
    setError(""); setLoading(true);
    try {
      const endpoint = mode === "login" ? "/auth/login" : "/auth/register";
      const body = mode === "login"
        ? { email: form.email, password: form.password }
        : form;
      const res = await authFetch(endpoint, { method: "POST", body: JSON.stringify(body) });
      if (res.token) {
        localStorage.setItem("biziq_token", res.token);
        localStorage.setItem("biziq_user", JSON.stringify(res.user));
        onAuth(res.user, res.token);
      } else {
        setError(res.detail || "Something went wrong");
      }
    } catch (e) {
      setError("Cannot connect to server. Is the backend running?");
    }
    setLoading(false);
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0d1117", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'DM Sans','Segoe UI',sans-serif" }}>

      {/* Background glow */}
      <div style={{ position: "fixed", top: "20%", left: "50%", transform: "translateX(-50%)", width: 600, height: 300, background: "radial-gradient(ellipse, rgba(0,212,170,0.06) 0%, transparent 70%)", pointerEvents: "none" }} />

      <div style={{ width: "100%", maxWidth: 440, padding: "0 24px" }}>

        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div style={{ fontSize: 36, fontWeight: 900, letterSpacing: -2, background: "linear-gradient(135deg,#00d4aa,#4a9eff)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>BizIQ</div>
          <div style={{ fontSize: 13, color: "#484f58", marginTop: 4, letterSpacing: 1, textTransform: "uppercase" }}>AI-Powered Business Intelligence</div>
        </div>

        {/* Card */}
        <div style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 16, padding: "32px" }}>

          {/* Tab switcher */}
          <div style={{ display: "flex", background: "#0d1117", borderRadius: 10, padding: 4, marginBottom: 28 }}>
            {["login", "register"].map(m => (
              <div key={m} onClick={() => { setMode(m); setError(""); }} style={{
                flex: 1, textAlign: "center", padding: "9px", borderRadius: 7, cursor: "pointer",
                fontSize: 13, fontWeight: 600, textTransform: "capitalize", transition: "all 0.2s",
                background: mode === m ? "linear-gradient(135deg,#00d4aa,#4a9eff)" : "transparent",
                color: mode === m ? "#0d1117" : "#8b949e",
              }}>{m === "login" ? "Sign In" : "Create Account"}</div>
            ))}
          </div>

          {/* Error */}
          {error && (
            <div style={{ background: "rgba(255,68,68,0.1)", border: "1px solid rgba(255,68,68,0.3)", borderRadius: 8, padding: "10px 14px", fontSize: 13, color: "#ff4444", marginBottom: 18 }}>
              ⚠️ {error}
            </div>
          )}

          {/* Fields */}
          {mode === "register" && <AuthInput label="Full Name" field="full_name" placeholder="e.g. Musa Abubakar" value={form.full_name} onChange={f("full_name")} />}
          <AuthInput label="Email Address" field="email" type="email" placeholder="you@example.com" value={form.email} onChange={f("email")} />
          <AuthInput label="Password" field="password" type="password" placeholder={mode === "register" ? "Minimum 8 characters" : "Your password"} value={form.password} onChange={f("password")} />
          {mode === "register" && (
            <>
              <AuthInput label="Business Name" field="business_name" placeholder="e.g. Musa's Store" value={form.business_name} onChange={f("business_name")} />
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, color: "#8b949e", marginBottom: 6, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5 }}>Industry</div>
                <select value={form.industry} onChange={f("industry")} style={{ width: "100%", background: "#0d1117", border: "1px solid #30363d", borderRadius: 8, padding: "11px 14px", color: "#e6edf3", fontSize: 14, outline: "none", boxSizing: "border-box" }}>
                  {["Retail", "Food & Restaurant", "Agriculture", "Manufacturing", "Services", "Healthcare", "Education", "Other"].map(i => (
                    <option key={i} value={i}>{i}</option>
                  ))}
                </select>
              </div>
              <AuthInput label="Location" field="location" placeholder="e.g. Abuja, Nigeria" value={form.location} onChange={f("location")} />
            </>
          )}

          {/* Submit */}
          <div onClick={submit} style={{
            background: loading ? "#21262d" : "linear-gradient(135deg,#00d4aa,#4a9eff)",
            borderRadius: 10, padding: "13px", textAlign: "center", fontWeight: 700, fontSize: 14,
            color: loading ? "#484f58" : "#0d1117", cursor: loading ? "not-allowed" : "pointer",
            marginTop: 8, transition: "all 0.2s",
          }}>
            {loading ? "Please wait..." : mode === "login" ? "Sign In →" : "Create My Account →"}
          </div>

          {mode === "login" && (
            <div style={{ textAlign: "center", marginTop: 16, fontSize: 12, color: "#484f58" }}>
              Don't have an account?{" "}
              <span onClick={() => setMode("register")} style={{ color: "#00d4aa", cursor: "pointer" }}>Sign up free</span>
            </div>
          )}
        </div>

        <div style={{ textAlign: "center", marginTop: 20, fontSize: 11, color: "#484f58" }}>
          🔒 Your data is encrypted and private to your account
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────
// MAIN APP (shown after login)
// ──────────────────────────────────────────────

const Card = ({ children, style = {} }) => (
  <div style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 12, padding: "20px", ...style }}>{children}</div>
);
const Label = ({ children }) => (
  <div style={{ fontSize: 11, color: "#484f58", textTransform: "uppercase", letterSpacing: 1, marginBottom: 6 }}>{children}</div>
);
const ScoreBar = ({ score, max, color }) => (
  <div style={{ background: "#0d1117", borderRadius: 6, height: 8, overflow: "hidden", marginTop: 6 }}>
    <div style={{ width: `${(score / max) * 100}%`, background: color, height: "100%", borderRadius: 6, transition: "width 1.2s ease" }} />
  </div>
);

function MainApp({ user: initialUser, token, onLogout }) {
  const [nav, setNav] = useState("Dashboard");
  const [showMobileSidebar, setShowMobileSidebar] = useState(false);
  const [user, setUser] = useState(initialUser);
  const [summary, setSummary] = useState({});
  const [transactions, setTxns] = useState([]);
  const [trends, setTrends] = useState([]);
  const [advice, setAdvice] = useState([]);
  const [byDay, setByDay] = useState([]);
  const [revPred, setRevPred] = useState({});
  const [expPred, setExpPred] = useState({});
  const [health, setHealth] = useState({ total_score: 0, label: "Loading..." });
  const [recs, setRecs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ type: "sales", description: "", amount: "", date: new Date().toISOString().split("T")[0], category: "" });
  const [pwForm, setPwForm] = useState({ current_password: "", new_password: "" });
  const [saving, setSaving] = useState(false);
  const [flash, setFlash] = useState("");

  const api = (url, options) => authFetch(url, options, token);
  const showFlash = (msg) => { setFlash(msg); setTimeout(() => setFlash(""), 2500); };

  useEffect(() => { loadAll(); }, []);

  const loadAll = async (isQuick = false) => {
    if (!isQuick) setLoading(true);
    const safe = async (fn) => { try { return await fn(); } catch (e) { console.warn(e); return null; } };

    try {
      const [s, t, bd] = await Promise.all([
        api("/analytics/summary"),
        api("/transactions?limit=20"),
        api("/analytics/by-day?days=7"),
      ]);

      if (s) setSummary(s);
      if (t && Array.isArray(t)) setTxns(t);
      if (bd && Array.isArray(bd)) setByDay(bd);
    } catch (e) {
      console.error(e);
      showFlash("❌ Error refreshing data");
    }

    if (isQuick === true) {
      setLoading(false);
      backgroundRefresh();
      return;
    }

    await backgroundRefresh();
    setLoading(false);
  };

  const backgroundRefresh = async () => {
    const safe = async (fn) => { try { return await fn(); } catch (e) { console.warn(e); return null; } };
    const [adv, tr, rp, ep, h] = await Promise.all([
      safe(() => api("/ai/advice")),
      safe(() => api("/market/trends")),
      safe(() => api("/ai/predict/revenue")),
      safe(() => api("/ai/predict/expenses")),
      safe(() => api("/ai/health-score")),
    ]);

    if (adv && Array.isArray(adv)) {
      setAdvice(adv);
      // Automatically keep recs in sync if they are similar
      setRecs(adv.map(a => ({ title: a.title, detail: a.text, priority: a.type, icon: a.icon, color: a.color })));
    }
    if (tr) setTrends(tr.data || []);
    if (rp) setRevPred(rp);
    if (ep) setExpPred(ep);
    if (h && h.total_score !== undefined) setHealth(h);
  };

  const saveEntry = async () => {
    if (!form.description || !form.amount) return;
    setSaving(true);
    await api("/transactions", { method: "POST", body: JSON.stringify({ ...form, amount: parseFloat(form.amount) }) });
    showFlash("✓ Entry saved!");
    setSaving(false);
    setForm({ type: "sales", description: "", amount: "", date: new Date().toISOString().split("T")[0], category: "" });
    loadAll(true);
  };

  const saveProfile = async () => {
    const res = await api("/auth/profile", {
      method: "PUT", body: JSON.stringify({
        full_name: user.full_name,
        business_name: user.business_name,
        industry: user.industry,
        location: user.location,
        currency: user.currency,
        ai_api_key: user.ai_api_key
      })
    });
    if (res.user) { setUser(res.user); showFlash("✓ Profile updated!"); }
  };

  const changePassword = async () => {
    if (!pwForm.current_password || !pwForm.new_password) return;
    const res = await api("/auth/change-password", { method: "POST", body: JSON.stringify(pwForm) });
    if (res.success) { showFlash("✓ Password changed!"); setPwForm({ current_password: "", new_password: "" }); }
    else showFlash("✗ " + (res.detail || "Error"));
  };

  const handleLogout = async () => {
    try { await api("/auth/logout", { method: "POST" }); } catch (_) { }
    localStorage.removeItem("biziq_token");
    localStorage.removeItem("biziq_user");
    onLogout();
  };

  return (
    <div style={{ fontFamily: "'DM Sans','Segoe UI',sans-serif", background: "#0d1117", minHeight: "100vh", color: "#e6edf3", display: "flex" }}>

      {/* Flash message */}
      {flash && (
        <div style={{ position: "fixed", top: 20, right: 20, background: flash.startsWith("✗") ? "#ff4444" : "#00d4aa", color: "#0d1117", borderRadius: 8, padding: "10px 18px", fontSize: 13, fontWeight: 700, zIndex: 1000, boxShadow: "0 4px 20px rgba(0,0,0,0.3)" }}>
          {flash}
        </div>
      )}

      {/* Mobile Header Overlay (when sidebar open) */}
      {showMobileSidebar && (
        <div
          onClick={() => setShowMobileSidebar(false)}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 100, backdropFilter: "blur(4px)" }}
          className="show-mobile"
        />
      )}

      {/* Sidebar */}
      <div
        className={showMobileSidebar ? "animate-slide-in" : "hide-mobile"}
        style={{
          width: 220, borderRight: "1px solid #21262d", display: "flex", flexDirection: "column",
          padding: "24px 0", position: "fixed", height: "100vh", zIndex: 101, background: "#0d1117",
          ...(showMobileSidebar ? { display: "flex", width: 260 } : {})
        }}
      >
        <div style={{ padding: "0 20px 24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: 22, fontWeight: 900, letterSpacing: -1, background: "linear-gradient(135deg,#00d4aa,#4a9eff)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>BizIQ</div>
            <div style={{ fontSize: 10, color: "#484f58", letterSpacing: 1, textTransform: "uppercase", marginTop: 2 }}>Business Intelligence</div>
          </div>
          <div onClick={() => setShowMobileSidebar(false)} className="show-mobile" style={{ cursor: "pointer", color: "#8b949e", fontSize: 20 }}>✕</div>
        </div>
        {NAV.map(n => (
          <div key={n} onClick={() => { setNav(n); setShowMobileSidebar(false); }} style={{
            padding: "11px 20px", cursor: "pointer", fontSize: 13, fontWeight: 500,
            color: nav === n ? "#00d4aa" : "#8b949e",
            background: nav === n ? "rgba(0,212,170,0.08)" : "transparent",
            borderLeft: nav === n ? "2px solid #00d4aa" : "2px solid transparent",
            transition: "all 0.15s",
          }}>{n === "AI Predictions" ? "🧠 " : ""}{n}</div>
        ))}

        {/* User info + logout */}
        <div style={{ marginTop: "auto", padding: "16px 20px", borderTop: "1px solid #21262d" }}>
          {health && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, color: "#484f58", textTransform: "uppercase", letterSpacing: 1 }}>Health Score</div>
              <div style={{ fontSize: 26, fontWeight: 800, color: health.color }}>{health.total_score}<span style={{ fontSize: 12, color: "#484f58" }}>/100</span></div>
              <div style={{ fontSize: 11, color: health.color }}>{health.grade} — {health.label}</div>
            </div>
          )}
          <div style={{ fontSize: 12, color: "#8b949e", fontWeight: 600 }}>{user.business_name}</div>
          <div style={{ fontSize: 11, color: "#484f58" }}>{user.email}</div>
          <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
            <div style={{ fontSize: 10, background: "rgba(0,212,170,0.1)", color: "#00d4aa", padding: "3px 8px", borderRadius: 20, border: "1px solid rgba(0,212,170,0.2)" }}>
              {loading ? "⟳" : "● Live"}
            </div>
            <div onClick={handleLogout} style={{ fontSize: 10, background: "rgba(255,68,68,0.1)", color: "#ff4444", padding: "3px 8px", borderRadius: 20, border: "1px solid rgba(255,68,68,0.2)", cursor: "pointer" }}>
              Sign Out
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="main-content" style={{ marginLeft: 220, flex: 1, padding: "28px 32px" }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 26, gap: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div onClick={() => setShowMobileSidebar(true)} className="show-mobile" style={{ cursor: "pointer", background: "#161b22", padding: "8px", borderRadius: 8, border: "1px solid #21262d" }}>
              <div style={{ width: 18, height: 2, background: "#8b949e", marginBottom: 4 }}></div>
              <div style={{ width: 18, height: 2, background: "#8b949e", marginBottom: 4 }}></div>
              <div style={{ width: 18, height: 2, background: "#8b949e" }}></div>
            </div>
            <div>
              <h1 style={{ fontSize: 22, fontWeight: 700, margin: 0, letterSpacing: -0.5 }}>{nav}</h1>
              <div className="hide-mobile" style={{ fontSize: 12, color: "#484f58", marginTop: 3 }}>
                Welcome back, {user.full_name} · {new Date().toDateString()}
              </div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <div onClick={() => loadAll()} style={{ background: "#161b22", border: "1px solid #21262d", borderRadius: 8, padding: "8px 14px", fontSize: 12, color: "#8b949e", cursor: "pointer" }}>↻<span className="hide-mobile"> Refresh</span></div>
            <div onClick={() => setNav("Data Entry")} style={{ background: "linear-gradient(135deg,#00d4aa,#4a9eff)", borderRadius: 8, padding: "8px 14px", fontSize: 12, fontWeight: 700, color: "#0d1117", cursor: "pointer" }}>+<span className="hide-mobile"> New Entry</span></div>
          </div>
        </div>

        {/* DASHBOARD */}
        {nav === "Dashboard" && (
          <div>
            <div className="grid-cols-4" style={{ display: "grid", gap: 14, marginBottom: 18 }}>
              {[
                { label: "Monthly Revenue", value: fmt(summary.monthly_revenue), color: "#00d4aa" },
                { label: "Op. Expenses", value: fmt(summary.operating_expenses), color: "#ff4444" },
                { label: "Inventory Value", value: fmt(summary.inventory_value), color: "#4a9eff" },
                { label: "Net Profit", value: fmt(summary.net_profit), color: (summary.net_profit || 0) > 0 ? "#00d4aa" : "#ff4444" },
              ].map((s, i) => (
                <Card key={i}>
                  <Label>{s.label}</Label>
                  <div style={{ fontSize: 20, fontWeight: 700, color: s.color }}>{s.value}</div>
                </Card>
              ))}
            </div>
            <div className="grid-mobile-stack" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              <Card>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 14 }}>🤖 AI Insights</div>
                {advice.slice(0, 3).map((a, i) => (
                  <div key={i} style={{ display: "flex", gap: 10, marginBottom: 10, padding: "10px", background: "#0d1117", borderRadius: 8, borderLeft: `3px solid ${a.color}` }}>
                    <div>{a.icon}</div>
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 700, color: a.color, textTransform: "uppercase" }}>{a.title}</div>
                      <div style={{ fontSize: 12, color: "#8b949e", marginTop: 2, lineHeight: 1.5 }}>{a.text}</div>
                    </div>
                  </div>
                ))}
              </Card>
              <Card>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 14 }}>📋 Recent Transactions</div>
                {transactions.slice(0, 6).map((t, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: i < 5 ? "1px solid #21262d" : "none" }}>
                    <div>
                      <div style={{ fontSize: 12 }}>{t.description}</div>
                      <div style={{ fontSize: 11, color: "#484f58" }}>{t.date}</div>
                    </div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: t.type === "sales" ? "#00d4aa" : "#ff4444" }}>
                      {t.type === "sales" ? "+" : "-"}{fmt(t.amount)}
                    </div>
                  </div>
                ))}
              </Card>
            </div>
          </div>
        )}

        {/* AI PREDICTIONS */}
        {nav === "AI Predictions" && (
          <div>
            {health && (
              <Card style={{ marginBottom: 16, background: `linear-gradient(135deg, ${health.color}10, #161b22)`, border: `1px solid ${health.color}30` }}>
                <div className="grid-mobile-stack" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 20 }}>
                  <div>
                    <Label>Business Health Score</Label>
                    <div style={{ fontSize: 52, fontWeight: 900, color: health.color, lineHeight: 1 }}>{health.total_score}<span style={{ fontSize: 18, color: "#484f58" }}>/100</span></div>
                    <div style={{ fontSize: 14, color: health.color, marginTop: 4, fontWeight: 600 }}>{health.grade} — {health.label}</div>
                    <div style={{ fontSize: 12, color: "#8b949e", marginTop: 6 }}>{health.tip}</div>
                  </div>
                  <div style={{ width: "100%", maxWidth: 240 }}>
                    {health.breakdown && Object.values(health.breakdown).map((b, i) => (
                      <div key={i} style={{ marginBottom: 14 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                          <span style={{ color: "#8b949e" }}>{b.label}</span>
                          <span style={{ color: health.color, fontWeight: 700 }}>{b.score}/{b.max}</span>
                        </div>
                        <ScoreBar score={b.score} max={b.max} color={health.color} />
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            )}
            <div className="grid-mobile-stack" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 16 }}>
              {revPred?.status === "success" && (
                <Card>
                  <Label>Revenue Forecast — Next 30 Days</Label>
                  <div style={{ fontSize: 24, fontWeight: 800, color: "#00d4aa" }}>{fmt(revPred.predicted_next_30_days)}</div>
                  <div style={{ fontSize: 13, color: revPred.trend === "up" ? "#00d4aa" : "#ff4444", marginBottom: 12 }}>
                    {revPred.trend === "up" ? "▲" : "▼"} {Math.abs(revPred.growth_forecast_pct)}% vs current
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{ fontSize: 11, color: "#8b949e" }}>Confidence</div>
                    <div style={{ flex: 1 }}><ScoreBar score={revPred.confidence} max={100} color="#00d4aa" /></div>
                    <div style={{ fontSize: 11, color: "#00d4aa", fontWeight: 700 }}>{revPred.confidence}%</div>
                  </div>
                </Card>
              )}
              {expPred?.status === "success" && (
                <Card>
                  <Label>Expense Forecast — Next 30 Days</Label>
                  <div style={{ fontSize: 24, fontWeight: 800, color: "#ff4444" }}>{fmt(expPred.predicted_next_30_days)}</div>
                  {revPred?.status === "success" && (
                    <div style={{ background: "#0d1117", borderRadius: 8, padding: "10px 14px", marginBottom: 12 }}>
                      <div style={{ fontSize: 11, color: "#484f58" }}>Predicted Net Profit</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: "#4a9eff" }}>
                        {fmt(revPred.predicted_next_30_days - expPred.predicted_next_30_days)}
                      </div>
                    </div>
                  )}
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{ fontSize: 11, color: "#8b949e" }}>Confidence</div>
                    <div style={{ flex: 1 }}><ScoreBar score={expPred.confidence} max={100} color="#ff4444" /></div>
                    <div style={{ fontSize: 11, color: "#ff4444", fontWeight: 700 }}>{expPred.confidence}%</div>
                  </div>
                </Card>
              )}
            </div>
            <Card>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 16 }}>🎯 Smart Recommendations</div>
              {recs.map((r, i) => (
                <div key={i} style={{ background: "#0d1117", borderRadius: 10, padding: "16px", marginBottom: 10, borderLeft: `4px solid ${r.color}`, display: "flex", gap: 14 }}>
                  <div style={{ fontSize: 22 }}>{r.icon}</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10, color: r.color, textTransform: "uppercase", letterSpacing: 1, fontWeight: 700 }}>{r.category} · {r.priority}</div>
                    <div style={{ fontSize: 13, fontWeight: 700, marginTop: 2 }}>{r.title}</div>
                    <div style={{ fontSize: 12, color: "#8b949e", marginTop: 4, lineHeight: 1.5 }}>{r.detail}</div>
                    <div style={{ marginTop: 8, display: "inline-block", background: `${r.color}15`, color: r.color, fontSize: 11, padding: "3px 10px", borderRadius: 20, border: `1px solid ${r.color}30` }}>✓ {r.action}</div>
                  </div>
                  <div style={{ fontSize: 11, color: "#484f58" }}>{r.confidence}% conf.</div>
                </div>
              ))}
            </Card>
          </div>
        )}

        {/* DATA ENTRY */}
        {nav === "Data Entry" && (
          <div className="grid-mobile-stack" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <Card>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 20 }}>Record a Transaction</div>
              <div style={{ display: "flex", background: "#0d1117", borderRadius: 8, padding: 4, marginBottom: 18 }}>
                {["sales", "expense", "inventory"].map(t => (
                  <div key={t} onClick={() => setForm({ ...form, type: t })} style={{
                    flex: 1, textAlign: "center", padding: "8px", borderRadius: 6, cursor: "pointer",
                    fontSize: 12, fontWeight: 600, textTransform: "capitalize", transition: "all 0.15s",
                    background: form.type === t ? (t === "sales" ? "#00d4aa" : t === "expense" ? "#ff4444" : "#4a9eff") : "transparent",
                    color: form.type === t ? "#0d1117" : "#8b949e",
                  }}>{t}</div>
                ))}
              </div>
              {[
                { label: "Description", key: "description", placeholder: "e.g. Daily sales revenue", type: "text" },
                { label: "Amount (₦)", key: "amount", placeholder: "e.g. 150000", type: "number" },
                { label: "Category", key: "category", placeholder: "Revenue / Inventory", type: "text" },
                { label: "Date", key: "date", type: "date" },
              ].map(f => (
                <div key={f.key} style={{ marginBottom: 14 }}>
                  <Label>{f.label}</Label>
                  <input type={f.type} value={form[f.key]} placeholder={f.placeholder || ""}
                    onChange={e => { const val = e.target.value; setForm(prev => ({ ...prev, [f.key]: val })); }}
                    style={{ width: "100%", background: "#0d1117", border: "1px solid #21262d", borderRadius: 8, padding: "10px 14px", color: "#e6edf3", fontSize: 13, outline: "none", boxSizing: "border-box" }} />
                </div>
              ))}
              <div onClick={saveEntry} style={{ background: "linear-gradient(135deg,#00d4aa,#4a9eff)", borderRadius: 8, padding: "12px", textAlign: "center", fontWeight: 700, fontSize: 13, color: "#0d1117", cursor: "pointer", opacity: saving ? 0.7 : 1 }}>
                {saving ? "Saving..." : "Save Entry"}
              </div>
            </Card>
            <Card>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 14 }}>All Transactions</div>
              <div style={{ maxHeight: 480, overflowY: "auto" }}>
                {transactions.map((t, i) => (
                  <div key={t.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "9px 0", borderBottom: "1px solid #21262d" }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12 }}>{t.description}</div>
                      <div style={{ fontSize: 11, color: "#484f58" }}>{t.date} · {t.category || t.type}</div>
                    </div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: t.type === "sales" ? "#00d4aa" : "#ff4444", marginRight: 10 }}>
                      {t.type === "sales" ? "+" : "-"}{fmt(t.amount)}
                    </div>
                    <div onClick={() => {
                      if (window.confirm("Delete this transaction?")) {
                        api(`/transactions/${t.id}`, { method: "DELETE" }).then(() => loadAll(true));
                      }
                    }}
                      style={{ color: "#484f58", cursor: "pointer", fontSize: 13, padding: "4px 8px", borderRadius: 4, transition: "all 0.2s" }}
                      onMouseEnter={e => { e.target.style.color = "#ff4444"; e.target.style.background = "rgba(255,68,68,0.1)"; }}
                      onMouseLeave={e => { e.target.style.color = "#484f58"; e.target.style.background = "transparent"; }}>✕</div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}

        {/* MARKET TRENDS */}
        {nav === "Market Trends" && (
          <Card>
            <div style={{ fontSize: 12, color: "#484f58", marginBottom: 16 }}>Live global commodity prices · Auto-converted to NGN</div>
            {trends.length === 0 && <div style={{ color: "#484f58", textAlign: "center", padding: 30 }}>Configure API keys in market_service.py to see live prices.</div>}
            {trends.map((m, i) => (
              <div key={i} style={{ background: "#0d1117", borderRadius: 10, padding: "14px 18px", marginBottom: 10, display: "flex", alignItems: "center", gap: 14, border: "1px solid #21262d" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{m.item}</div>
                  <div style={{ fontSize: 11, color: "#00d4aa", marginTop: 3 }}>💡 {m.advice}</div>
                  {m.supplier && (
                    <div style={{ fontSize: 11, color: "#8b949e", marginTop: 4, display: "flex", alignItems: "center", gap: 6 }}>
                      <span>📍 Where to buy:</span>
                      <span style={{ color: "#4a9eff", fontWeight: 600 }}>{m.supplier}</span>
                    </div>
                  )}
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{fmt(m.price_ngn)}</div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: m.trend > 0 ? "#ff4444" : "#00d4aa" }}>
                    {m.trend > 0 ? "+" : ""}{m.trend}%
                  </div>
                </div>
                <div style={{ fontSize: 26 }}>{m.trend > 0 ? "📈" : "📉"}</div>
              </div>
            ))}
          </Card>
        )}

        {/* REPORTS */}
        {nav === "Reports" && (
          <div>
            <div className="grid-mobile-stack" style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 14, marginBottom: 16 }}>
              {[
                { label: "Monthly Revenue", value: fmt(summary.monthly_revenue), color: "#00d4aa" },
                { label: "Net Profit", value: fmt(summary.net_profit), color: summary.net_profit > 0 ? "#00d4aa" : "#ff4444" },
                { label: "Profit Margin", value: `${summary.profit_margin || 0}%`, color: "#4a9eff" },
              ].map((r, i) => (
                <Card key={i}><Label>{r.label}</Label><div style={{ fontSize: 24, fontWeight: 800, color: r.color }}>{r.value}</div></Card>
              ))}
            </div>
            <Card>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 18 }}>Revenue vs Expenses — Last 7 Days</div>
              {[...byDay].reverse().map((day, i) => {
                const maxVal = Math.max(...byDay.map(d => Math.max(d.revenue || 0, d.expenses || 0)), 1);
                return (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
                    <div style={{ width: 68, fontSize: 11, color: "#484f58" }}>{day.date?.slice(5)}</div>
                    <div style={{ flex: 1 }}>
                      <ScoreBar score={day.revenue || 0} max={maxVal} color="#00d4aa" />
                      <div style={{ marginTop: 4 }}><ScoreBar score={day.expenses || 0} max={maxVal} color="#ff444480" /></div>
                    </div>
                    <div style={{ fontSize: 11, color: "#8b949e", width: 130, textAlign: "right" }}>+{fmt(day.revenue)} / -{fmt(day.expenses)}</div>
                  </div>
                );
              })}
            </Card>
          </div>
        )}

        {/* SETTINGS */}
        {nav === "Settings" && (
          <div className="grid-mobile-stack" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, maxWidth: 800 }}>
            <Card>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 18 }}>Business Profile</div>
              {[
                { label: "Full Name", key: "full_name" },
                { label: "Business Name", key: "business_name" },
                { label: "Location", key: "location" },
                { label: "Currency", key: "currency" },
                { label: "AI Brain Key (Groq)", key: "ai_api_key" },
              ].map((f, i) => (
                <div key={i} style={{ marginBottom: 14 }}>
                  <Label>{f.label}</Label>
                  <input value={user[f.key] || ""} onChange={e => setUser({ ...user, [f.key]: e.target.value })}
                    style={{ width: "100%", background: "#0d1117", border: "1px solid #30363d", borderRadius: 8, padding: "10px 14px", color: "#e6edf3", fontSize: 13, outline: "none", boxSizing: "border-box" }} />
                </div>
              ))}
              <div onClick={saveProfile} style={{ background: "linear-gradient(135deg,#00d4aa,#4a9eff)", borderRadius: 8, padding: "11px", textAlign: "center", fontWeight: 700, fontSize: 13, color: "#0d1117", cursor: "pointer" }}>
                Save Profile
              </div>
            </Card>
            <Card>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 18 }}>Change Password</div>
              {[
                { label: "Current Password", key: "current_password" },
                { label: "New Password", key: "new_password" },
              ].map((f, i) => (
                <div key={i} style={{ marginBottom: 14 }}>
                  <Label>{f.label}</Label>
                  <input type="password" value={pwForm[f.key]} onChange={e => setPwForm({ ...pwForm, [f.key]: e.target.value })}
                    style={{ width: "100%", background: "#0d1117", border: "1px solid #30363d", borderRadius: 8, padding: "10px 14px", color: "#e6edf3", fontSize: 13, outline: "none", boxSizing: "border-box" }} />
                </div>
              ))}
              <div onClick={changePassword} style={{ background: "#21262d", border: "1px solid #30363d", borderRadius: 8, padding: "11px", textAlign: "center", fontWeight: 700, fontSize: 13, color: "#8b949e", cursor: "pointer" }}>
                Change Password
              </div>
              <div style={{ marginTop: 24, paddingTop: 24, borderTop: "1px solid #21262d" }}>
                <div style={{ fontSize: 12, color: "#484f58", marginBottom: 8 }}>Account</div>
                <div style={{ fontSize: 12, color: "#8b949e" }}>Email: {user.email}</div>
                <div style={{ fontSize: 12, color: "#8b949e", marginTop: 4 }}>Plan: <span style={{ color: "#00d4aa", textTransform: "capitalize" }}>{user.plan || "free"}</span></div>
              </div>
            </Card>
          </div>
        )}
      </div>
      <BizIQChatbot
        token={token}
        businessData={{
          owner: user?.full_name || "",
          name: user?.business_name || "",
          revenue: summary?.monthly_revenue || 0,
          profit: summary?.net_profit || 0,
          health: health?.total_score || 0
        }}
      />
    </div>
  );
}

// ──────────────────────────────────────────────
// ROOT — decides what to show
// ──────────────────────────────────────────────

export default function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);

  useEffect(() => {
    // Check if already logged in
    const savedToken = localStorage.getItem("biziq_token");
    const savedUser = localStorage.getItem("biziq_user");
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
    }
  }, []);

  const handleAuth = (u, t) => { setUser(u); setToken(t); };
  const handleLogout = () => { setUser(null); setToken(null); };

  if (!user) return <AuthScreen onAuth={handleAuth} />;
  return <MainApp user={user} token={token} onLogout={handleLogout} />;
}
