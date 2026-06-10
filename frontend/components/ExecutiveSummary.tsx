"use client";

import { useState } from "react";
import type { ComparisonResult } from "@/types";
import ImpactBadge from "./ImpactBadge";
import { AlertTriangle, CheckCircle2, FileText, TrendingUp } from "lucide-react";

interface Props {
  result: ComparisonResult;
}

const SUMMARY_LIMIT = 600; // Character limit for executive summary preview

export default function ExecutiveSummary({ result }: Props) {
  const { summary, doc1_stats, doc2_stats } = result;
  const [showMore, setShowMore] = useState(false);

  const statCards = [
    { label: "Total Changes", value: summary.total_changes, sub: "detected" },
    { label: "Additions", value: summary.additions, sub: "new content", color: "text-jade-400" },
    { label: "Deletions", value: summary.deletions, sub: "removed", color: "text-crimson-400" },
    { label: "Modifications", value: summary.modifications, sub: "altered", color: "text-amber-400" },
    { label: "Regulatory", value: summary.regulatory_updates, sub: "updates", color: "text-sapphire-400" },
  ];

  return (
    <div className="space-y-4 sm:space-y-6 tab-content">
      {/* Overall impact header */}
      <div className="p-4 sm:p-6 rounded-2xl bg-ink-900 border border-ink-800">
        <div className="flex items-start justify-between gap-3 sm:gap-4 mb-4">
          <div>
            <h3 className="font-serif text-lg sm:text-xl font-semibold text-ink-100 mb-1">Executive Summary</h3>
            <p className="text-sm text-ink-500">Automated compliance intelligence report</p>
          </div>
          <ImpactBadge level={summary.overall_impact_level} />
        </div>
        <p className="text-ink-300 text-sm leading-relaxed whitespace-pre-line">
          {summary.executive_summary.length > SUMMARY_LIMIT && !showMore
            ? `${summary.executive_summary.substring(0, SUMMARY_LIMIT)}...`
            : summary.executive_summary}
        </p>
        {summary.executive_summary.length > SUMMARY_LIMIT && (
          <button
            onClick={() => setShowMore(!showMore)}
            className="text-xs text-amber-400 hover:text-amber-300 focus:outline-none"
          >
            {showMore ? "Show Less" : "Show More"}
          </button>
        )}
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 sm:gap-3">
        {statCards.map((s) => (
          <div key={s.label} className="p-3 sm:p-4 rounded-xl bg-ink-900 border border-ink-800 text-center">
            <div className={`text-xl sm:text-2xl font-bold font-mono ${s.color ?? "text-ink-100"}`}>
              {s.value}
            </div>
            <div className="text-xs font-medium text-ink-400 mt-0.5">{s.label}</div>
            <div className="text-xs text-ink-600 hidden sm:block">{s.sub}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5">
        {/* Document stats */}
        <div className="p-4 sm:p-5 rounded-2xl bg-ink-900 border border-ink-800">
          <h4 className="text-sm font-semibold text-ink-300 mb-4 flex items-center gap-2">
            <FileText className="w-4 h-4 text-ink-500" /> Document Statistics
          </h4>
          <div className="space-y-3">
            {[
              { label: "Document A (Legacy)", stats: doc1_stats },
              { label: "Document B (Updated)", stats: doc2_stats },
            ].map(({ label, stats }) => (
              <div key={label} className="p-3 rounded-xl bg-ink-950 border border-ink-800">
                <p className="text-xs font-medium text-ink-400 mb-2">{label}</p>
                <div className="grid grid-cols-3 gap-2 text-center">
                  {[
                    { k: "Pages", v: stats.total_pages },
                    { k: "Words", v: stats.total_words.toLocaleString() },
                    { k: "Sections", v: stats.sections_detected.length },
                  ].map(({ k, v }) => (
                    <div key={k}>
                      <div className="text-sm font-bold text-ink-100 font-mono">{v}</div>
                      <div className="text-xs text-ink-600">{k}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Key changes */}
        {summary.key_changes.length > 0 && (
          <div className="p-4 sm:p-5 rounded-2xl bg-ink-900 border border-ink-800">
            <h4 className="text-sm font-semibold text-ink-300 mb-4 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-ink-500" /> Key Changes
            </h4>
            <ul className="space-y-2">
              {summary.key_changes.map((change, i) => (
                <li key={i} className="flex items-start gap-2.5 text-sm">
                  <span className="w-5 h-5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs flex items-center justify-center flex-shrink-0 mt-0.5 font-mono">
                    {i + 1}
                  </span>
                  <span className="text-ink-300">{change}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-5">
        {/* Risk areas */}
        {summary.risk_areas.length > 0 && (
          <div className="p-4 sm:p-5 rounded-2xl bg-ink-900 border border-ink-800">
            <h4 className="text-sm font-semibold text-crimson-400 mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" /> Risk Areas
            </h4>
            <ul className="space-y-2">
              {summary.risk_areas.map((area, i) => (
                <li key={i} className="flex items-start gap-2.5 text-sm">
                  <span className="w-1.5 h-1.5 rounded-full bg-crimson-500 flex-shrink-0 mt-1.5" />
                  <span className="text-ink-400">{area}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Compliance flags */}
        {summary.compliance_flags.length > 0 && (
          <div className="p-4 sm:p-5 rounded-2xl bg-ink-900 border border-ink-800">
            <h4 className="text-sm font-semibold text-sapphire-400 mb-4 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" /> Compliance Flags
            </h4>
            <ul className="space-y-2">
              {summary.compliance_flags.map((flag, i) => (
                <li key={i} className="flex items-start gap-2.5 text-sm">
                  <span className="w-1.5 h-1.5 rounded-full bg-sapphire-400 flex-shrink-0 mt-1.5" />
                  <span className="text-ink-400">{flag}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
