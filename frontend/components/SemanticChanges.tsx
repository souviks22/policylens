"use client";

import { useState, useEffect } from "react";
import type { ComparisonResult, ChangeType, ImpactLevel, SemanticChange } from "@/types";
import ImpactBadge from "./ImpactBadge";
import ChangeBadge from "./ChangeBadge";
import AnnotationsPanel from "./AnnotationsPanel";
import { getAnnotations } from "@/lib/api";
import {
  ChevronDown, ChevronUp, Lightbulb, Shield,
  Building2, Globe, MessageSquare,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Props { result: ComparisonResult; }
type TypeFilter   = "all" | ChangeType;
type ImpactFilter = "all" | ImpactLevel;

// ── ChangeCard ─────────────────────────────────────────────────────────────────

function ChangeCard({
  change,
  comparisonId,
  annotationCount,
}: {
  change: SemanticChange;
  comparisonId: string;
  annotationCount: number;
}) {
  const [expanded, setExpanded]             = useState(false);
  const [showAnnotations, setShowAnnotations] = useState(false);

  return (
    <div className={cn(
      "rounded-2xl border transition-all duration-200",
      expanded ? "bg-ink-900 border-ink-700" : "bg-ink-900 border-ink-800 hover:border-ink-700"
    )}>
      {/* ── Collapsed row ───────────────────────────────────────────────── */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-5"
      >
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-0.5">
            <ChangeBadge type={change.change_type} size="sm" />
          </div>

          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-ink-100">{change.summary}</p>
            {change.section && (
              <p className="text-xs text-ink-600 mt-0.5">§ {change.section}</p>
            )}
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Annotation count badge — visible even when collapsed */}
            {annotationCount > 0 && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-mono">
                <MessageSquare className="w-3 h-3" />
                {annotationCount}
              </span>
            )}
            <ImpactBadge level={change.impact_level} size="sm" />
            {expanded
              ? <ChevronUp className="w-4 h-4 text-ink-500" />
              : <ChevronDown className="w-4 h-4 text-ink-500" />}
          </div>
        </div>
      </button>

      {/* ── Expanded content ─────────────────────────────────────────────── */}
      {expanded && (
        <div className="px-5 pb-5 space-y-4 border-t border-ink-800 pt-4 tab-content">

          {/* Before / After */}
          {(change.old_content || change.new_content) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {change.old_content && (
                <div className="p-3 rounded-xl bg-crimson-950/40 border border-crimson-800/40">
                  <p className="text-xs font-semibold text-crimson-400 mb-2 uppercase tracking-wider">Before</p>
                  <p className="text-xs text-ink-400 leading-relaxed font-mono whitespace-pre-wrap">
                    {change.old_content}
                  </p>
                </div>
              )}
              {change.new_content && (
                <div className="p-3 rounded-xl bg-jade-950/40 border border-jade-800/40">
                  <p className="text-xs font-semibold text-jade-400 mb-2 uppercase tracking-wider">After</p>
                  <p className="text-xs text-ink-400 leading-relaxed font-mono whitespace-pre-wrap">
                    {change.new_content}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Analysis */}
          {change.explanation && (
            <div className="p-3 rounded-xl bg-ink-950 border border-ink-800">
              <p className="text-xs font-semibold text-ink-400 mb-2 flex items-center gap-1.5">
                <Lightbulb className="w-3.5 h-3.5 text-amber-500" /> Analysis
              </p>
              <p className="text-sm text-ink-300 leading-relaxed">{change.explanation}</p>
            </div>
          )}

          {/* Impact grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              { icon: Building2, label: "Business Impact",    value: change.business_impact,    color: "text-amber-400" },
              { icon: Shield,    label: "Compliance Impact",  value: change.compliance_impact,  color: "text-sapphire-400" },
              { icon: Globe,     label: "Regulatory Impact",  value: change.regulatory_impact,  color: "text-jade-400" },
            ].map(({ icon: Icon, label, value, color }) =>
              value ? (
                <div key={label} className="p-3 rounded-xl bg-ink-950 border border-ink-800">
                  <p className={cn("text-xs font-semibold mb-1.5 flex items-center gap-1.5", color)}>
                    <Icon className="w-3.5 h-3.5" />{label}
                  </p>
                  <p className="text-xs text-ink-400 leading-relaxed">{value}</p>
                </div>
              ) : null
            )}
          </div>

          {/* Recommendations */}
          {change.recommendations.length > 0 && (
            <div className="p-3 rounded-xl bg-amber-950/20 border border-amber-800/30">
              <p className="text-xs font-semibold text-amber-400 mb-2 uppercase tracking-wider">
                Recommended Actions
              </p>
              <ul className="space-y-1.5">
                {change.recommendations.map((rec, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-ink-400">
                    <span className="text-amber-500 font-bold flex-shrink-0 mt-px">{i + 1}.</span>
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Annotations toggle */}
          <div>
            <button
              onClick={() => setShowAnnotations(!showAnnotations)}
              className={cn(
                "flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg transition-all",
                showAnnotations
                  ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                  : "bg-ink-800 text-ink-400 hover:bg-ink-700"
              )}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              {showAnnotations ? "Hide comments" : (
                annotationCount > 0 ? `${annotationCount} comment${annotationCount !== 1 ? "s" : ""}` : "Add comment"
              )}
            </button>

            {showAnnotations && (
              <div className="mt-3">
                <AnnotationsPanel
                  comparisonId={comparisonId}
                  changeId={change.id}
                  changeType="semantic"
                  floating={false}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── SemanticChanges ────────────────────────────────────────────────────────────

export default function SemanticChanges({ result }: Props) {
  const [typeFilter,   setTypeFilter]   = useState<TypeFilter>("all");
  const [impactFilter, setImpactFilter] = useState<ImpactFilter>("all");
  // Map of change_id → annotation count
  const [annCounts, setAnnCounts]       = useState<Record<string, number>>({});

  // Fetch all annotations for this comparison once, build a count map
  useEffect(() => {
    getAnnotations(result.comparison_id)
      .then(all => {
        const counts: Record<string, number> = {};
        all.forEach(a => {
          if (!a.resolved) counts[a.change_id] = (counts[a.change_id] ?? 0) + 1;
        });
        setAnnCounts(counts);
      })
      .catch(() => { /* non-critical */ });
  }, [result.comparison_id]);

  const filtered = result.semantic_changes.filter(c => {
    const typeMatch   = typeFilter   === "all" || c.change_type  === typeFilter;
    const impactMatch = impactFilter === "all" || c.impact_level === impactFilter;
    return typeMatch && impactMatch;
  });

  const totalAnnotations = Object.values(annCounts).reduce((s, n) => s + n, 0);

  return (
    <div className="space-y-4 tab-content">

      {/* Filter toolbar */}
      <div className="flex flex-wrap items-center gap-2 p-4 rounded-xl bg-ink-900 border border-ink-800">
        <div className="flex flex-wrap gap-1.5">
          {(["all","addition","deletion","modification","regulatory_update"] as TypeFilter[]).map(f => (
            <button
              key={f}
              onClick={() => setTypeFilter(f)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                typeFilter === f ? "bg-amber-500 text-ink-950" : "bg-ink-800 text-ink-400 hover:bg-ink-700"
              )}
            >
              {f === "all" ? "All Types"
                : f === "regulatory_update" ? "Regulatory"
                : f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        <div className="w-px bg-ink-700 mx-1 self-stretch" />

        <div className="flex flex-wrap gap-1.5">
          {(["all","high","medium","low"] as ImpactFilter[]).map(f => (
            <button
              key={f}
              onClick={() => setImpactFilter(f)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                impactFilter === f ? "bg-ink-100 text-ink-900" : "bg-ink-800 text-ink-400 hover:bg-ink-700"
              )}
            >
              {f === "all" ? "All Impact" : f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-3 text-xs text-ink-600">
          {totalAnnotations > 0 && (
            <span className="flex items-center gap-1 text-amber-500/70">
              <MessageSquare className="w-3 h-3" />
              {totalAnnotations} comment{totalAnnotations !== 1 ? "s" : ""}
            </span>
          )}
          <span>{filtered.length} / {result.semantic_changes.length}</span>
        </div>
      </div>

      {/* Change cards */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 text-ink-600 text-sm">
          No changes match the current filters.
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(c => (
            <ChangeCard
              key={c.id}
              change={c}
              comparisonId={result.comparison_id}
              annotationCount={annCounts[c.id] ?? 0}
            />
          ))}
        </div>
      )}
    </div>
  );
}
