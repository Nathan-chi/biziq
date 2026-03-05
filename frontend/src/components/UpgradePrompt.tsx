import { useSubscription, type PlanName } from '../hooks/useSubscription';

interface UpgradePromptProps {
    /** The feature name shown in the lock message */
    feature: string;
    /** Minimum plan required: "pro" | "business" */
    requiredPlan?: PlanName;
    /** Content to render when the user has access */
    children: React.ReactNode;
    /** Optional: override the default lock card with your own UI */
    fallback?: React.ReactNode;
}

const PLAN_LABELS: Record<PlanName, string> = {
    free: 'Free',
    pro: 'Pro',
    business: 'Business',
};

export default function UpgradePrompt({
    feature,
    requiredPlan = 'pro',
    children,
    fallback,
}: UpgradePromptProps) {
    const { planName, isPro, isBusiness } = useSubscription();

    const hasAccess =
        (requiredPlan === 'pro' && (isPro || isBusiness)) ||
        (requiredPlan === 'business' && isBusiness) ||
        requiredPlan === 'free';

    if (hasAccess) return <>{children}</>;

    if (fallback) return <>{fallback}</>;

    return (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center">
            {/* Lock icon */}
            <div className="w-12 h-12 rounded-full bg-white border border-slate-200 shadow-sm flex items-center justify-center mx-auto mb-4">
                <svg className="w-5 h-5 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0110 0v4" />
                </svg>
            </div>

            <h3 className="text-base font-semibold text-slate-800 mb-1">
                {feature} is a {PLAN_LABELS[requiredPlan]} feature
            </h3>
            <p className="text-sm text-slate-500 mb-5 max-w-xs mx-auto">
                You're on the <span className="font-medium">{PLAN_LABELS[planName]}</span> plan.
                Upgrade to unlock {feature} and {requiredPlan === 'pro' ? '10+' : '5+'} more features.
            </p>

            <a
                href="/billing"
                className="inline-flex items-center gap-2 bg-blue-600 text-white text-sm font-semibold px-5 py-2.5 rounded-xl hover:bg-blue-700 transition-colors shadow-sm shadow-blue-200"
            >
                Upgrade to {PLAN_LABELS[requiredPlan]}
                <svg className="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
            </a>

            <p className="text-xs text-slate-400 mt-3">Cancel anytime · No lock-in</p>
        </div>
    );
}
