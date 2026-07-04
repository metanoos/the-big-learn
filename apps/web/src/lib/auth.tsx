"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getMe, login as apiLogin, register as apiRegister, logout as apiLogout, resendVerification, type User, ApiError } from "./api";

type AuthState = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  resendVerifyEmail: () => Promise<void>;
};

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const value: AuthState = {
    user,
    loading,
    async login(email, password) {
      setUser(await apiLogin(email, password));
    },
    async register(username, email, password) {
      setUser(await apiRegister(username, email, password));
    },
    async logout() {
      await apiLogout();
      setUser(null);
    },
    async resendVerifyEmail() {
      await resendVerification();
      // refresh user state (though it won't change verified status, the
      // throttle is server-side; this confirms the request landed)
    },
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

// re-export for convenience
export { ApiError };
export type { User };
