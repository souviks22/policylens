"use client";

import { useState, useMemo } from "react";
import type { ComparisonResult, DiffChunk } from "@/types";
import { cn } from "@/lib/utils";
import ChangeBadge from "./ChangeBadge";
import { Columns, List } from "lucide-react";

interface Props {
  result: ComparisonResult;
}

function highlight(text: string, type: "old" | "new") {
  const cls = type === "old"
    ? "bg-crimson-500/10 text-crimson-200"
    : "bg-jade-500/10 text-jade-200";
  return <span className={cn("block rounded px-1 py-0.5", cls)}>{text}</span>;
}

function DiffChunkRow({ chunk }: { chunk: DiffChunk }) {
  return (
    <div className="border-b border-ink-800 last:border-0">
      <div className="px-4 py-2 flex items-center gap-2 bg-ink-900/50 border-b border-ink-800">
        <ChangeBadge type={chunk.type} size="sm" />
        {chunk.section && (
          <span className="text-xs text-ink-600">§ {chunk.section}</span>
        )}
      </div>
      <div className="grid grid-cols-2 divide-x divide-ink-800">
        <div className="p-4 text-xs font-mono leading-relaxed text-ink-400 min-h-[2rem]">
          {chunk.old_text
            ? highlight(chunk.old_text, "old")
            : <span className="text-ink-700 italic">—</span>}
        </div>
        <div className="p-4 text-xs font-mono leading-relaxed text-ink-400 min-h-[2rem]">
          {chunk.new_text
            ? highlight(chunk.new_text, "new")
            : <span className="text-ink-700 italic">—</span>}
        </div>
      </div>
    </div>
  );
}

export default function DiffViewer({ result }: Props) {
  const [view, setView] = useState<"diff" | "side">("diff");
  const [page, setPage] = useState(0);
  const perPage = 20;

  const chunks = useMemo(
    () => result.diff_chunks.filter((c) => c.type !== "unchanged"),
    [result.diff_chunks]
  );

  const totalPages = Math.ceil(chunks.length / perPage);
  const pageChunks = chunks.slice(page * perPage, (page + 1) * perPage);

  return (
    <div className="space-y-4 tab-content">
      {/* Toolbar */}
      <div className="flex items-center gap-3 p-4 rounded-xl bg-ink-900 border border-ink-800">
        <div className="flex gap-1">
          <button
            onClick={() => setView("diff")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              view === "diff" ? "bg-amber-500 text-ink-950" : "bg-ink-800 text-ink-400 hover:bg-ink-700"
            )}
          >
            <List className="w-3.5 h-3.5" /> Changes Only
          </button>
          <button
            onClick={() => setView("side")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              view === "side" ? "bg-amber-500 text-ink-950" : "bg-ink-800 text-ink-400 hover:bg-ink-700"
            )}
          >
            <Columns className="w-3.5 h-3.5" /> Side-by-Side
          </button>
        </div>
        <span className="ml-auto text-xs text-ink-600">
          {chunks.length} changed block{chunks.length !== 1 ? "s" : ""}
        </span>
      </div>

      {view === "diff" ? (
        <div className="rounded-2xl border border-ink-800 overflow-hidden">
          {/* Column headers */}
          <div className="grid grid-cols-2 divide-x divide-ink-800 bg-ink-900 border-b border-ink-800">
            <div className="px-4 py-2.5 flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-crimson-500/20 border border-crimson-500/30 text-crimson-400 text-xs flex items-center justify-center font-mono">A</span>
              <span className="text-xs font-medium text-ink-400 truncate">{result.doc1_name}</span>
            </div>
            <div className="px-4 py-2.5 flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-jade-500/20 border border-jade-500/30 text-jade-400 text-xs flex items-center justify-center font-mono">B</span>
              <span className="text-xs font-medium text-ink-400 truncate">{result.doc2_name}</span>
            </div>
          </div>

          {pageChunks.length === 0 ? (
            <div className="text-center py-16 text-ink-600">No textual differences detected.</div>
          ) : (
            pageChunks.map((chunk) => <DiffChunkRow key={chunk.id} chunk={chunk} />)
          )}
        </div>
      ) : (
        /* Side by side full text */
        <div className="rounded-2xl border border-ink-800 overflow-hidden">
          <div className="grid grid-cols-2 divide-x divide-ink-800 bg-ink-900 border-b border-ink-800">
            <div className="px-4 py-2.5 flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-crimson-500/20 border border-crimson-500/30 text-crimson-400 text-xs flex items-center justify-center font-mono">A</span>
              <span className="text-xs font-medium text-ink-400 truncate">{result.doc1_name}</span>
            </div>
            <div className="px-4 py-2.5 flex items-center gap-2">
              <span className="w-4 h-4 rounded bg-jade-500/20 border border-jade-500/30 text-jade-400 text-xs flex items-center justify-center font-mono">B</span>
              <span className="text-xs font-medium text-ink-400 truncate">{result.doc2_name}</span>
            </div>
          </div>
          <div className="grid grid-cols-2 divide-x divide-ink-800">
            <div className="p-4 text-xs font-mono text-ink-400 leading-relaxed whitespace-pre-wrap max-h-[60vh] overflow-y-auto">
              {result.doc1_content}
            </div>
            <div className="p-4 text-xs font-mono text-ink-400 leading-relaxed whitespace-pre-wrap max-h-[60vh] overflow-y-auto">
              {result.doc2_content}
            </div>
          </div>
        </div>
      )}

      {/* Pagination */}
      {view === "diff" && totalPages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-4 py-2 rounded-lg text-sm bg-ink-800 text-ink-300 hover:bg-ink-700 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-xs text-ink-500 font-mono">
            {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="px-4 py-2 rounded-lg text-sm bg-ink-800 text-ink-300 hover:bg-ink-700 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
