"use client";

import { useState, useEffect, useCallback } from "react";
import type { Annotation } from "@/types";
import { getAnnotations, createAnnotation, resolveAnnotation, deleteAnnotation } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { MessageSquare, CheckCheck, Trash2, Send, Loader2, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  comparisonId: string;
  changeId: string;
  changeType?: string;
  onClose?: () => void;
  floating?: boolean;
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function AnnotationsPanel({
  comparisonId,
  changeId,
  changeType = "semantic",
  onClose,
  floating = false,
}: Props) {
  const { user } = useAuth();
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [loading, setLoading]         = useState(true);
  const [draft, setDraft]             = useState("");
  const [author, setAuthor]           = useState(user?.full_name || user?.username || "Reviewer");
  const [submitting, setSubmitting]   = useState(false);
  const [error, setError]             = useState<string | null>(null);

  // Keep author in sync when user changes
  useEffect(() => {
    if (user) setAuthor(user.full_name || user.username);
  }, [user]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const all = await getAnnotations(comparisonId);
      // Only show annotations for this specific change
      setAnnotations(all.filter(a => a.change_id === changeId));
    } catch {
      // silently fail — annotations are non-critical
    } finally {
      setLoading(false);
    }
  }, [comparisonId, changeId]);

  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    const text = draft.trim();
    if (!text || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const ann = await createAnnotation({
        comparison_id: comparisonId,
        change_id: changeId,
        change_type: changeType,
        author: author.trim() || "Reviewer",
        text,
      });
      setAnnotations(prev => [...prev, ann]);
      setDraft("");
    } catch {
      setError("Failed to save comment. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleResolve = async (id: string) => {
    try {
      const updated = await resolveAnnotation(id);
      setAnnotations(prev => prev.map(a => a.id === id ? updated : a));
    } catch { /* ignore */ }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteAnnotation(id);
      setAnnotations(prev => prev.filter(a => a.id !== id));
    } catch { /* ignore */ }
  };

  const open     = annotations.filter(a => !a.resolved);
  const resolved = annotations.filter(a => a.resolved);

  return (
    <div className={cn(
      "flex flex-col bg-ink-950 border border-ink-800 rounded-xl overflow-hidden",
      floating ? "w-80 shadow-2xl shadow-ink-950/80" : "w-full"
    )}>
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-ink-800 bg-ink-900">
        <MessageSquare className="w-3.5 h-3.5 text-amber-400" />
        <span className="text-xs font-semibold text-ink-200">
          Comments
          {open.length > 0 && (
            <span className="ml-2 px-1.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 font-mono">
              {open.length}
            </span>
          )}
        </span>
        {onClose && (
          <button onClick={onClose} className="ml-auto text-ink-600 hover:text-ink-300 transition-colors">
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Thread */}
      <div className="overflow-y-auto max-h-64 p-3 space-y-2">
        {loading ? (
          <div className="flex items-center justify-center py-5">
            <Loader2 className="w-4 h-4 text-ink-600 animate-spin" />
          </div>
        ) : annotations.length === 0 ? (
          <p className="text-xs text-ink-700 text-center py-5 italic">No comments yet — be the first.</p>
        ) : (
          <>
            {open.map(ann => (
              <div key={ann.id} className="p-3 rounded-lg bg-ink-900 border border-ink-800 group">
                <div className="flex items-baseline justify-between gap-2 mb-1.5">
                  <span className="text-xs font-semibold text-ink-300">{ann.author}</span>
                  <span className="text-xs text-ink-700">{timeAgo(ann.created_at)}</span>
                </div>
                <p className="text-xs text-ink-400 leading-relaxed">{ann.text}</p>
                <div className="flex gap-3 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => handleResolve(ann.id)}
                    className="flex items-center gap-1 text-xs text-jade-500 hover:text-jade-400 transition-colors"
                  >
                    <CheckCheck className="w-3 h-3" /> Resolve
                  </button>
                  <button
                    onClick={() => handleDelete(ann.id)}
                    className="flex items-center gap-1 text-xs text-crimson-500 hover:text-crimson-400 transition-colors"
                  >
                    <Trash2 className="w-3 h-3" /> Delete
                  </button>
                </div>
              </div>
            ))}

            {resolved.length > 0 && (
              <details className="group/resolved">
                <summary className="text-xs text-ink-700 cursor-pointer hover:text-ink-500 transition-colors select-none py-1">
                  {resolved.length} resolved comment{resolved.length !== 1 ? "s" : ""}
                </summary>
                <div className="mt-2 space-y-2">
                  {resolved.map(ann => (
                    <div key={ann.id} className="p-2.5 rounded-lg bg-ink-900 border border-ink-800 opacity-40">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-semibold text-ink-600 line-through">{ann.author}</span>
                        <CheckCheck className="w-3 h-3 text-jade-600" />
                      </div>
                      <p className="text-xs text-ink-600 line-through">{ann.text}</p>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </>
        )}
      </div>

      {/* Composer */}
      <div className="border-t border-ink-800 p-3 space-y-2 bg-ink-900/50">
        {/* Author name — pre-filled from auth, editable */}
        <input
          value={author}
          onChange={e => setAuthor(e.target.value)}
          placeholder="Your name"
          className="w-full bg-ink-950 border border-ink-800 rounded-lg px-3 py-1.5 text-xs text-ink-300 placeholder-ink-700 focus:outline-none focus:border-amber-500/40 transition-colors"
        />

        <div className="flex gap-2">
          <textarea
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit(); }}
            placeholder="Write a comment… (⌘↵ to send)"
            rows={2}
            className="flex-1 bg-ink-950 border border-ink-800 rounded-lg px-3 py-2 text-xs text-ink-300 placeholder-ink-700 focus:outline-none focus:border-amber-500/40 transition-colors resize-none"
          />
          <button
            onClick={submit}
            disabled={!draft.trim() || submitting}
            className="self-end px-3 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-ink-950 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            {submitting
              ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
              : <Send className="w-3.5 h-3.5" />}
          </button>
        </div>

        {error && <p className="text-xs text-crimson-400">{error}</p>}
      </div>
    </div>
  );
}
