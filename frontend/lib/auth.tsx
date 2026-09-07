'use client';

// Client-side auth state, as a single React Context provider instead of a
// grab-bag of localStorage-reading utility functions repeated on every page.
//
// The backend requires a real bearer token on every protected route (see the
// security hardening in the backend), so the frontend needs one source of
// truth for "who is logged in" and one reusable guard (`useRequireAuth`) for
// "is this page even allowed to render for this user" - rather than each
// page hand-rolling its own redirect-if-missing check.

import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';

export type Role = 'VENDOR' | 'LENDER' | 'ADMIN';

export interface AuthUser {
  user_id: string;
  email: string;
  role: Role;
  vendor_id: string | null;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  register: (email: string, password: string, role: string, phone?: string) => Promise<AuthUser>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const STORAGE_TOKEN_KEY = 'access_token';
const STORAGE_USER_KEY = 'auth_user';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Restore session from localStorage on first load. There is no hardcoded
    // vendor/user fallback anywhere in this flow -- if there's no valid stored
    // session, `user` stays null and protected pages redirect to /login.
    try {
      const token = localStorage.getItem(STORAGE_TOKEN_KEY);
      const storedUser = localStorage.getItem(STORAGE_USER_KEY);
      if (token && storedUser) {
        setUser(JSON.parse(storedUser));
      }
    } catch {
      // Corrupt storage -> treat as logged out rather than throwing.
    } finally {
      setLoading(false);
    }
  }, []);

  const persistSession = (data: any): AuthUser => {
    const authUser: AuthUser = {
      user_id: data.user_id,
      email: data.email,
      role: data.role,
      vendor_id: data.vendor_id ?? null,
    };
    localStorage.setItem(STORAGE_TOKEN_KEY, data.access_token);
    localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(authUser));
    // lib/api.ts reads the raw token under this key
    localStorage.setItem('access_token', data.access_token);
    setUser(authUser);
    return authUser;
  };

  const login = useCallback(async (email: string, password: string) => {
    const data = await api.login(email, password);
    return persistSession(data);
  }, []);

  const register = useCallback(async (email: string, password: string, role: string, phone?: string) => {
    const data = await api.register(email, password, role, phone);
    return persistSession(data);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_TOKEN_KEY);
    localStorage.removeItem(STORAGE_USER_KEY);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}

/**
 * Redirects to /login if there is no authenticated session, and (optionally)
 * enforces that the session's role is one of `allowedRoles`. Call this at the
 * top of any protected page component.
 */
export function useRequireAuth(allowedRoles?: Role[]) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    if (allowedRoles && !allowedRoles.includes(user.role)) {
      router.replace('/login');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, loading]);

  return { user, loading };
}
