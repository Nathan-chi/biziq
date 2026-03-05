import { useSubscription } from '../hooks/useSubscription';

export default function BillingNavBadge() {
    const { planName, isActive, subscription, daysRemaining } = useSubscription();

    // Payment failed
    if (subscription?.status === 'attention') {
        return (
            <span style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                width: 18, height: 18, borderRadius: '50%', background: '#ef4444',
                color: '#fff', fontSize: 10, fontWeight: 800,
            }}>!</span>
        );
    }

    // Cancelling soon ≤ 7 days
    if (subscription?.status === 'non_renewing' && daysRemaining !== null && daysRemaining <= 7) {
        return (
            <span style={{
                background: 'rgba(245,158,11,0.12)', color: '#f59e0b',
                fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 999,
            }}>
                {daysRemaining}d left
            </span>
        );
    }

    // Active paid plan
    if (isActive && planName !== 'free') {
        return (
            <span style={{
                background: 'rgba(0,212,170,0.12)', color: '#00d4aa',
                fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 999,
                textTransform: 'capitalize',
            }}>
                {planName}
            </span>
        );
    }

    // Free tier
    return (
        <span style={{
            background: 'linear-gradient(135deg,rgba(0,212,170,0.15),rgba(74,158,255,0.15))',
            color: '#4a9eff', fontSize: 10, fontWeight: 800, padding: '2px 7px', borderRadius: 999,
        }}>
            Upgrade
        </span>
    );
}
