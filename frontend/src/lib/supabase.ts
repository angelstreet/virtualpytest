import { createClient } from '@supabase/supabase-js';

// Get environment variables
// Option 1: Add to frontend/.env: VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
// Option 2: Leave empty to disable auth completely (no login required)
const supabaseUrl = 
  (import.meta as any).env?.VITE_SUPABASE_URL || 
  '';

const supabaseAnonKey = 
  (import.meta as any).env?.VITE_SUPABASE_ANON_KEY || 
  '';

// Check if auth is enabled (credentials provided)
export const isAuthEnabled = !!(supabaseUrl && supabaseAnonKey);

if (!isAuthEnabled) {
  console.log('🔓 Auth disabled: No Supabase credentials in frontend/.env');
  console.log('   App will run without authentication');
  console.log('   To enable auth, add to frontend/.env:');
  console.log('   - VITE_SUPABASE_URL=https://your-project.supabase.co');
  console.log('   - VITE_SUPABASE_ANON_KEY=your-key-here');
} else {
  console.log('🔒 Auth enabled');
  console.log('   Supabase URL:', supabaseUrl);
  console.log('   Anon Key:', supabaseAnonKey ? `${supabaseAnonKey.substring(0, 20)}...` : 'MISSING');
}

// Create Supabase client (with dummy values if auth disabled)
export const supabase = createClient(
  supabaseUrl || 'https://placeholder.supabase.co',
  supabaseAnonKey || 'placeholder-key',
  {
    auth: {
      autoRefreshToken: isAuthEnabled,
      persistSession: isAuthEnabled,
      detectSessionInUrl: isAuthEnabled,
    },
  }
);

// Database types for better type safety
export type Database = {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string;
          email: string | null;
          full_name: string | null;
          avatar_url: string | null;
          role: 'admin' | 'tester' | 'viewer';
          permissions: string[];
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id: string;
          email?: string | null;
          full_name?: string | null;
          avatar_url?: string | null;
          role?: 'admin' | 'tester' | 'viewer';
          permissions?: string[];
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          email?: string | null;
          full_name?: string | null;
          avatar_url?: string | null;
          role?: 'admin' | 'tester' | 'viewer';
          permissions?: string[];
          created_at?: string;
          updated_at?: string;
        };
      };
    };
  };
};

