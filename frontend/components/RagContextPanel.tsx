"use client";

import { useState, useEffect } from "react";
import { Sparkles, Globe, Building2, ChevronDown, ChevronUp, BookOpen } from "lucide-react";
import type { RagContextSummary } from "@/types";

interface Props {
  ragContext: RagContextSummary | null | undefined;
}

export default function RagContextPanel({ ragContext }: Props) {
  const [expanded, setExpanded] = useState(false);
  useEffect(() => {
    if (expanded) {
      window.scrollBy({
        top: 200,
        behavior: "smooth",
      });
    }
  }, [expanded]);

  if (!ragContext || ragContext.sources.length === 0) {
    return (
      <div className="flex items-center gap-3 px-4 py-3 my-6 rounded-xl bg-ink-900 border border-ink-700 text-sm text-ink-500">
        <BookOpen className="w-4 h-4 text-ink-600 flex-shrink-0" />
        <span>
          No knowledge base context was used. Add documents to the{" "}
          <a href="/knowledge-base" className="text-amber-400 hover:underline">Knowledge Base</a>{" "}
          to ground analysis in regulatory standards.
        </span>
      </div>
    );
  }

  const total = ragContext.global_chunks_used + ragContext.personal_chunks_used;

  return (
    <div className="rounded-xl bg-ink-900 border border-ink-700 overflow-hidden my-6">
      {/* Header */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-ink-800 transition-all text-left"
      >
        <div className="w-7 h-7 rounded-lg bg-amber-500/10 flex items-center justify-center flex-shrink-0">
          <Sparkles className="w-3.5 h-3.5 text-amber-400" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-ink-200">
            Most Relevant References
          </p>
          <p className="text-xs text-ink-500">
            {total} chunk{total !== 1 ? "s" : ""} retrieved from knowledge base ·{" "}
            {ragContext.global_chunks_used > 0 && (
              <span className="text-amber-400">{ragContext.global_chunks_used} global</span>
            )}
            {ragContext.global_chunks_used > 0 && ragContext.personal_chunks_used > 0 && " + "}
            {ragContext.personal_chunks_used > 0 && (
              <span className="text-jade-400">{ragContext.personal_chunks_used} company</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400">
            Grounds
          </span>
          {expanded
            ? <ChevronUp className="w-4 h-4 text-ink-500" />
            : <ChevronDown className="w-4 h-4 text-ink-500" />
          }
        </div>
      </button>

      {/* Expanded source list */}
      {expanded && (
        <div className="border-t border-ink-800 px-3 sm:px-4 py-3 space-y-2">
          <p className="text-xs text-ink-500 mb-3">
            The following regulatory context contributed to the compliance analysis:
          </p>
          {ragContext.sources.map((src, i) => (
            <div
              key={i}
              className="flex gap-3 p-3 rounded-lg bg-ink-800 border border-ink-700"
            >
              <div className={`mt-0.5 flex-shrink-0 w-5 h-5 rounded-md flex items-center justify-center ${src.scope === "global" ? "bg-amber-500/10" : "bg-jade-500/10"
                }`}>
                {src.scope === "global"
                  ? <Globe className="w-3 h-3 text-amber-400" />
                  : <Building2 className="w-3 h-3 text-jade-400" />
                }
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1 gap-2">
                  <p className="text-xs font-medium text-ink-300 truncate">
                    {src.source_doc_name}
                  </p>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <span className={`text-xs px-1.5 py-0.5 rounded-full border ${src.scope === "global"
                      ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
                      : "text-jade-400 bg-jade-500/10 border-jade-500/20"
                      }`}>
                      {src.scope === "global" ? "Global KB" : "Company KB"}
                    </span>
                    <span className="text-xs text-ink-600">
                      {(src.relevance_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <p className="text-xs text-ink-500 line-clamp-3 leading-relaxed">
                  {src.excerpt}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
