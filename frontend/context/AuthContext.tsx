"use client";

import {
  createContext, useContext, useState, useEffect,
  useCallback, ReactNode,
} from "react";
import axios from "axios";
import { useRouter, usePathname } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "pl_token";
const PUBLIC_PATHS = ["/login"];

export interface AuthUser {
  id: string;
  username: string;
  full_name: string | null;
}

interface AuthCtx {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser]       = useState<AuthUser | null>(null);
  const [token, setToken]     = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router   = useRouter();
  const pathname = usePathname();

  // Attach Bearer token to every outgoing axios request
  useEffect(() => {
    const id = axios.interceptors.request.use((config) => {
      const t = localStorage.getItem(TOKEN_KEY);
      if (t) config.headers.Authorization = `Bearer ${t}`;
      return config;
    });
    return () => axios.interceptors.request.eject(id);
  }, []);

  // Restore session from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(TOKEN_KEY);
    if (!saved) { setLoading(false); return; }
    axios
      .get<AuthUser>(`${API_URL}/api/auth/me`, {
        headers: { Authorization: `Bearer ${saved}` },
      })
      .then((res) => { setToken(saved); setUser(res.data); })
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false));
  }, []);

  // Route guard — redirect to /login when unauthenticated
  useEffect(() => {
    if (loading) return;
    const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p));
    if (!user && !isPublic) router.replace("/login");
  }, [user, loading, pathname, router]);

  const _persist = useCallback((t: string, u: AuthUser) => {
    localStorage.setItem(TOKEN_KEY, t);
    setToken(t);
    setUser(u);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const form = new URLSearchParams();
    form.append("username", username.trim().toLowerCase());
    form.append("password", password);
    const res = await axios.post<{
      access_token: string; user_id: string; username: string; full_name: string | null;
    }>(`${API_URL}/api/auth/login`, form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    _persist(res.data.access_token, {
      id: res.data.user_id,
      username: res.data.username,
      full_name: res.data.full_name,
    });
    router.replace("/");
  }, [_persist, router]);

  const register = useCallback(async (
    username: string, password: string, fullName?: string
  ) => {
    const res = await axios.post<{
      access_token: string; user_id: string; username: string; full_name: string | null;
    }>(`${API_URL}/api/auth/register`, {
      username: username.trim().toLowerCase(),
      password,
      full_name: fullName?.trim() || null,
    });
    _persist(res.data.access_token, {
      id: res.data.user_id,
      username: res.data.username,
      full_name: res.data.full_name,
    });
    router.replace("/");
  }, [_persist, router]);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    router.replace("/login");
  }, [router]);

  return (
    <Ctx.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth(): AuthCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be inside <AuthProvider>");
  return ctx;
}
