import { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useSubscription } from '../hooks/useSubscription';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const MAX_POLLS = 10;
const POLL_EVERY = 2000;

export default function BillingSuccess() {
    const navigate = useNavigate();
    const [params] = useSearchParams();
    const reference = params.get('reference') ?? params.get('trxref');

    const { subscription, refresh } = useSubscription();

    const [status, setStatus] = useState<'verifying' | 'activating' | 'done' | 'timeout'>('verifying');
    const [pollCount, setPollCount] = useState(0);
    const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

    // Step 1: verify reference
    useEffect(() => {
        if (!reference) { setStatus('activating'); return; }

        fetch(`${API}/api/paystack/verify?reference=${reference}`)
            .then(r => r.json())
            .then((data: { status: string }) => {
                setStatus(data.status === 'success' ? 'activating' : 'activating');
            })
            .catch(() => setStatus('activating'));
    }, [reference]);

    // Step 2: poll
    useEffect(() => {
        if (status !== 'activating') return;
        pollTimer.current = setInterval(async () => {
            await refresh();
            setPollCount(c => c + 1);
        }, POLL_EVERY);
        return () => { if (pollTimer.current) clearInterval(pollTimer.current); };
    }, [status, refresh]);

    // Step 3: watch
    useEffect(() => {
        if (status !== 'activating') return;
        if (subscription?.status === 'active') {
            setStatus('done');
            if (pollTimer.current) clearInterval(pollTimer.current);
            setTimeout(() => navigate('/dashboard'), 1800);
            return;
        }
        if (pollCount >= MAX_POLLS) {
            setStatus('timeout');
            if (pollTimer.current) clearInterval(pollTimer.current);
        }
    }, [subscription, pollCount, status, navigate]);

    const card: React.CSSProperties = {
        background: '#161b22', border: '1px solid #21262d', borderRadius: 20,
        padding: 40, maxWidth: 380, width: '100%', textAlign: 'center',
    };

    return (
        <div style={{
            minHeight: '100vh', background: '#0d1117',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontFamily: "'DM Sans','Segoe UI',sans-serif", padding: 16,
        }}>
            <div style={card}>

                {status === 'verifying' && (
                    <>
                        <Spinner color="#8b949e" />
                        <h1 style={h1}>Verifying payment…</h1>
                        <p style={sub}>Confirming your transaction with Paystack.</p>
                    </>
                )}

                {status === 'activating' && (
                    <>
                        <Spinner color="#4a9eff" />
                        <h1 style={h1}>Activating your plan…</h1>
                        <p style={sub}>Payment confirmed! Setting up your subscription. This usually takes a few seconds.</p>
                        <ProgressDots count={pollCount} max={MAX_POLLS} />
                    </>
                )}

                {status === 'done' && (
                    <>
                        <SuccessCircle />
                        <h1 style={{ ...h1, fontSize: 22 }}>You're all set! 🎉</h1>
                        <p style={sub}>Your plan is now active.</p>
                        <p style={{ fontSize: 12, color: '#484f58', marginTop: 8 }}>Redirecting to your dashboard…</p>
                    </>
                )}

                {status === 'timeout' && (
                    <>
                        <PendingCircle />
                        <h1 style={h1}>Almost there…</h1>
                        <p style={{ ...sub, marginBottom: 24 }}>
                            Your payment went through but the subscription is still activating. It usually completes within 2 minutes.
                        </p>
                        <button
                            onClick={() => navigate('/dashboard')}
                            style={{
                                width: '100%', padding: '12px', borderRadius: 10, border: 'none',
                                background: 'linear-gradient(135deg,#00d4aa,#4a9eff)',
                                color: '#0d1117', fontWeight: 700, fontSize: 14, cursor: 'pointer', marginBottom: 10,
                            }}
                        >
                            Go to dashboard
                        </button>
                        <button
                            onClick={() => { setPollCount(0); setStatus('activating'); }}
                            style={{
                                width: '100%', padding: '12px', borderRadius: 10,
                                border: '1px solid #30363d', background: 'transparent',
                                color: '#8b949e', fontWeight: 600, fontSize: 13, cursor: 'pointer',
                            }}
                        >
                            Check again
                        </button>
                    </>
                )}
            </div>
            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
    );
}

const h1: React.CSSProperties = { fontSize: 19, fontWeight: 800, color: '#e6edf3', margin: '16px 0 8px', letterSpacing: -0.3 };
const sub: React.CSSProperties = { fontSize: 13, color: '#8b949e', margin: 0, lineHeight: 1.6 };

function Spinner({ color }: { color: string }) {
    return (
        <div style={{ display: 'flex', justifyContent: 'center' }}>
            <div style={{
                width: 48, height: 48, borderRadius: '50%',
                border: `3px solid ${color}22`,
                borderTopColor: color,
                animation: 'spin 1s linear infinite',
            }} />
        </div>
    );
}

function SuccessCircle() {
    return (
        <div style={{ display: 'flex', justifyContent: 'center' }}>
            <div style={{
                width: 64, height: 64, borderRadius: '50%',
                background: 'rgba(0,212,170,0.12)', border: '1px solid rgba(0,212,170,0.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28,
            }}>✅</div>
        </div>
    );
}

function PendingCircle() {
    return (
        <div style={{ display: 'flex', justifyContent: 'center' }}>
            <div style={{
                width: 64, height: 64, borderRadius: '50%',
                background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28,
            }}>⏳</div>
        </div>
    );
}

function ProgressDots({ count, max }: { count: number; max: number }) {
    return (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 5, marginTop: 16 }}>
            {Array.from({ length: max }).map((_, i) => (
                <div key={i} style={{
                    height: 4, borderRadius: 2, transition: 'all 0.3s',
                    width: i < count ? 16 : 6,
                    background: i < count ? '#4a9eff' : '#21262d',
                }} />
            ))}
        </div>
    );
}
