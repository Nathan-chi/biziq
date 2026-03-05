import { useState } from 'react';
import { useSubscription } from '../hooks/useSubscription';

// ── Helpers ─────────────────────────────────────────────────────
const fmt = (naira: number) =>
    new Intl.NumberFormat('en-NG', { style: 'currency', currency: 'NGN', maximumFractionDigits: 0 }).format(naira);

function fmtDate(iso: string | null) {
    if (!iso) return '—';
    return new Date(iso).toLocaleDateString('en-NG', { day: 'numeric', month: 'long', year: 'numeric' });
}

const STATUS_META: Record<string, { color: string; label: string }> = {
    active: { color: '#00d4aa', label: 'Active' },
    non_renewing: { color: '#f59e0b', label: 'Cancels soon' },
    attention: { color: '#ef4444', label: 'Payment issue' },
    pending: { color: '#8b949e', label: 'Pending' },
    cancelled: { color: '#484f58', label: 'Cancelled' },
    completed: { color: '#484f58', label: 'Expired' },
};

// ── Sub-components ──────────────────────────────────────────────
function StatusPill({ status }: { status: string }) {
    const m = STATUS_META[status] ?? STATUS_META.cancelled;
    return (
        <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '3px 10px', borderRadius: 999, fontSize: 11, fontWeight: 700,
            background: `${m.color}18`, color: m.color, border: `1px solid ${m.color}40`,
        }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: m.color }} />
            {m.label}
        </span>
    );
}

function CheckIcon({ color = '#00d4aa' }: { color?: string }) {
    return (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0, marginTop: 1 }}>
            <circle cx="8" cy="8" r="7" fill={`${color}22`} />
            <path d="M5 8l2 2 4-4" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    );
}

function Feature({ text, included = true }: { text: string; included?: boolean }) {
    return (
        <li style={{
            display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: 13,
            color: included ? '#c9d1d9' : '#484f58',
            textDecoration: included ? 'none' : 'line-through',
        }}>
            {included
                ? <CheckIcon />
                : <span style={{ width: 16, height: 16, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#484f58', marginTop: 1 }}>✕</span>
            }
            {text}
        </li>
    );
}

function CancelModal({ onConfirm, onClose, isCancelling }: {
    onConfirm: () => void;
    onClose: () => void;
    isCancelling: boolean;
}) {
    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 100,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(6px)', padding: 16,
        }}>
            <div style={{
                background: '#161b22', border: '1px solid #30363d', borderRadius: 20,
                padding: 36, maxWidth: 380, width: '100%', textAlign: 'center',
            }}>
                <div style={{
                    width: 52, height: 52, borderRadius: '50%', background: 'rgba(239,68,68,0.12)',
                    border: '1px solid rgba(239,68,68,0.3)', display: 'flex', alignItems: 'center',
                    justifyContent: 'center', margin: '0 auto 16px',
                }}>
                    <span style={{ fontSize: 24 }}>⚠️</span>
                </div>
                <div style={{ fontSize: 17, fontWeight: 700, color: '#e6edf3', marginBottom: 8 }}>
                    Cancel subscription?
                </div>
                <div style={{ fontSize: 13, color: '#8b949e', marginBottom: 24, lineHeight: 1.6 }}>
                    You'll keep access until the end of your billing period. You can resubscribe anytime.
                </div>
                <div style={{ display: 'flex', gap: 10 }}>
                    <button
                        onClick={onClose}
                        disabled={isCancelling}
                        style={{
                            flex: 1, padding: '11px', borderRadius: 10, border: '1px solid #30363d',
                            background: 'transparent', color: '#8b949e', fontSize: 13, fontWeight: 600,
                            cursor: 'pointer',
                        }}
                    >
                        Keep plan
                    </button>
                    <button
                        onClick={onConfirm}
                        disabled={isCancelling}
                        style={{
                            flex: 1, padding: '11px', borderRadius: 10, border: 'none',
                            background: 'rgba(239,68,68,0.15)', color: '#ef4444',
                            fontSize: 13, fontWeight: 700, cursor: 'pointer',
                        }}
                    >
                        {isCancelling ? 'Cancelling…' : 'Yes, cancel'}
                    </button>
                </div>
            </div>
        </div>
    );
}

// ── Main Page ───────────────────────────────────────────────────
export default function Billing() {
    const {
        subscription, plans, planName, isActive, daysRemaining,
        isLoading, error,
        initiateCheckout, cancelSubscription, manageSubscription,
    } = useSubscription();

    const [checkingOut, setCheckingOut] = useState<string | null>(null);
    const [checkoutError, setCheckoutError] = useState<string | null>(null);
    const [showCancelModal, setShowCancelModal] = useState(false);
    const [isCancelling, setIsCancelling] = useState(false);
    const [cancelSuccess, setCancelSuccess] = useState(false);

    async function handleCheckout(planId: string) {
        setCheckingOut(planId);
        setCheckoutError(null);
        try {
            await initiateCheckout(planId);
        } catch (err: unknown) {
            setCheckoutError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
        } finally {
            setCheckingOut(null);
        }
    }

    async function handleCancel() {
        setIsCancelling(true);
        try {
            await cancelSubscription();
            setShowCancelModal(false);
            setCancelSuccess(true);
        } catch {
            setShowCancelModal(false);
        } finally {
            setIsCancelling(false);
        }
    }

    if (isLoading) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
                <div style={{ textAlign: 'center' }}>
                    <div style={{
                        width: 36, height: 36, border: '3px solid #30363d',
                        borderTopColor: '#00d4aa', borderRadius: '50%',
                        animation: 'spin 1s linear infinite', margin: '0 auto 12px',
                    }} />
                    <div style={{ color: '#8b949e', fontSize: 13 }}>Loading billing…</div>
                </div>
            </div>
        );
    }

    return (
        <div style={{ padding: '0 0 40px' }}>
            {showCancelModal && (
                <CancelModal onConfirm={handleCancel} onClose={() => setShowCancelModal(false)} isCancelling={isCancelling} />
            )}

            {/* ── Header ── */}
            <div style={{ marginBottom: 28 }}>
                <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.5, color: '#00d4aa', textTransform: 'uppercase', marginBottom: 6 }}>
                    💳 Billing & Plans
                </div>
                <h1 style={{ fontSize: 24, fontWeight: 800, color: '#e6edf3', margin: 0, letterSpacing: -0.5 }}>
                    Upgrade your plan
                </h1>
                <p style={{ fontSize: 13, color: '#8b949e', marginTop: 6 }}>
                    Unlock AI features, unlimited transactions, and powerful tools for your business.
                </p>
            </div>

            {/* ── Error banners ── */}
            {(error || checkoutError) && (
                <div style={{
                    background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)',
                    borderRadius: 10, padding: '12px 16px', marginBottom: 20, fontSize: 13, color: '#ef4444',
                    display: 'flex', alignItems: 'center', gap: 8,
                }}>
                    ⚠️ {error || checkoutError}
                </div>
            )}
            {cancelSuccess && (
                <div style={{
                    background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.25)',
                    borderRadius: 10, padding: '12px 16px', marginBottom: 20, fontSize: 13, color: '#f59e0b',
                    display: 'flex', alignItems: 'center', gap: 8,
                }}>
                    ✅ Subscription cancelled. You'll keep access until the end of your billing period.
                </div>
            )}

            {/* ── Active subscription card ── */}
            {isActive && subscription && (
                <div style={{
                    background: '#161b22', border: '1px solid #30363d', borderRadius: 14,
                    overflow: 'hidden', marginBottom: 24,
                }}>
                    <div style={{ height: 3, background: 'linear-gradient(90deg,#00d4aa,#4a9eff)' }} />
                    <div style={{
                        padding: '18px 20px', display: 'flex',
                        alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12,
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                            <div style={{
                                width: 44, height: 44, borderRadius: 10,
                                background: 'rgba(0,212,170,0.1)', border: '1px solid rgba(0,212,170,0.2)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20,
                            }}>
                                ⚡
                            </div>
                            <div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                                    <span style={{ fontWeight: 700, fontSize: 15, color: '#e6edf3' }}>
                                        {subscription.plan} Plan
                                    </span>
                                    <StatusPill status={subscription.status} />
                                </div>
                                <div style={{ fontSize: 12, color: '#8b949e' }}>
                                    {subscription.current_period_end && (
                                        <span>Renews {fmtDate(subscription.current_period_end)}</span>
                                    )}
                                    {daysRemaining !== null && daysRemaining <= 7 && (
                                        <span style={{ marginLeft: 8, color: '#f59e0b', fontWeight: 600 }}>
                                            · {daysRemaining} day{daysRemaining !== 1 ? 's' : ''} left
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                        <div style={{ display: 'flex', gap: 8 }}>
                            <button
                                onClick={manageSubscription}
                                style={{
                                    padding: '8px 16px', borderRadius: 8, border: '1px solid #30363d',
                                    background: 'transparent', color: '#8b949e', fontSize: 12, fontWeight: 600, cursor: 'pointer',
                                }}
                            >
                                Manage card
                            </button>
                            {subscription.status === 'active' && (
                                <button
                                    onClick={() => setShowCancelModal(true)}
                                    style={{
                                        padding: '8px 16px', borderRadius: 8,
                                        border: '1px solid rgba(239,68,68,0.3)',
                                        background: 'rgba(239,68,68,0.08)', color: '#ef4444',
                                        fontSize: 12, fontWeight: 600, cursor: 'pointer',
                                    }}
                                >
                                    Cancel
                                </button>
                            )}
                        </div>
                    </div>
                    {subscription.status === 'attention' && (
                        <div style={{
                            margin: '0 20px 16px', background: 'rgba(239,68,68,0.08)',
                            border: '1px solid rgba(239,68,68,0.25)', borderRadius: 10,
                            padding: '10px 14px', fontSize: 12, color: '#ef4444',
                        }}>
                            ⚠️ There was an issue with your last payment.{' '}
                            <button onClick={manageSubscription} style={{ background: 'none', border: 'none', color: '#ef4444', textDecoration: 'underline', cursor: 'pointer', fontSize: 12, fontWeight: 700, padding: 0 }}>
                                Update your card
                            </button>{' '}
                            to keep access.
                        </div>
                    )}
                </div>
            )}

            {/* ── Pricing grid ── */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                gap: 16,
            }}>
                {/* Free plan */}
                <PlanCard
                    title="Free"
                    price="₦0"
                    per="forever"
                    tagline="Perfect for getting started."
                    isCurrent={planName === 'free'}
                    isPopular={false}
                    features={[
                        'Up to 50 transactions/month',
                        'Basic dashboard & analytics',
                        'Inventory tracking',
                        { text: 'AI assistant (daily advice)', included: false },
                        { text: 'Live market data', included: false },
                        { text: 'Business health score', included: false },
                    ]}
                    buttonLabel={planName === 'free' ? 'Current plan' : 'Free forever'}
                    buttonDisabled
                />

                {/* Paid plans from backend */}
                {plans.map((plan) => {
                    const isCurrent = subscription?.plan_id === plan.id && isActive;
                    const isPopular = plan.name.toLowerCase() === 'pro';
                    const isLoadingThis = checkingOut === plan.id;

                    return (
                        <PlanCard
                            key={plan.id}
                            title={plan.name}
                            price={fmt(plan.amount)}
                            per="month"
                            tagline={plan.name === 'Pro' ? 'For serious business owners.' : 'For growing businesses.'}
                            isCurrent={isCurrent}
                            isPopular={isPopular}
                            features={plan.features}
                            buttonLabel={
                                isLoadingThis ? 'Redirecting…' :
                                    isCurrent ? 'Current plan' :
                                        `Upgrade to ${plan.name} →`
                            }
                            buttonDisabled={isCurrent || !!checkingOut}
                            buttonLoading={isLoadingThis}
                            onUpgrade={() => handleCheckout(plan.id)}
                        />
                    );
                })}

                {plans.length === 0 && !isLoading && (
                    <div style={{
                        gridColumn: '1 / -1',
                        background: '#161b22', border: '1px dashed #30363d',
                        borderRadius: 14, padding: 32, textAlign: 'center',
                        color: '#484f58', fontSize: 13,
                    }}>
                        No plans available — check that the backend is running.
                    </div>
                )}
            </div>

            {/* ── Reassurance strip ── */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginTop: 24 }}>
                {[
                    { icon: '🔒', title: 'Secure payments', body: "All payments processed by Paystack — Nigeria's most trusted payment processor." },
                    { icon: '↩️', title: 'Cancel anytime', body: 'No lock-in. Cancel with one click and keep access until end of billing cycle.' },
                    { icon: '💬', title: 'Local support', body: "Questions? We're based in Nigeria and respond fast." },
                ].map((item) => (
                    <div key={item.title} style={{
                        background: '#161b22', border: '1px solid #21262d',
                        borderRadius: 12, padding: '14px 16px',
                        display: 'flex', gap: 12, alignItems: 'flex-start',
                    }}>
                        <span style={{ fontSize: 20 }}>{item.icon}</span>
                        <div>
                            <div style={{ fontSize: 13, fontWeight: 700, color: '#e6edf3', marginBottom: 4 }}>{item.title}</div>
                            <div style={{ fontSize: 12, color: '#8b949e', lineHeight: 1.5 }}>{item.body}</div>
                        </div>
                    </div>
                ))}
            </div>

            <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
    );
}

// ── Plan card sub-component ─────────────────────────────────────
type FeatureItem = string | { text: string; included: boolean };

function PlanCard({
    title, price, per, tagline, isCurrent, isPopular,
    features, buttonLabel, buttonDisabled, buttonLoading, onUpgrade,
}: {
    title: string;
    price: string;
    per: string;
    tagline: string;
    isCurrent: boolean;
    isPopular: boolean;
    features: FeatureItem[];
    buttonLabel: string;
    buttonDisabled?: boolean;
    buttonLoading?: boolean;
    onUpgrade?: () => void;
}) {
    const [hovered, setHovered] = useState(false);

    const borderColor = isPopular
        ? '#00d4aa'
        : isCurrent ? '#4a9eff40' : hovered ? '#30363d' : '#21262d';

    return (
        <div style={{
            background: '#161b22',
            border: `1px solid ${borderColor}`,
            borderRadius: 16,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            transition: 'border-color 0.2s, transform 0.2s',
            transform: hovered && !buttonDisabled ? 'translateY(-2px)' : 'none',
            boxShadow: isPopular ? '0 0 0 1px #00d4aa20, 0 8px 24px rgba(0,212,170,0.08)' : 'none',
        }}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
        >
            {/* Top accent */}
            {isPopular && (
                <div style={{ height: 3, background: 'linear-gradient(90deg,#00d4aa,#4a9eff)' }} />
            )}

            <div style={{ padding: '20px 20px 0' }}>
                {/* Popular badge */}
                {isPopular && (
                    <span style={{
                        display: 'inline-block', background: 'linear-gradient(135deg,#00d4aa,#4a9eff)',
                        color: '#0d1117', fontSize: 10, fontWeight: 800, letterSpacing: 0.8,
                        textTransform: 'uppercase', padding: '3px 10px', borderRadius: 999, marginBottom: 12,
                    }}>
                        ⭐ Most Popular
                    </span>
                )}
                {isCurrent && !isPopular && (
                    <span style={{
                        display: 'inline-block', background: 'rgba(74,158,255,0.1)',
                        border: '1px solid rgba(74,158,255,0.3)',
                        color: '#4a9eff', fontSize: 10, fontWeight: 700, letterSpacing: 0.5,
                        padding: '3px 10px', borderRadius: 999, marginBottom: 12,
                    }}>
                        ✓ Current plan
                    </span>
                )}

                <div style={{ fontSize: 17, fontWeight: 800, color: '#e6edf3', marginBottom: 6 }}>{title}</div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginBottom: 4 }}>
                    <span style={{ fontSize: 30, fontWeight: 900, letterSpacing: -1, color: '#e6edf3' }}>{price}</span>
                    <span style={{ fontSize: 12, color: '#484f58' }}>/{per}</span>
                </div>
                <div style={{ fontSize: 12, color: '#8b949e', marginBottom: 16 }}>{tagline}</div>
            </div>

            {/* Divider */}
            <div style={{ height: 1, background: '#21262d', margin: '0 20px' }} />

            {/* Features */}
            <ul style={{ padding: '16px 20px', margin: 0, listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
                {features.map((f, i) => {
                    if (typeof f === 'string') return <Feature key={i} text={f} />;
                    return <Feature key={i} text={f.text} included={f.included} />;
                })}
            </ul>

            {/* CTA */}
            <div style={{ padding: '12px 20px 20px' }}>
                <button
                    onClick={onUpgrade}
                    disabled={buttonDisabled}
                    style={{
                        width: '100%', padding: '12px', borderRadius: 10,
                        fontSize: 13, fontWeight: 700, cursor: buttonDisabled ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s',
                        background: buttonDisabled
                            ? '#21262d'
                            : isPopular
                                ? 'linear-gradient(135deg,#00d4aa,#4a9eff)'
                                : '#0d1117',
                        color: buttonDisabled
                            ? '#484f58'
                            : isPopular ? '#0d1117' : '#e6edf3',
                        border: buttonDisabled ? 'none' : isPopular ? 'none' : '1px solid #30363d',
                        opacity: buttonLoading ? 0.7 : 1,
                    }}
                >
                    {buttonLoading ? (
                        <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                            <span style={{
                                width: 14, height: 14, border: '2px solid rgba(13,17,23,0.3)',
                                borderTopColor: '#0d1117', borderRadius: '50%',
                                animation: 'spin 1s linear infinite', display: 'inline-block',
                            }} />
                            Redirecting…
                        </span>
                    ) : buttonLabel}
                </button>
            </div>
        </div>
    );
}
