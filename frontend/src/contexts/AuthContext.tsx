import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ── Types ──────────────────────────────────────────────────────
interface User {
    id: string | number;
    email: string;
    full_name: string;
    business_name: string;
    industry?: string;
    location?: string;
    currency?: string;
    plan?: string;
    ai_api_key?: string;
}

interface AuthState {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    error: string | null;
}

interface AuthContextValue extends AuthState {
    signIn: (form: { email: string; password: string }) => Promise<void>;
    signUp: (form: Record<string, string>) => Promise<void>;
    signOut: () => void;
    clearError: () => void;
}

// ── Context ────────────────────────────────────────────────────
const AuthContext = createContext<AuthContextValue | null>(null);

// ── Provider ───────────────────────────────────────────────────
export function AuthProvider({ children }: { children: ReactNode }) {
    const [state, setState] = useState<AuthState>({
        user: null,
        token: null,
        isLoading: true,
        error: null,
    });

    // Bootstrap from localStorage on mount
    useEffect(() => {
        const savedToken = localStorage.getItem('biziq_token');
        const savedUser = localStorage.getItem('biziq_user');
        if (savedToken && savedUser) {
            try {
                setState({
                    token: savedToken,
                    user: JSON.parse(savedUser),
                    isLoading: false,
                    error: null,
                });
            } catch {
                localStorage.removeItem('biziq_token');
                localStorage.removeItem('biziq_user');
                setState(s => ({ ...s, isLoading: false }));
            }
        } else {
            setState(s => ({ ...s, isLoading: false }));
        }
    }, []);

    const signIn = useCallback(async (form: { email: string; password: string }) => {
        setState(s => ({ ...s, isLoading: true, error: null }));
        try {
            const res = await fetch(`${API}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(form),
            });
            const data = await res.json();
            if (data.token) {
                localStorage.setItem('biziq_token', data.token);
                localStorage.setItem('biziq_user', JSON.stringify(data.user));
                // Update shared state — ALL components using useAuth will re-render
                setState({ user: data.user, token: data.token, isLoading: false, error: null });
            } else {
                setState(s => ({ ...s, isLoading: false, error: data.detail || 'Incorrect email or password' }));
            }
        } catch {
            setState(s => ({ ...s, isLoading: false, error: 'Cannot connect to server. Is the backend running?' }));
        }
    }, []);

    const signUp = useCallback(async (form: Record<string, string>) => {
        setState(s => ({ ...s, isLoading: true, error: null }));
        try {
            const res = await fetch(`${API}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(form),
            });
            const data = await res.json();
            if (data.token) {
                localStorage.setItem('biziq_token', data.token);
                localStorage.setItem('biziq_user', JSON.stringify(data.user));
                setState({ user: data.user, token: data.token, isLoading: false, error: null });
            } else {
                setState(s => ({ ...s, isLoading: false, error: data.detail || 'Registration failed' }));
            }
        } catch {
            setState(s => ({ ...s, isLoading: false, error: 'Cannot connect to server. Is the backend running?' }));
        }
    }, []);

    const signOut = useCallback(() => {
        localStorage.removeItem('biziq_token');
        localStorage.removeItem('biziq_user');
        setState({ user: null, token: null, isLoading: false, error: null });
    }, []);

    const clearError = useCallback(() => setState(s => ({ ...s, error: null })), []);

    return (
        <AuthContext.Provider value={{ ...state, signIn, signUp, signOut, clearError }}>
            {children}
        </AuthContext.Provider>
    );
}

// ── Hook ───────────────────────────────────────────────────────
export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
    return ctx;
}
