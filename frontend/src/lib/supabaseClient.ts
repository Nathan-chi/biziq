import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string;
const supabaseAnon = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

if (!supabaseUrl || !supabaseAnon) {
    throw new Error(
        'Missing Supabase env vars.\n' +
        'Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to your .env file.'
    );
}

export const supabase = createClient(supabaseUrl, supabaseAnon, {
    auth: {
        // Persist session in localStorage so users stay logged in on refresh
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true, // handles OAuth + magic link redirects automatically
    },
});
