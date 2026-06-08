"use client";

import { useState, FormEvent } from "react";
import { useAuth } from "@/context/AuthContext";
import { GitCompare, Eye, EyeOff, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type Mode = "login" | "register";

export default function LoginPage() {
  const { login, register } = useAuth();
  const [mode, setMode]         = useState<Mode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);

  const switchMode = (m: Mode) => { setMode(m); setError(null); };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (mode === "register" && password.length < 6) {
      setError("Password must be at least 6 characters."); return;
    }
    setLoading(true);
    try {
      if (mode === "login") {
        await login(username, password);
      } else {
        await register(username, password, fullName || undefined);
      }
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || (err instanceof Error ? err.message : "Something went wrong"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grain min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">

        {/* Brand */}
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <div className="w-10 h-10 rounded-xl bg-amber-500 flex items-center justify-center">
            <GitCompare className="w-5 h-5 text-ink-950" />
          </div>
          <span className="font-serif text-2xl font-bold text-ink-50">PolicyLens</span>
        </div>

        <div className="bg-ink-900 border border-ink-800 rounded-2xl p-8 shadow-2xl shadow-ink-950">

          {/* Tabs */}
          <div className="flex rounded-xl overflow-hidden border border-ink-800 mb-7">
            {(["login", "register"] as Mode[]).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => switchMode(m)}
                className={cn(
                  "flex-1 py-2.5 text-sm font-medium transition-all",
                  mode === m ? "bg-amber-500 text-ink-950" : "text-ink-500 hover:text-ink-300"
                )}
              >
                {m === "login" ? "Sign In" : "Register"}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && (
              <div>
                <label className="block text-xs font-medium text-ink-400 mb-1.5">
                  Full Name <span className="text-ink-700">(optional)</span>
                </label>
                <input
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Jane Smith"
                  className="w-full bg-ink-950 border border-ink-800 rounded-xl px-4 py-2.5 text-sm text-ink-100 placeholder-ink-700 focus:outline-none focus:border-amber-500/50 transition-colors"
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-ink-400 mb-1.5">Username</label>
              <input
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="yourhandle"
                autoComplete="username"
                className="w-full bg-ink-950 border border-ink-800 rounded-xl px-4 py-2.5 text-sm text-ink-100 placeholder-ink-700 focus:outline-none focus:border-amber-500/50 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-ink-400 mb-1.5">Password</label>
              <div className="relative">
                <input
                  required
                  type={showPw ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  className="w-full bg-ink-950 border border-ink-800 rounded-xl px-4 py-2.5 pr-11 text-sm text-ink-100 placeholder-ink-700 focus:outline-none focus:border-amber-500/50 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-600 hover:text-ink-400 transition-colors"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-crimson-950 border border-crimson-800 text-crimson-300 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl bg-amber-500 hover:bg-amber-400 text-ink-950 font-semibold text-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2 mt-2"
            >
              {loading
                ? <><Loader2 className="w-4 h-4 animate-spin" />{mode === "login" ? "Signing in…" : "Creating account…"}</>
                : mode === "login" ? "Sign In" : "Create Account"}
            </button>
          </form>

          <p className="text-xs text-ink-600 text-center mt-5">
            {mode === "login" ? "No account? " : "Have an account? "}
            <button
              type="button"
              onClick={() => switchMode(mode === "login" ? "register" : "login")}
              className="text-amber-500 hover:text-amber-400 transition-colors"
            >
              {mode === "login" ? "Register" : "Sign in"}
            </button>
          </p>
        </div>

        <p className="text-center text-xs text-ink-700 mt-5">
          PolicyLens · AI Policy Document Intelligence
        </p>
      </div>
    </div>
  );
}
