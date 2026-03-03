import { useState, useRef, useEffect } from "react";

const QUICK_QUESTIONS = [
    "How is my business doing?",
    "What does profit margin mean?",
    "Should I buy more sugar now?",
    "Explain my expenses simply",
    "What should I do this week?",
    "Why are my costs so high?",
];

export default function BizIQChatbot({ businessData, token }) {
    const [messages, setMessages] = useState([
        {
            role: "assistant",
            content: `👋 Hey ${businessData.owner || "there"}! I'm your BizIQ assistant.\n\nI can explain your business numbers in simple language — no big grammar! Just ask me anything about your money, sales, expenses, or what the market is doing.\n\nWhat would you like to know? 😊`,
        },
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [isOpen, setIsOpen] = useState(false);
    const bottomRef = useRef(null);
    const inputRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    const send = async (text) => {
        const q = (text || input).trim();
        if (!q || loading) return;
        setInput("");

        const newMessages = [...messages, { role: "user", content: q }];
        setMessages(newMessages);
        setLoading(true);

        try {
            const apiBase = import.meta.env.VITE_API_URL || "http://localhost:8000";
            const response = await fetch(`${apiBase}/chat/message`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    messages: newMessages.map(m => ({ role: m.role, content: m.content }))
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "API error");
            }

            if (data.reply) {
                setMessages([...newMessages, { role: "assistant", content: data.reply }]);
            } else {
                throw new Error("Empty response from AI");
            }
        } catch (e) {
            console.error("Chatbot Error:", e);
            setMessages([...newMessages, {
                role: "assistant",
                content: `⚠️ Error: ${e.message}. Please check if the backend is running and your Groq API key is correct.`,
            }]);
        }
        setLoading(false);
        setTimeout(() => inputRef.current?.focus(), 100);
    };

    const handleKey = (e) => {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
    };

    if (!isOpen) {
        return (
            <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 999 }}>
                <div onClick={() => setIsOpen(true)} style={{
                    width: 60, height: 60, borderRadius: "50%", cursor: "pointer",
                    background: "linear-gradient(135deg,#00d4aa,#4a9eff)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 26, boxShadow: "0 4px 24px rgba(0,212,170,0.4)",
                    transition: "transform 0.2s",
                }}
                    onMouseOver={e => e.currentTarget.style.transform = "scale(1.1)"}
                    onMouseOut={e => e.currentTarget.style.transform = "scale(1)"}
                >🤖</div>
            </div>
        );
    }

    return (
        <div style={{
            fontFamily: "'DM Sans','Segoe UI',sans-serif",
            position: "fixed", bottom: 24, right: 24,
            width: 380, height: 580,
            background: "#161b22",
            border: "1px solid #21262d",
            borderRadius: 20,
            display: "flex", flexDirection: "column",
            boxShadow: "0 20px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(0,212,170,0.1)",
            zIndex: 999,
            overflow: "hidden",
        }}>

            {/* Header */}
            <div style={{
                padding: "16px 18px",
                background: "linear-gradient(135deg, rgba(0,212,170,0.12), rgba(74,158,255,0.08))",
                borderBottom: "1px solid #21262d",
                display: "flex", alignItems: "center", justifyContent: "space-between",
            }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{
                        width: 38, height: 38, borderRadius: "50%",
                        background: "linear-gradient(135deg,#00d4aa,#4a9eff)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 18,
                    }}>🤖</div>
                    <div>
                        <div style={{ fontSize: 14, fontWeight: 700, color: "#e6edf3" }}>BizIQ Assistant</div>
                        <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 1 }}>
                            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#00d4aa" }} />
                            <div style={{ fontSize: 11, color: "#00d4aa" }}>Powered by Groq · Llama 3.3</div>
                        </div>
                    </div>
                </div>
                <div onClick={() => setIsOpen(false)} style={{ cursor: "pointer", color: "#484f58", fontSize: 18, padding: "4px 8px", borderRadius: 6, transition: "all 0.15s" }}
                    onMouseOver={e => { e.currentTarget.style.background = "#21262d"; e.currentTarget.style.color = "#8b949e"; }}
                    onMouseOut={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "#484f58"; }}
                >✕</div>
            </div>

            {/* Business snapshot bar */}
            <div style={{
                display: "flex", gap: 0,
                borderBottom: "1px solid #21262d",
                background: "#0d1117",
            }}>
                {[
                    { label: "Revenue", value: `₦${(businessData.revenue || 0).toLocaleString()}`, color: "#00d4aa" },
                    { label: "Profit", value: `₦${(businessData.profit || 0).toLocaleString()}`, color: "#4a9eff" },
                    { label: "Health", value: `${businessData.health || 0}/100`, color: "#f5a623" },
                ].map((s, i) => (
                    <div key={i} style={{ flex: 1, padding: "8px 10px", textAlign: "center", borderRight: i < 2 ? "1px solid #21262d" : "none" }}>
                        <div style={{ fontSize: 10, color: "#484f58", textTransform: "uppercase", letterSpacing: 0.5 }}>{s.label}</div>
                        <div style={{ fontSize: 13, fontWeight: 700, color: s.color, marginTop: 1 }}>{s.value}</div>
                    </div>
                ))}
            </div>

            {/* Messages */}
            <div style={{ flex: 1, overflowY: "auto", padding: "14px 14px 6px", display: "flex", flexDirection: "column", gap: 10 }}>
                {messages.map((m, i) => (
                    <div key={i} style={{
                        display: "flex",
                        flexDirection: m.role === "user" ? "row-reverse" : "row",
                        alignItems: "flex-end", gap: 8,
                    }}>
                        {m.role === "assistant" && (
                            <div style={{ width: 28, height: 28, borderRadius: "50%", background: "linear-gradient(135deg,#00d4aa,#4a9eff)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, flexShrink: 0 }}>🤖</div>
                        )}
                        <div style={{
                            maxWidth: "78%",
                            background: m.role === "user"
                                ? "linear-gradient(135deg,#00d4aa,#4a9eff)"
                                : "#21262d",
                            color: m.role === "user" ? "#0d1117" : "#e6edf3",
                            borderRadius: m.role === "user" ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
                            padding: "10px 14px",
                            fontSize: 13,
                            lineHeight: 1.55,
                            whiteSpace: "pre-wrap",
                            fontWeight: m.role === "user" ? 600 : 400,
                        }}>
                            {m.content}
                        </div>
                    </div>
                ))}

                {/* Typing indicator */}
                {loading && (
                    <div style={{ display: "flex", alignItems: "flex-end", gap: 8 }}>
                        <div style={{ width: 28, height: 28, borderRadius: "50%", background: "linear-gradient(135deg,#00d4aa,#4a9eff)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13 }}>🤖</div>
                        <div style={{ background: "#21262d", borderRadius: "18px 18px 18px 4px", padding: "12px 16px", display: "flex", gap: 4, alignItems: "center" }}>
                            {[0, 1, 2].map(i => (
                                <div key={i} style={{
                                    width: 7, height: 7, borderRadius: "50%", background: "#00d4aa",
                                    animation: "bounce 1.2s ease-in-out infinite",
                                    animationDelay: `${i * 0.2}s`,
                                }} />
                            ))}
                        </div>
                    </div>
                )}
                <div ref={bottomRef} />
            </div>

            {/* Quick questions */}
            {messages.length <= 2 && !loading && (
                <div style={{ padding: "6px 14px", display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {QUICK_QUESTIONS.map((q, i) => (
                        <div key={i} onClick={() => send(q)} style={{
                            background: "#0d1117", border: "1px solid #30363d",
                            borderRadius: 20, padding: "5px 11px", fontSize: 11, color: "#8b949e",
                            cursor: "pointer", transition: "all 0.15s",
                        }}
                            onMouseOver={e => { e.currentTarget.style.borderColor = "#00d4aa"; e.currentTarget.style.color = "#00d4aa"; }}
                            onMouseOut={e => { e.currentTarget.style.borderColor = "#30363d"; e.currentTarget.style.color = "#8b949e"; }}
                        >{q}</div>
                    ))}
                </div>
            )}

            {/* Input */}
            <div style={{ padding: "10px 14px 14px", borderTop: "1px solid #21262d" }}>
                <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
                    <textarea
                        ref={inputRef}
                        rows={1}
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={handleKey}
                        placeholder="Ask about your business..."
                        style={{
                            flex: 1, background: "#0d1117", border: "1px solid #30363d",
                            borderRadius: 12, padding: "10px 14px", color: "#e6edf3",
                            fontSize: 13, outline: "none", resize: "none",
                            fontFamily: "inherit", lineHeight: 1.4,
                            transition: "border 0.2s", maxHeight: 80, overflowY: "auto",
                        }}
                        onFocus={e => e.target.style.borderColor = "#00d4aa"}
                        onBlur={e => e.target.style.borderColor = "#30363d"}
                    />
                    <div onClick={() => send()} style={{
                        width: 40, height: 40, borderRadius: 12, flexShrink: 0,
                        background: input.trim() && !loading
                            ? "linear-gradient(135deg,#00d4aa,#4a9eff)"
                            : "#21262d",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        cursor: input.trim() && !loading ? "pointer" : "default",
                        transition: "all 0.2s", fontSize: 16,
                    }}>
                        {loading ? "⟳" : "↑"}
                    </div>
                </div>
                <div style={{ fontSize: 10, color: "#484f58", textAlign: "center", marginTop: 8 }}>
                    Powered by Groq · Llama 3.3 · Your data stays private
                </div>
            </div>

            <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-6px); }
        }
      `}</style>
        </div>
    );
}
