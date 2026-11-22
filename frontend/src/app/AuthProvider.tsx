import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { apiRequest, setAccessToken } from '../lib/api/client';
import type { AdminSubRole, AuthSessionUser, KnitauRole } from '../lib/auth/rbac';

interface BackendUserPayload {
  id: string;
  email: string;
  full_name: string;
  role: KnitauRole;
  admin_sub_role: AdminSubRole | '';
}

interface AuthContextValue {
  user: AuthSessionUser | null;
  isRestoringSession: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function mapUser(raw: BackendUserPayload): AuthSessionUser {
  return {
    id: raw.id,
    fullName: raw.full_name,
    role: raw.role,
    adminSubRole: raw.admin_sub_role || undefined,
  };
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthSessionUser | null>(null);
  const [isRestoringSession, setIsRestoringSession] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const refreshed = await apiRequest<{ access: string }>('/auth/refresh/', {
          method: 'POST',
          skipAuthRefresh: true,
        });
        setAccessToken(refreshed.access);
        const me = await apiRequest<BackendUserPayload>('/auth/me/');
        if (active) setUser(mapUser(me));
      } catch {
        setAccessToken(null);
        if (active) setUser(null);
      } finally {
        if (active) setIsRestoringSession(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiRequest<{ access: string; user: BackendUserPayload }>('/auth/login/', {
      method: 'POST',
      body: { email, password },
      skipAuthRefresh: true,
    });
    setAccessToken(res.access);
    setUser(mapUser(res.user));
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiRequest('/auth/logout/', { method: 'POST', skipAuthRefresh: true });
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, isRestoringSession, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
