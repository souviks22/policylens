"use client";

import { useState } from "react";
import type { ComparisonResult, SectionMatch } from "@/types";
import SimilarityMatrix from "./SimilarityMatrix";
import { cn } from "@/lib/utils";
import {
  CheckCircle2, AlertTriangle, PlusCircle, MinusCircle,
  Copy, Grid3x3, List, ChevronDown, ChevronUp,
} from "lucide-react";

interface Props { result: ComparisonResult; }

// ── Types ──────────────────────────────────────────────────────────────────────
type MatchType = "unchanged" | "modified" | "added" | "deleted";

const MATCH_CFG: Record<MatchType, {
  label: string;
  icon: React.FC<{ className?: string }>;
  badge: string;    // badge pill classes
  numColor: string; // stat number color
}> = {
  unchanged: {
    label: "Unchanged",
    icon: CheckCircle2,
    badge: "bg-jade-500/10 text-jade-400 border border-jade-500/30",
    numColor: "text-jade-400",
  },
  modified: {
    label: "Modified",
    icon: AlertTriangle,
    badge: "bg-amber-500/10 text-amber-400 border border-amber-500/30",
    numColor: "text-amber-400",
  },
  added: {
    label: "Added",
    icon: PlusCircle,
    badge: "bg-sapphire-500/10 text-sapphire-400 border border-sapphire-500/30",
    numColor: "text-sapphire-400",
  },
  deleted: {
    label: "Deleted",
    icon: MinusCircle,
    badge: "bg-crimson-500/10 text-crimson-400 border border-crimson-500/30",
    numColor: "text-crimson-400",
  },
};

// ── Sub-components ─────────────────────────────────────────────────────────────

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score >= 0.96 ? "bg-jade-500" :
    score >= 0.72 ? "bg-amber-500" :
    "bg-ink-700";
  return (
    <div className="flex items-center gap-2 min-w-0">
      <div className="flex-1 h-1.5 rounded-full bg-ink-800 overflow-hidden">
        <div className={cn("h-full rounded-full transition-all", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-ink-500 w-9 text-right flex-shrink-0">{pct}%</span>
    </div>
  );
}

function MatchRow({ match }: { match: SectionMatch }) {
  const [open, setOpen] = useState(false);
  const cfg = MATCH_CFG[match.match_type as MatchType] ?? MATCH_CFG.modified;
  const Icon = cfg.icon;
  const showScore = match.match_type !== "added" && match.match_type !== "deleted";

  return (
    <div className={cn(
      "rounded-xl border transition-all",
      open ? "bg-ink-900 border-ink-700" : "bg-ink-900 border-ink-800 hover:border-ink-700"
    )}>
      {/* Row header — always visible */}
      <button className="w-full text-left p-4" onClick={() => setOpen(!open)}>
        <div className="flex items-center gap-3">
          {/* Status badge */}
          <span className={cn(
            "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium flex-shrink-0",
            cfg.badge
          )}>
            <Icon className="w-3 h-3" />
            {cfg.label}
          </span>

          {/* Section names */}
          <div className="flex-1 min-w-0 grid grid-cols-1 sm:grid-cols-2 gap-1 sm:gap-3">
            <span className="text-xs text-ink-400 truncate">
              {match.doc1_section ?? <span className="text-ink-700 italic">—</span>}
            </span>
            <span className="text-xs text-ink-400 truncate">
              {match.doc2_section ?? <span className="text-ink-700 italic">—</span>}
            </span>
          </div>

          {/* Similarity bar */}
          <div className="hidden sm:block w-32 flex-shrink-0">
            {showScore && <ScoreBar score={match.similarity_score} />}
          </div>

          {/* Expand chevron */}
          <div className="flex-shrink-0 text-ink-600">
            {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </div>
        </div>
      </button>

      {/* Expanded content */}
      {open && (
        <div className="px-3 sm:px-4 pb-3 sm:pb-4 pt-3 border-t border-ink-800 grid grid-cols-1 gap-3 tab-content">
          <div>
            <p className="text-xs font-semibold text-crimson-400 mb-2 uppercase tracking-wider">
              Document A — {match.doc1_section ?? "Not present"}
            </p>
            <div className="text-xs text-ink-500 leading-relaxed font-mono bg-ink-950 rounded-lg p-3 border border-ink-800 max-h-48 overflow-y-auto whitespace-pre-wrap">
              {match.doc1_content
                ? match.doc1_content
                : <span className="italic text-ink-700">Section not present in Document A</span>}
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold text-jade-400 mb-2 uppercase tracking-wider">
              Document B — {match.doc2_section ?? "Not present"}
            </p>
            <div className="text-xs text-ink-500 leading-relaxed font-mono bg-ink-950 rounded-lg p-3 border border-ink-800 max-h-48 overflow-y-auto whitespace-pre-wrap">
              {match.doc2_content
                ? match.doc2_content
                : <span className="italic text-ink-700">Section not present in Document B</span>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function SectionAnalysis({ result }: Props) {
  const [view,   setView]   = useState<"list" | "heatmap">("list");
  const [filter, setFilter] = useState<"all" | MatchType>("all");

  const sa = result.section_analysis;
  if (!sa) {
    return (
      <div className="text-center py-16 text-ink-600 text-sm italic">
        Section analysis data is not available for this comparison.
      </div>
    );
  }

  const counts: Record<MatchType, number> = {
    unchanged: sa.matches.filter(m => m.match_type === "unchanged").length,
    modified:  sa.matches.filter(m => m.match_type === "modified").length,
    added:     sa.matches.filter(m => m.match_type === "added").length,
    deleted:   sa.matches.filter(m => m.match_type === "deleted").length,
  };

  const filtered = filter === "all"
    ? sa.matches
    : sa.matches.filter(m => m.match_type === filter);

  return (
    <div className="space-y-5 tab-content">

      {/* ── Stats row ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {/* Overall structural similarity */}
        <div className="col-span-2 sm:col-span-1 p-4 rounded-xl bg-ink-900 border border-ink-800 text-center">
          <div className="text-2xl font-bold font-mono text-ink-100">
            {Math.round(sa.overall_structural_similarity * 100)}%
          </div>
          <div className="text-xs text-ink-500 mt-0.5">Structural Similarity</div>
        </div>

        {/* Per-type counts */}
        {(["unchanged","modified","added","deleted"] as MatchType[]).map(k => {
          const cfg = MATCH_CFG[k];
          return (
            <div key={k} className="p-4 rounded-xl bg-ink-900 border border-ink-800 text-center">
              <div className={cn("text-2xl font-bold font-mono", cfg.numColor)}>
                {counts[k]}
              </div>
              <div className="text-xs text-ink-500 mt-0.5">{cfg.label}</div>
            </div>
          );
        })}
      </div>

      {/* ── Clone pairs alert ──────────────────────────────────────────────── */}
      {sa.semantic_clone_pairs.length > 0 && (
        <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/20 flex items-start gap-3">
          <Copy className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-amber-400">Semantic Clone Sections Detected</p>
            <p className="text-xs text-ink-500 mt-1">
              These section pairs score ≥98% cosine similarity — they may be duplicated boilerplate or copy-pasted clauses:
            </p>
            <ul className="mt-2 space-y-1">
              {sa.semantic_clone_pairs.map(([h1, h2], i) => (
                <li key={i} className="text-xs font-mono">
                  <span className="text-crimson-400">{h1}</span>
                  <span className="text-ink-600 mx-2">↔</span>
                  <span className="text-jade-400">{h2}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* ── Toolbar ────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-2 p-4 rounded-xl bg-ink-900 border border-ink-800">
        {/* Filter buttons */}
        <div className="flex flex-wrap gap-1">
          {(["all","unchanged","modified","added","deleted"] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                filter === f ? "bg-amber-500 text-ink-950" : "bg-ink-800 text-ink-400 hover:bg-ink-700"
              )}
            >
              {f === "all" ? "All" : MATCH_CFG[f].label}
              {f !== "all" && (
                <span className="ml-1.5 opacity-60">{counts[f]}</span>
              )}
            </button>
          ))}
        </div>

        {/* View toggle */}
        <div className="ml-auto flex gap-1">
          <button
            onClick={() => setView("list")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              view === "list" ? "bg-amber-500 text-ink-950" : "bg-ink-800 text-ink-400 hover:bg-ink-700"
            )}
          >
            <List className="w-3.5 h-3.5" /> List
          </button>
          <button
            onClick={() => setView("heatmap")}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              view === "heatmap" ? "bg-amber-500 text-ink-950" : "bg-ink-800 text-ink-400 hover:bg-ink-700"
            )}
          >
            <Grid3x3 className="w-3.5 h-3.5" /> Similarity Matrix
          </button>
        </div>
      </div>

      {/* ── List view ──────────────────────────────────────────────────────── */}
      {view === "list" && (
        <>
          {/* Column header */}
          <div className="hidden md:grid grid-cols-[140px_1fr_1fr_140px_24px] gap-3 px-4 text-xs font-semibold text-ink-700 uppercase tracking-wider">
            <span>Status</span>
            <span>Document A Section</span>
            <span>Document B Section</span>
            <span>Similarity</span>
            <span />
          </div>

          <div className="space-y-2">
            {filtered.length === 0 ? (
              <div className="text-center py-10 text-ink-600 text-sm">
                No {filter === "all" ? "" : MATCH_CFG[filter as MatchType]?.label.toLowerCase()} sections found.
              </div>
            ) : (
              filtered.map(m => <MatchRow key={m.id} match={m} />)
            )}
          </div>
        </>
      )}

      {/* ── Heatmap view ───────────────────────────────────────────────────── */}
      {view === "heatmap" && (
        <div className="p-3 sm:p-5 rounded-2xl bg-ink-900 border border-ink-800 overflow-x-auto">
          <div className="flex items-start justify-between gap-4 mb-4">
            <div>
              <p className="text-sm font-semibold text-ink-200">Section Cosine Similarity Matrix</p>
              <p className="text-xs text-ink-600 mt-0.5">
                Rows = Document A · Columns = Document B · Hover a cell for details
              </p>
            </div>
            <div className="text-xs text-ink-600 font-mono flex-shrink-0">
              {sa.doc1_section_labels.length} × {sa.doc2_section_labels.length} sections
            </div>
          </div>

          {sa.similarity_matrix.length > 0 ? (
            <SimilarityMatrix
              matrix={sa.similarity_matrix}
              rowLabels={sa.doc1_section_labels}
              colLabels={sa.doc2_section_labels}
              maxRows={14}
              maxCols={14}
            />
          ) : (
            <p className="text-xs text-ink-600 italic py-4 text-center">
              Similarity matrix data not available.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
