import { useEffect, useState, useCallback } from 'react';
import { useAuth } from './useAuth';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ── Types ─────────────────────────────────────────────────────
export type PlanName = 'free' | 'pro' | 'business';

export interface Plan {
    id: string;
    name: string;
    amount: number;
    paystack_plan_code?: string;
    features: string[];
}

export interface Subscription {
    status: 'pending' | 'active' | 'non_renewing' | 'attention' | 'completed' | 'cancelled';
    plan: string;
    plan_id: string;
    current_period_end: string | null;
    cancel_at_period_end: boolean;
    paystack_subscription_code?: string;
    paystack_email_token?: string;
}

interface UseSubscriptionReturn {
    subscription: Subscription | null;
    plans: Plan[];
    planName: PlanName;
    isActive: boolean;
    isPro: boolean;
    isBusiness: boolean;
    daysRemaining: number | null;
    isLoading: boolean;
    error: string | null;
    initiateCheckout: (planId: string) => Promise<void>;
    cancelSubscription: () => Promise<void>;
    manageSubscription: () => void;
    refresh: () => Promise<void>;
}

// ── Hook ──────────────────────────────────────────────────────
export function useSubscription(): UseSubscriptionReturn {
    const { user, token } = useAuth();

    const [subscription, setSubscription] = useState<Subscription | null>(null);
    const [plans, setPlans] = useState<Plan[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // ── Fetch subscription + plans ──────────────────────────────
    const fetchData = useCallback(async () => {
        if (!user || !token) {
            setSubscription(null);
            setIsLoading(false);
            return;
        }
        setIsLoading(true);
        setError(null);

        try {
            const [plansRes, subRes] = await Promise.all([
                fetch(`${API}/api/plans`),
                fetch(`${API}/api/subscription`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                })
            ]);

            if (!plansRes.ok || !subRes.ok) throw new Error('Failed to fetch data');

            const plansData = await plansRes.json();
            const subData = await subRes.json();

            setPlans(plansData);
            if (subData.status !== 'none') {
                setSubscription(subData);
            } else {
                setSubscription(null);
            }
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'Failed to load subscription');
        } finally {
            setIsLoading(false);
        }
    }, [user, token]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    // ── Derived state ──────────────────────────────────────────
    const isActive = subscription?.status === 'active' || subscription?.status === 'non_renewing';
    const planName = derivePlanName(subscription, isActive);
    const isPro = isActive && planName === 'pro';
    const isBusiness = isActive && planName === 'business';

    const daysRemaining = (() => {
        if (!subscription?.current_period_end) return null;
        const diff = new Date(subscription.current_period_end).getTime() - Date.now();
        return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
    })();

    // ── Checkout: initialise via FastAPI ─────────
    const initiateCheckout = useCallback(async (planId: string) => {
        if (!user || !token) throw new Error('Not authenticated');

        const res = await fetch(`${API}/api/paystack/initialize`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ planId }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Failed to initialise checkout');
        }

        const data = await res.json();
        if (data.authorization_url) {
            window.location.href = data.authorization_url;
        } else {
            throw new Error('Payment service did not provide a redirect URL. Please try again.');
        }
    }, [user, token]);

    // ── Cancel subscription ────────────────────────────────────
    const cancelSubscription = useCallback(async () => {
        if (!subscription?.paystack_subscription_code || !subscription?.paystack_email_token) {
            throw new Error('No active subscription to cancel');
        }

        const res = await fetch(`${API}/api/paystack/cancel`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                subscriptionCode: subscription.paystack_subscription_code,
                emailToken: subscription.paystack_email_token,
            }),
        });

        if (!res.ok) throw new Error('Failed to cancel subscription');
        await fetchData();
    }, [subscription, token, fetchData]);

    // ── Manage subscription (Paystack hosted portal) ───────────
    const manageSubscription = useCallback(() => {
        if (!subscription?.paystack_subscription_code || !subscription?.paystack_email_token) return;
        const url = `https://paystack.com/manage/${subscription.paystack_subscription_code}/${subscription.paystack_email_token}`;
        window.open(url, '_blank', 'noopener,noreferrer');
    }, [subscription]);

    return {
        subscription,
        plans,
        planName,
        isActive,
        isPro,
        isBusiness,
        daysRemaining,
        isLoading,
        error,
        initiateCheckout,
        cancelSubscription,
        manageSubscription,
        refresh: fetchData,
    };
}

// ── Helper ────────────────────────────────────────────────────
function derivePlanName(sub: Subscription | null, isActive: boolean): PlanName {
    if (!sub || !isActive) return 'free';
    const name = sub.plan?.toLowerCase() ?? '';
    if (name.includes('business')) return 'business';
    if (name.includes('pro')) return 'pro';
    return 'free';
}
