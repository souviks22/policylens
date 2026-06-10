"use client";

import { useState } from "react";
import type { ComparisonResult } from "@/types";
import ExecutiveSummary from "./ExecutiveSummary";
import SemanticChanges from "./SemanticChanges";
import DiffViewer from "./DiffViewer";
import SectionAnalysisTab from "./SectionAnalysis";
import ImpactBadge from "./ImpactBadge";
import ComparisonChat from "./ComparisonChat";
import RagContextPanel from "./RagContextPanel";

import { cn } from "@/lib/utils";
import { exportComparison } from "@/lib/api";
import {
  GitCompare, ArrowLeft, BarChart3, Diff, Brain,
  Layers, History, FileDown, Loader2,
} from "lucide-react";
import Link from "next/link";

type Tab = "summary" | "semantic" | "diff" | "sections";
type ExportFmt = "pdf" | "docx";

interface Props {
  result: ComparisonResult;
  onReset: () => void;
}

const TABS: { id: Tab; label: string; icon: React.FC<{ className?: string }> }[] = [
  { id: "summary", label: "Executive Summary", icon: BarChart3 },
  { id: "semantic", label: "Semantic Changes", icon: Brain },
  { id: "sections", label: "Section Analysis", icon: Layers },
  { id: "diff", label: "Text Diff", icon: Diff },
];

export default function ComparisonDashboard({ result, onReset }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("summary");
  const [exporting, setExporting] = useState<ExportFmt | null>(null);
  const [exportErr, setExportErr] = useState<string | null>(null);

  const sim = Math.round((result.text_similarity_ratio ?? 0) * 100);
  const structural = result.section_analysis
    ? Math.round(result.section_analysis.overall_structural_similarity * 100)
    : null;

  const handleExport = async (fmt: ExportFmt) => {
    setExporting(fmt);
    setExportErr(null);
    try {
      await exportComparison(result.comparison_id, fmt);
    } catch (e) {
      setExportErr(e instanceof Error ? e.message : "Export failed");
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="grain min-h-screen flex flex-col">

      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-ink-800 bg-ink-950/90 backdrop-blur-md px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center gap-3 flex-wrap">

          <Link href="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-500 flex items-center justify-center">
              <GitCompare className="w-4 h-4 text-ink-950" />
            </div>
            <span className="font-serif text-xl font-semibold text-ink-100">PolicyLens</span>
          </Link>

          <div className="hidden md:flex items-center gap-2 text-xs font-mono text-ink-600">
            <span className="px-2 py-0.5 rounded bg-ink-900 border border-ink-800 text-ink-400 max-w-[170px] truncate">
              {result.doc1_name}
            </span>
            <GitCompare className="w-3 h-3" />
            <span className="px-2 py-0.5 rounded bg-ink-900 border border-ink-800 text-ink-400 max-w-[170px] truncate">
              {result.doc2_name}
            </span>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <ImpactBadge level={result.summary.overall_impact_level} />

            {/* Export */}
            {(["pdf", "docx"] as ExportFmt[]).map((fmt) => (
              <button
                key={fmt}
                onClick={() => handleExport(fmt)}
                disabled={!!exporting}
                title={`Download ${fmt.toUpperCase()} report`}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-ink-800 text-ink-300 hover:bg-ink-700 hover:text-ink-100 disabled:opacity-40 transition-all"
              >
                {exporting === fmt
                  ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  : <FileDown className="w-3.5 h-3.5" />}
                {fmt.toUpperCase()}
              </button>
            ))}

            <Link
              href="/history"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-ink-400 hover:text-ink-200 hover:bg-ink-800 transition-all"
            >
              <History className="w-3.5 h-3.5" /> History
            </Link>
            <button
              onClick={onReset}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-ink-400 hover:text-ink-200 hover:bg-ink-800 transition-all"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back
            </button>
          </div>
        </div>

        {/* Export error */}
        {exportErr && (
          <div className="max-w-7xl mx-auto mt-2 px-1">
            <p className="text-xs text-crimson-400">⚠ {exportErr}</p>
          </div>
        )}
      </header>

      {/* Quick stats */}
      <div className="border-b border-ink-800 bg-ink-900/40">
        <div className="max-w-7xl mx-auto px-6 py-3 flex flex-wrap items-center gap-x-6 gap-y-1">
          {[
            { label: "Changes", value: result.summary.total_changes, color: "text-ink-100" },
            { label: "Additions", value: result.summary.additions, color: "text-jade-400" },
            { label: "Deletions", value: result.summary.deletions, color: "text-crimson-400" },
            { label: "Modified", value: result.summary.modifications, color: "text-amber-400" },
            { label: "Regulatory", value: result.summary.regulatory_updates, color: "text-sapphire-400" },
          ].map((s) => (
            <div key={s.label} className="flex items-baseline gap-1.5">
              <span className={cn("text-lg font-bold font-mono", s.color)}>{s.value}</span>
              <span className="text-xs text-ink-600">{s.label}</span>
            </div>
          ))}
          <div className="ml-auto flex items-center gap-4 text-xs text-ink-600">
            <span>Text <span className="text-ink-400 font-mono">{sim}%</span></span>
            {structural !== null && (
              <span>Structural <span className="text-ink-400 font-mono">{structural}%</span></span>
            )}
            <span className="font-mono text-ink-700">{result.comparison_id.slice(0, 8)}</span>
          </div>
        </div>
      </div>

      {/* Tab bar */}
      <div className="border-b border-ink-800 bg-ink-950">
        <div className="max-w-7xl mx-auto px-6 flex">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={cn(
                "flex items-center gap-2 px-5 py-4 text-sm font-medium transition-all border-b-2 -mb-px",
                activeTab === id
                  ? "border-amber-500 text-amber-400"
                  : "border-transparent text-ink-500 hover:text-ink-300 hover:border-ink-700"
              )}
            >
              <Icon className="w-4 h-4" />{label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <main className="flex-1 px-6 py-8">
        <div className="max-w-7xl mx-auto">
          {activeTab === "summary" && <ExecutiveSummary result={result} />}
          {activeTab === "semantic" && <SemanticChanges result={result} />}
          {activeTab === "sections" && <SectionAnalysisTab result={result} />}
          {activeTab === "diff" && <DiffViewer result={result} />}
          
          {/* RAG context banner — always visible at the bottom */}
          <RagContextPanel ragContext={result.rag_context} />
        </div>
      </main>

      {/* Floating chat — always accessible regardless of active tab */}
      <ComparisonChat
        comparisonId={result.comparison_id}
        doc1Name={result.doc1_name}
        doc2Name={result.doc2_name}
      />
    </div>
  );
}
