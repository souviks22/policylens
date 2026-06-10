"use client";

import { useState, useEffect } from "react";
import { listHistory, deleteComparison, getComparison } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import type { ComparisonListItem, ComparisonResult } from "@/types";
import ComparisonDashboard from "@/components/ComparisonDashboard";
import {
  GitCompare, Trash2, ExternalLink, Loader2, ChevronRight,
  AlertTriangle, History, ArrowLeft, LogOut, User, Database,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";

const impactColors: Record<string, string> = {
  high:   "text-crimson-400 border-crimson-500/30 bg-crimson-500/10",
  medium: "text-amber-400  border-amber-500/30  bg-amber-500/10",
  low:    "text-jade-400   border-jade-500/30   bg-jade-500/10",
  none:   "text-ink-500    border-ink-700        bg-ink-800",
};

function timeStr(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export default function HistoryPage() {
  const { user, logout, loading: authLoading } = useAuth();
  const [items, setItems]       = useState<ComparisonListItem[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [viewing, setViewing]   = useState<ComparisonResult | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !user) return;
    listHistory()
      .then(setItems)
      .catch(() => setError("Could not load history. Is the API running?"))
      .finally(() => setLoading(false));
  }, [authLoading, user]);

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this comparison?")) return;
    setDeleting(id);
    try {
      await deleteComparison(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } finally { setDeleting(null); }
  };

  const handleOpen = async (id: string) => {
    setLoadingId(id);
    try {
      const result = await getComparison(id);
      setViewing(result);
    } catch { alert("Could not load comparison."); }
    finally { setLoadingId(null); }
  };

  if (viewing) {
    return <ComparisonDashboard result={viewing} onReset={() => setViewing(null)} />;
  }

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-amber-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="grain min-h-screen flex flex-col">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="border-b border-ink-800 px-8 py-5 flex items-center gap-3">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-500 flex items-center justify-center">
            <GitCompare className="w-4 h-4 text-ink-950" />
          </div>
          <span className="font-serif text-xl font-semibold text-ink-100">PolicyLens</span>
        </Link>

        <ChevronRight className="w-4 h-4 text-ink-600" />
        <div className="flex items-center gap-1.5 text-sm text-ink-300">
          <History className="w-4 h-4 text-amber-500" />
          <span>History</span>
        </div>

        <div className="ml-auto flex items-center gap-3">
          <Link
            href="/knowledge-base"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-ink-400 hover:text-ink-200 hover:bg-ink-800 transition-all"
          >
            <Database className="w-3.5 h-3.5" /> Knowledge Base
          </Link>
          <Link
            href="/"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-ink-400 hover:text-ink-200 hover:bg-ink-800 transition-all"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> New Comparison
          </Link>

          {user && (
            <div className="flex items-center gap-2 pl-3 border-l border-ink-800">
              <div className="flex items-center gap-1.5 text-xs text-ink-500">
                <div className="w-6 h-6 rounded-full bg-amber-500/20 border border-amber-500/30 flex items-center justify-center">
                  <User className="w-3 h-3 text-amber-400" />
                </div>
                <span className="text-ink-400">{user.full_name || user.username}</span>
              </div>
              <button
                onClick={logout}
                className="p-1.5 rounded-lg text-ink-600 hover:text-crimson-400 hover:bg-ink-800 transition-all"
                title="Sign out"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </header>

      {/* ── Main ───────────────────────────────────────────────────────── */}
      <main className="flex-1 max-w-5xl mx-auto w-full px-6 py-10">
        <div className="mb-8">
          <h1 className="font-serif text-3xl font-bold text-ink-50 mb-2">Your Comparisons</h1>
          <p className="text-ink-500 text-sm">
            All comparisons run under <span className="text-ink-300 font-medium">{user?.username}</span> are saved here.
          </p>
        </div>

        {loading && (
          <div className="flex items-center gap-3 text-ink-500 py-16 justify-center">
            <Loader2 className="w-5 h-5 animate-spin" /> Loading…
          </div>
        )}

        {error && (
          <div className="flex items-center gap-3 p-5 rounded-xl bg-crimson-950 border border-crimson-800 text-crimson-300">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" /> {error}
          </div>
        )}

        {!loading && !error && items.length === 0 && (
          <div className="text-center py-24 text-ink-600">
            <History className="w-10 h-10 mx-auto mb-4 opacity-30" />
            <p>No comparisons yet.</p>
            <Link href="/" className="mt-4 inline-block text-sm text-amber-400 hover:underline">
              Run your first comparison →
            </Link>
          </div>
        )}

        {!loading && items.length > 0 && (
          <div className="space-y-3">
            {items.map((item) => (
              <div
                key={item.id}
                className="p-5 rounded-2xl bg-ink-900 border border-ink-800 hover:border-ink-700 transition-all"
              >
                <div className="flex items-start gap-4 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-sm font-medium text-ink-100 truncate max-w-[200px]">
                        {item.doc1_name}
                      </span>
                      <GitCompare className="w-3.5 h-3.5 text-ink-600 flex-shrink-0" />
                      <span className="text-sm font-medium text-ink-100 truncate max-w-[200px]">
                        {item.doc2_name}
                      </span>
                    </div>
                    <p className="text-xs text-ink-600">{timeStr(item.created_at)}</p>
                  </div>

                  <div className="hidden sm:flex items-center gap-4 text-xs">
                    {[
                      { v: item.total_changes, l: "changes",  c: "text-ink-300" },
                      { v: item.additions,     l: "added",    c: "text-jade-400" },
                      { v: item.deletions,     l: "deleted",  c: "text-crimson-400" },
                      { v: Math.round(item.structural_similarity * 100) + "%", l: "structural", c: "text-ink-300" },
                    ].map(({ v, l, c }) => (
                      <div key={l} className="text-center">
                        <div className={cn("font-bold font-mono", c)}>{v}</div>
                        <div className="text-ink-600">{l}</div>
                      </div>
                    ))}
                  </div>

                  <span className={cn(
                    "px-2.5 py-1 rounded-full border text-xs font-medium flex-shrink-0",
                    impactColors[item.overall_impact] ?? impactColors.none
                  )}>
                    {item.overall_impact.charAt(0).toUpperCase() + item.overall_impact.slice(1)} Impact
                  </span>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => handleOpen(item.id)}
                      disabled={!!loadingId}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-ink-800 text-ink-300 hover:bg-ink-700 disabled:opacity-50 transition-all"
                    >
                      {loadingId === item.id
                        ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        : <ExternalLink className="w-3.5 h-3.5" />}
                      Open
                    </button>
                    <button
                      onClick={() => handleDelete(item.id)}
                      disabled={deleting === item.id}
                      className="p-1.5 rounded-lg text-ink-600 hover:text-crimson-400 hover:bg-crimson-950/40 transition-all"
                    >
                      {deleting === item.id
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <Trash2 className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
