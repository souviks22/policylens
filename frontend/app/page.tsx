"use client";

import { useState, useCallback } from "react";
import { uploadDocument, analyzeDocuments } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import type { ComparisonResult, UploadedDoc } from "@/types";
import FileDropZone from "@/components/FileDropZone";
import ComparisonDashboard from "@/components/ComparisonDashboard";
import AnalyzingOverlay from "@/components/AnalyzingOverlay";
import { FileText, GitCompare, Shield, Zap, History, LogOut, User, Loader2 } from "lucide-react";
import Link from "next/link";

type Step = "upload" | "analyzing" | "results";

export default function Home() {
  const { user, logout, loading: authLoading } = useAuth();
  const [step, setStep] = useState<Step>("upload");
  const [doc1, setDoc1] = useState<UploadedDoc | null>(null);
  const [doc2, setDoc2] = useState<UploadedDoc | null>(null);
  const [uploading1, setUploading1] = useState(false);
  const [uploading2, setUploading2] = useState(false);
  const [progress1, setProgress1] = useState(0);
  const [progress2, setProgress2] = useState(0);
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDrop1 = useCallback(async (file: File) => {
    setUploading1(true);
    setProgress1(0);
    setError(null);
    try {
      const res = await uploadDocument(file, setProgress1);
      setDoc1({ file_id: res.file_id, filename: res.filename, pages: res.pages, word_count: res.word_count });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Upload failed";
      setError(`Document 1: ${msg}`);
    } finally {
      setUploading1(false);
    }
  }, []);

  const handleDrop2 = useCallback(async (file: File) => {
    setUploading2(true);
    setProgress2(0);
    setError(null);
    try {
      const res = await uploadDocument(file, setProgress2);
      setDoc2({ file_id: res.file_id, filename: res.filename, pages: res.pages, word_count: res.word_count });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Upload failed";
      setError(`Document 2: ${msg}`);
    } finally {
      setUploading2(false);
    }
  }, []);

  const handleAnalyze = async () => {
    if (!doc1 || !doc2) return;
    setStep("analyzing");
    setError(null);
    try {
      const res = await analyzeDocuments(doc1.file_id, doc2.file_id);
      setResult(res);
      setStep("results");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Analysis failed";
      setError(msg);
      setStep("upload");
    }
  };

  const handleReset = () => {
    setStep("upload");
    setDoc1(null);
    setDoc2(null);
    setResult(null);
    setError(null);
    setProgress1(0);
    setProgress2(0);
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-amber-500 animate-spin" />
      </div>
    );
  }

  if (step === "analyzing") {
    return <AnalyzingOverlay doc1={doc1!} doc2={doc2!} />;
  }

  if (step === "results" && result) {
    return <ComparisonDashboard result={result} onReset={handleReset} />;
  }

  return (
    <div className="grain min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-ink-800 px-8 py-5 flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-500 flex items-center justify-center">
            <GitCompare className="w-4 h-4 text-ink-950" />
          </div>
          <span className="font-serif text-xl font-semibold text-ink-100">PolicyLens</span>
        </div>

        <div className="ml-auto flex items-center gap-3">
          <Link
            href="/history"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-ink-400 hover:text-ink-200 hover:bg-ink-800 transition-all"
          >
            <History className="w-3.5 h-3.5" /> History
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
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs text-ink-600 hover:text-crimson-400 hover:bg-ink-800 transition-all"
                title="Sign out"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-4 py-16">
        {/* Hero */}
        <div className="text-center mb-14 max-w-2xl animate-slide-up">
          <h1 className="font-serif text-5xl font-bold text-ink-50 mb-4 leading-tight">
            Policy Document<br />
            <span className="text-amber-400 italic">Intelligence</span>
          </h1>
          <p className="text-ink-400 text-lg leading-relaxed">
            Upload two versions of a policy document and get AI-powered semantic comparison,
            compliance impact analysis, and an executive change report — in seconds.
          </p>
        </div>

        {/* Feature pills */}
        <div className="flex flex-wrap gap-3 justify-center mb-12">
          {[
            { icon: FileText, label: "PDF Text Extraction" },
            { icon: GitCompare, label: "Semantic Diff" },
            { icon: Shield, label: "Compliance Analysis" },
            { icon: Zap, label: "AI-Powered Insights" },
          ].map(({ icon: Icon, label }) => (
            <div key={label} className="flex items-center gap-2 px-4 py-2 rounded-full bg-ink-900 border border-ink-700 text-ink-400 text-sm">
              <Icon className="w-3.5 h-3.5 text-amber-500" />
              {label}
            </div>
          ))}
        </div>

        {/* Upload Area */}
        <div className="w-full max-w-4xl">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-5 h-5 rounded-full bg-ink-700 flex items-center justify-center text-xs font-mono text-ink-300">A</div>
                <span className="text-sm font-medium text-ink-300">Legacy / Original Document</span>
              </div>
              <FileDropZone
                label="Drop legacy policy PDF here"
                onFile={handleDrop1}
                uploaded={doc1}
                loading={uploading1}
                progress={progress1}
                accent="crimson"
              />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-5 h-5 rounded-full bg-ink-700 flex items-center justify-center text-xs font-mono text-ink-300">B</div>
                <span className="text-sm font-medium text-ink-300">Updated / Modernized Document</span>
              </div>
              <FileDropZone
                label="Drop updated policy PDF here"
                onFile={handleDrop2}
                uploaded={doc2}
                loading={uploading2}
                progress={progress2}
                accent="jade"
              />
            </div>
          </div>

          {error && (
            <div className="mt-4 p-4 rounded-xl bg-crimson-950 border border-crimson-800 text-crimson-300 text-sm">
              ⚠ {error}
            </div>
          )}

          <button
            onClick={handleAnalyze}
            disabled={!doc1 || !doc2 || uploading1 || uploading2}
            className="
              mt-6 w-full py-4 rounded-xl font-semibold text-base
              transition-all duration-200
              disabled:opacity-30 disabled:cursor-not-allowed
              bg-amber-500 hover:bg-amber-400 text-ink-950
              flex items-center justify-center gap-2.5
              shadow-lg shadow-amber-500/10
            "
          >
            <Zap className="w-4 h-4" />
            Analyze Documents
          </button>

          <p className="text-center text-xs text-ink-600 mt-4">
            PDF files only · Max 50 MB each · Analysis takes 30-45 seconds
          </p>
        </div>
      </main>
    </div>
  );
}
