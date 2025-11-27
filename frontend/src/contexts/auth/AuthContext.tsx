import React, { createContext, useContext, useEffect, useState } from 'react';
import { User, Session } from '@supabase/supabase-js';
import { supabase } from '../../lib/supabase';
import { UserProfile } from '../../types/auth';

interface AuthContextType {
  user: User | null;
  profile: UserProfile | null;
  session: Session | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  signInWithGoogle: () => Promise<void>;
  signInWithGithub: () => Promise<void>;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  signUpWithEmail: (email: string, password: string, fullName?: string) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuthContext = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch user profile from database with caching
  const fetchProfile = async (userId: string): Promise<UserProfile | null> => {
    // Try cache first
    const cached = localStorage.getItem(`auth_profile_${userId}`);
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        return parsed as UserProfile;
      } catch (e) {
        console.warn('Error parsing cached profile:', e);
        localStorage.removeItem(`auth_profile_${userId}`);
      }
    }

    try {
      const { data, error } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', userId)
        .single();

      if (error) {
        // Profile doesn't exist yet (common on first login before trigger runs)
        // or profiles table doesn't exist (SQL not run yet)
        console.warn('Profile fetch error (expected on first login):', error.message);
        return null;
      }

      // Update cache
      if (data) {
        localStorage.setItem(`auth_profile_${userId}`, JSON.stringify(data));
      }

      return data as UserProfile;
    } catch (err) {
      console.warn('Error in fetchProfile (table may not exist yet):', err);
      return null;
    }
  };

  // Initialize auth state
  useEffect(() => {
    let mounted = true;
    let initialLoadHandled = false;
    
    // Safety timeout - clear loading if auth completely fails
    const timeout = setTimeout(() => {
      if (mounted && isLoading && !initialLoadHandled) {
        console.warn('[@AuthContext] Auth initialization timeout - clearing loading state');
        setIsLoading(false);
      }
    }, 3000); // 3 second timeout as fallback

    const initAuth = async () => {
      try {
        console.log('[@AuthContext] Initializing auth...');
        
        // Try to get session from localStorage immediately (synchronous-like speed)
        const { data: { session: initialSession }, error: sessionError } = await supabase.auth.getSession();
        
        if (sessionError) {
          console.error('[@AuthContext] Session error:', sessionError);
          if (mounted) {
            setIsLoading(false);
            initialLoadHandled = true;
            clearTimeout(timeout);
          }
          return;
        }
        
        if (mounted && initialSession) {
          console.log('[@AuthContext] Session found immediately:', initialSession.user.email);
          setSession(initialSession);
          setUser(initialSession.user);
          
          // Fetch profile before clearing loading state to ensure permissions are ready
          console.log('[@AuthContext] Fetching profile...');
          const userProfile = await fetchProfile(initialSession.user.id);
          
          if (mounted) {
            if (userProfile) {
              console.log('[@AuthContext] Profile loaded:', userProfile.role);
            }
            setProfile(userProfile);
            
            // Clear loading only after profile is fetched
            setIsLoading(false);
            initialLoadHandled = true;
            clearTimeout(timeout);
          }
        } else if (mounted) {
           // No session found immediately - clear loading and let user see login
           console.log('[@AuthContext] No immediate session found');
           setIsLoading(false);
           initialLoadHandled = true;
           clearTimeout(timeout);
        }
      } catch (error: any) {
        console.error('[@AuthContext] Error initializing auth:', error.message);
        if (mounted) {
          setIsLoading(false);
          initialLoadHandled = true;
          clearTimeout(timeout);
        }
      }
    };

    initAuth();

    // Listen for auth changes (login, logout, token refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, newSession) => {
        console.log('[@AuthContext] Auth state changed:', event, newSession ? `User: ${newSession.user.email}` : 'No session');
        
        if (!mounted) return;

        // Skip SIGNED_IN event on initial load (already handled by initAuth)
        if (event === 'SIGNED_IN' && !initialLoadHandled) {
          console.log('[@AuthContext] Skipping SIGNED_IN event - already handled by initAuth');
          return;
        }

        setSession(newSession);
        setUser(newSession?.user ?? null);

        if (newSession?.user) {
          const userProfile = await fetchProfile(newSession.user.id);
          if (mounted && userProfile) {
            console.log('[@AuthContext] Profile updated:', userProfile.role);
            setProfile(userProfile);
          }
        } else {
          setProfile(null);
        }

        if (!initialLoadHandled) {
          setIsLoading(false);
          initialLoadHandled = true;
          clearTimeout(timeout);
        }
      }
    );

    return () => {
      mounted = false;
      clearTimeout(timeout);
      subscription.unsubscribe();
    };
  }, []);

  // Sign in with Google
  const signInWithGoogle = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    if (error) {
      console.error('Error signing in with Google:', error);
      throw error;
    }
  };

  // Sign in with GitHub
  const signInWithGithub = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'github',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    if (error) {
      console.error('Error signing in with GitHub:', error);
      throw error;
    }
  };

  // Sign in with Email/Password
  const signInWithEmail = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      console.error('Error signing in with email:', error);
      throw error;
    }
  };

  // Sign up with Email/Password
  const signUpWithEmail = async (email: string, password: string, fullName?: string) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          full_name: fullName,
        },
      },
    });

    if (error) {
      console.error('Error signing up with email:', error);
      throw error;
    }
  };

  // Reset Password
  const resetPassword = async (email: string) => {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/reset-password`,
    });

    if (error) {
      console.error('Error resetting password:', error);
      throw error;
    }
  };

  // Sign out
  const signOut = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) {
      console.error('Error signing out:', error);
      throw error;
    }
    // Clear local storage cache
    if (user) {
      localStorage.removeItem(`auth_profile_${user.id}`);
    }
    setUser(null);
    setProfile(null);
    setSession(null);
  };

  // Refresh profile manually (bypassing cache read, but updating it)
  const refreshProfile = async () => {
    if (user) {
      try {
        const { data } = await supabase
          .from('profiles')
          .select('*')
          .eq('id', user.id)
          .single();

        if (data) {
          localStorage.setItem(`auth_profile_${user.id}`, JSON.stringify(data));
          setProfile(data as UserProfile);
        }
      } catch (err) {
        console.error('Error refreshing profile:', err);
      }
    }
  };

  const value: AuthContextType = {
    user,
    profile,
    session,
    isLoading,
    isAuthenticated: !!user,
    signInWithGoogle,
    signInWithGithub,
    signInWithEmail,
    signUpWithEmail,
    resetPassword,
    signOut,
    refreshProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

