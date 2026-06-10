"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useDropzone } from "react-dropzone";
import {
  listKbDocuments, uploadKbDocument, deleteKbDocument,
  searchKb, getKbStats,
} from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import type { KbDocument, KbSearchResult, KbStats } from "@/types";
import Link from "next/link";
import {
  GitCompare, Database, Upload, Trash2, Search, Globe,
  Building2, FileText, ChevronRight, Loader2, AlertCircle,
  CheckCircle2, X, BookOpen, User, LogOut, History, Sparkles,
} from "lucide-react";

type Tab = "global" | "personal";

export default function KnowledgeBasePage() {
  const { user, logout, loading: authLoading } = useAuth();
  const [activeTab, setActiveTab]   = useState<Tab>("global");
  const [documents, setDocuments]   = useState<KbDocument[]>([]);
  const [stats, setStats]           = useState<KbStats | null>(null);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState<string | null>(null);

  const [uploadScope, setUploadScope]           = useState<"global" | "personal">("global");
  const [uploadDescription, setUploadDescription] = useState("");
  const [uploading, setUploading]               = useState(false);
  const [uploadProgress, setUploadProgress]     = useState(0);
  const [uploadSuccess, setUploadSuccess]       = useState<string | null>(null);

  const [searchQuery, setSearchQuery]   = useState("");
  const [searchResults, setSearchResults] = useState<KbSearchResult[]>([]);
  const [searching, setSearching]       = useState(false);
  const searchTimer = useRef<NodeJS.Timeout | null>(null);

  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Mobile: toggle upload panel
  const [showUploadPanel, setShowUploadPanel] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [docs, s] = await Promise.all([
        listKbDocuments("all"),
        getKbStats(),
      ]);
      setDocuments(docs);
      setStats(s);
    } catch {
      setError("Failed to load knowledge base documents.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const visibleDocs = documents.filter((d) =>
    activeTab === "global" ? d.scope === "global" : d.scope === "personal"
  );

  const onDrop = useCallback(async (files: File[]) => {
    const file = files[0];
    if (!file) return;
    setUploading(true);
    setUploadProgress(0);
    setUploadSuccess(null);
    setError(null);
    try {
      const res = await uploadKbDocument(
        file, uploadScope, uploadDescription || undefined, setUploadProgress
      );
      setUploadSuccess(
        `"${res.filename}" indexed into ${res.scope === "global" ? "Global" : "Company"} KB — ${res.chunk_count} chunks.`
      );
      setUploadDescription("");
      await loadData();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Upload failed";
      setError(msg);
    } finally {
      setUploading(false);
    }
  }, [uploadScope, uploadDescription, loadData]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"], "text/plain": [".txt"], "text/markdown": [".md"] },
    multiple: false,
    disabled: uploading,
  });

  const handleDelete = async (docId: string) => {
    setDeletingId(docId);
    try {
      await deleteKbDocument(docId);
      await loadData();
    } catch {
      setError("Failed to delete document.");
    } finally {
      setDeletingId(null);
    }
  };

  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!searchQuery.trim() || searchQuery.length < 3) {
      setSearchResults([]);
      return;
    }
    searchTimer.current = setTimeout(async () => {
      setSearching(true);
      try {
        const results = await searchKb(searchQuery, 6);
        setSearchResults(results);
      } catch {
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 600);
  }, [searchQuery]);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-amber-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="grain min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-ink-800 px-4 sm:px-8 py-4 sm:py-5 flex items-center gap-2 sm:gap-4">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-500 flex items-center justify-center">
            <GitCompare className="w-4 h-4 text-ink-950" />
          </div>
          <span className="font-serif text-lg sm:text-xl font-semibold text-ink-100 hidden sm:inline">PolicyLens</span>
        </Link>

        <ChevronRight className="w-4 h-4 text-ink-600" />
        <div className="flex items-center gap-1.5 text-sm text-ink-300">
          <Database className="w-4 h-4 text-amber-500" />
          <span className="hidden xs:inline">Knowledge Base</span>
          <span className="xs:hidden">KB</span>
        </div>

        <div className="ml-auto flex items-center gap-1 sm:gap-3">
          {/* Mobile upload toggle */}
          <button
            onClick={() => setShowUploadPanel(!showUploadPanel)}
            className="flex lg:hidden items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs text-ink-400 hover:text-ink-200 hover:bg-ink-800 transition-all"
          >
            <Upload className="w-3.5 h-3.5" />
          </button>

          <Link
            href="/history"
            className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 rounded-lg text-xs text-ink-400 hover:text-ink-200 hover:bg-ink-800 transition-all"
          >
            <History className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">History</span>
          </Link>

          {user && (
            <div className="flex items-center gap-2 pl-2 sm:pl-3 border-l border-ink-800">
              <div className="hidden sm:flex items-center gap-1.5 text-xs text-ink-500">
                <div className="w-6 h-6 rounded-full bg-amber-500/20 border border-amber-500/30 flex items-center justify-center">
                  <User className="w-3 h-3 text-amber-400" />
                </div>
                <span className="text-ink-400 max-w-[100px] truncate">{user.full_name || user.username}</span>
              </div>
              <button
                onClick={logout}
                className="flex items-center gap-1 px-2 sm:px-2.5 py-1.5 rounded-lg text-xs text-ink-600 hover:text-crimson-400 hover:bg-ink-800 transition-all"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 py-6 sm:py-8">
        {/* Hero */}
        <div className="mb-6 sm:mb-8">
          <h1 className="font-serif text-2xl sm:text-3xl font-bold text-ink-50 mb-2 flex items-center gap-3">
            <Sparkles className="w-6 h-6 sm:w-7 sm:h-7 text-amber-400" />
            RAG Knowledge Base
          </h1>
          <p className="text-ink-400 text-sm leading-relaxed max-w-2xl">
            Upload regulatory standards, company policies, and compliance guidelines to ground
            AI analysis in authoritative reference material. Documents are automatically chunked
            and indexed for semantic retrieval during every comparison.
          </p>
        </div>

        {/* Stats bar */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-6 sm:mb-8">
            <StatCard
              icon={<Globe className="w-4 h-4 text-amber-400" />}
              label="Global KB docs"
              value={documents.filter((d) => d.scope === "global").length}
            />
            <StatCard
              icon={<Building2 className="w-4 h-4 text-jade-400" />}
              label="Company KB docs"
              value={documents.filter((d) => d.scope === "personal").length}
            />
            <StatCard
              icon={<BookOpen className="w-4 h-4 text-sapphire-400" />}
              label="Global chunks"
              value={stats.global_chunks}
            />
            <StatCard
              icon={<FileText className="w-4 h-4 text-ink-400" />}
              label="Company chunks"
              value={stats.personal_chunks}
            />
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8">
          {/* Left: Upload + Search — hidden on mobile unless toggled */}
          <div className={`lg:col-span-1 space-y-5 sm:space-y-6 ${showUploadPanel ? "block" : "hidden lg:block"}`}>
            {/* Upload panel */}
            <div className="rounded-2xl bg-ink-900 border border-ink-700 p-4 sm:p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-ink-200 flex items-center gap-2">
                  <Upload className="w-4 h-4 text-amber-400" /> Add Document
                </h2>
                <button
                  onClick={() => setShowUploadPanel(false)}
                  className="lg:hidden p-1 rounded text-ink-600 hover:text-ink-400"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Scope selector */}
              <div className="flex gap-2 mb-4">
                {(["global", "personal"] as const).map((s) => (
                  <button
                    key={s}
                    onClick={() => setUploadScope(s)}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium transition-all border ${
                      uploadScope === s
                        ? s === "global"
                          ? "bg-amber-500/10 border-amber-500/40 text-amber-400"
                          : "bg-jade-500/10 border-jade-500/40 text-jade-400"
                        : "bg-ink-800 border-ink-700 text-ink-500 hover:text-ink-300"
                    }`}
                  >
                    {s === "global"
                      ? <><Globe className="w-3 h-3" /> Global KB</>
                      : <><Building2 className="w-3 h-3" /> Company KB</>
                    }
                  </button>
                ))}
              </div>

              <input
                type="text"
                placeholder="Optional description…"
                value={uploadDescription}
                onChange={(e) => setUploadDescription(e.target.value)}
                className="w-full mb-3 px-3 py-2 rounded-lg bg-ink-800 border border-ink-700 text-ink-200 text-sm placeholder:text-ink-600 focus:outline-none focus:border-amber-500/50"
              />

              <div
                {...getRootProps()}
                className={`rounded-xl border-2 border-dashed p-5 sm:p-6 text-center cursor-pointer transition-all ${
                  isDragActive
                    ? "border-amber-400 bg-amber-500/5"
                    : uploading
                    ? "border-ink-700 opacity-50 cursor-not-allowed"
                    : "border-ink-700 hover:border-ink-500 hover:bg-ink-800/50"
                }`}
              >
                <input {...getInputProps()} />
                {uploading ? (
                  <div className="flex flex-col items-center gap-2">
                    <Loader2 className="w-6 h-6 text-amber-400 animate-spin" />
                    <p className="text-xs text-ink-400">Indexing… {uploadProgress}%</p>
                    <div className="w-full h-1 rounded-full bg-ink-700 mt-1">
                      <div
                        className="h-1 rounded-full bg-amber-500 transition-all"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  </div>
                ) : (
                  <>
                    <Upload className="w-6 h-6 text-ink-500 mx-auto mb-2" />
                    <p className="text-xs text-ink-400">
                      {isDragActive ? "Drop to index" : "Drop PDF / TXT / MD here"}
                    </p>
                    <p className="text-xs text-ink-600 mt-1">or click to browse · max 30 MB</p>
                  </>
                )}
              </div>

              {uploadSuccess && (
                <div className="mt-3 flex items-start gap-2 p-3 rounded-lg bg-jade-950 border border-jade-800 text-jade-300 text-xs">
                  <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  {uploadSuccess}
                </div>
              )}
            </div>

            {/* Search panel */}
            <div className="rounded-2xl bg-ink-900 border border-ink-700 p-4 sm:p-6">
              <h2 className="font-semibold text-ink-200 mb-4 flex items-center gap-2">
                <Search className="w-4 h-4 text-amber-400" /> Preview Retrieval
              </h2>
              <p className="text-xs text-ink-500 mb-3">
                Test what context the AI would retrieve for any query.
              </p>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-ink-500" />
                <input
                  type="text"
                  placeholder="e.g. GDPR data retention requirements"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-2 rounded-lg bg-ink-800 border border-ink-700 text-ink-200 text-sm placeholder:text-ink-600 focus:outline-none focus:border-amber-500/50"
                />
              </div>

              {searching && (
                <div className="mt-3 flex items-center gap-2 text-xs text-ink-500">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Searching…
                </div>
              )}

              {searchResults.length > 0 && (
                <div className="mt-3 space-y-2">
                  {searchResults.map((r, i) => (
                    <div key={i} className="p-3 rounded-lg bg-ink-800 border border-ink-700">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-ink-300 truncate max-w-[70%]">
                          {r.source_doc_name}
                        </span>
                        <span className={`text-xs px-1.5 py-0.5 rounded-full border ${
                          r.scope === "global"
                            ? "text-amber-400 bg-amber-500/10 border-amber-500/20"
                            : "text-jade-400 bg-jade-500/10 border-jade-500/20"
                        }`}>
                          {r.scope === "global" ? "Global" : "Company"}
                        </span>
                      </div>
                      <p className="text-xs text-ink-500 line-clamp-2">{r.excerpt}</p>
                      <p className="text-xs text-ink-600 mt-1">Score: {(r.score * 100).toFixed(0)}%</p>
                    </div>
                  ))}
                </div>
              )}

              {searchQuery.length >= 3 && !searching && searchResults.length === 0 && (
                <p className="mt-3 text-xs text-ink-600">No matching chunks found.</p>
              )}
            </div>
          </div>

          {/* Right: Document list */}
          <div className="lg:col-span-2">
            {/* Error */}
            {error && (
              <div className="mb-4 flex items-start gap-2 p-4 rounded-xl bg-crimson-950 border border-crimson-800 text-crimson-300 text-sm">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <div className="flex-1">{error}</div>
                <button onClick={() => setError(null)}><X className="w-4 h-4" /></button>
              </div>
            )}

            {/* Mobile: Add Document button when panel hidden */}
            {!showUploadPanel && (
              <button
                onClick={() => setShowUploadPanel(true)}
                className="lg:hidden w-full mb-4 flex items-center justify-center gap-2 py-2.5 rounded-xl border border-dashed border-ink-700 text-sm text-ink-400 hover:border-amber-500/40 hover:text-ink-200 transition-all"
              >
                <Upload className="w-4 h-4" /> Add Document
              </button>
            )}

            {/* Tabs */}
            <div className="flex gap-2 mb-5 sm:mb-6 overflow-x-auto">
              {(["global", "personal"] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-medium transition-all border whitespace-nowrap ${
                    activeTab === tab
                      ? tab === "global"
                        ? "bg-amber-500/10 border-amber-500/30 text-amber-400"
                        : "bg-jade-500/10 border-jade-500/30 text-jade-400"
                      : "bg-ink-900 border-ink-700 text-ink-500 hover:text-ink-300"
                  }`}
                >
                  {tab === "global"
                    ? <><Globe className="w-3.5 h-3.5" /> Global Regulatory KB</>
                    : <><Building2 className="w-3.5 h-3.5" /> My Company KB</>
                  }
                  <span className="ml-1 text-xs px-1.5 py-0.5 rounded-full bg-ink-800 text-ink-500">
                    {documents.filter((d) => d.scope === tab).length}
                  </span>
                </button>
              ))}
            </div>

            {/* Scope description */}
            <div className={`mb-4 sm:mb-5 p-3 sm:p-4 rounded-xl border text-xs sm:text-sm ${
              activeTab === "global"
                ? "bg-amber-500/5 border-amber-500/20 text-amber-200/70"
                : "bg-jade-500/5 border-jade-500/20 text-jade-200/70"
            }`}>
              {activeTab === "global" ? (
                <>
                  <strong className="text-amber-400">Global Regulatory KB</strong> — Shared across all users.
                  Upload GDPR, HIPAA, SOX, ISO 27001, and other regulatory standards here.
                  Every comparison is grounded against this knowledge base.
                </>
              ) : (
                <>
                  <strong className="text-jade-400">Company KB</strong> — Private to your account.
                  Upload internal policies, procedures, and company-specific compliance documents.
                  Combined with the Global KB during your analyses.
                </>
              )}
            </div>

            {/* Document list */}
            {loading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-6 h-6 text-amber-500 animate-spin" />
              </div>
            ) : visibleDocs.length === 0 ? (
              <EmptyState
                scope={activeTab}
                onUploadClick={() => {
                  setUploadScope(activeTab);
                  setShowUploadPanel(true);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
              />
            ) : (
              <div className="space-y-3">
                {visibleDocs.map((doc) => (
                  <DocumentRow
                    key={doc.id}
                    doc={doc}
                    deleting={deletingId === doc.id}
                    onDelete={() => handleDelete(doc.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

// Sub-components

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="rounded-xl bg-ink-900 border border-ink-700 px-3 sm:px-4 py-3">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-ink-500 truncate">{label}</span>
      </div>
      <p className="text-xl sm:text-2xl font-bold text-ink-100">{value.toLocaleString()}</p>
    </div>
  );
}

function DocumentRow({
  doc, deleting, onDelete,
}: { doc: KbDocument; deleting: boolean; onDelete: () => void }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-xl bg-ink-900 border border-ink-700 hover:border-ink-600 transition-all">
      <div className="flex items-center gap-3 sm:gap-4 px-3 sm:px-4 py-3">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
          doc.scope === "global" ? "bg-amber-500/10" : "bg-jade-500/10"
        }`}>
          <FileText className={`w-4 h-4 ${doc.scope === "global" ? "text-amber-400" : "text-jade-400"}`} />
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-ink-200 truncate">{doc.filename}</p>
          <p className="text-xs text-ink-500 truncate">
            {doc.chunk_count} chunks · {Math.round(doc.char_count / 1000)}k chars ·{" "}
            <span className="hidden sm:inline">Added by <span className="text-ink-400">{doc.uploaded_by}</span> · </span>
            {new Date(doc.created_at).toLocaleDateString()}
          </p>
          {doc.description && (
            <p className="text-xs text-ink-600 mt-0.5 truncate">{doc.description}</p>
          )}
        </div>

        <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="p-1.5 rounded-lg text-ink-500 hover:text-ink-300 hover:bg-ink-800 transition-all"
            title="View details"
          >
            <ChevronRight className={`w-4 h-4 transition-transform ${expanded ? "rotate-90" : ""}`} />
          </button>
          <button
            onClick={onDelete}
            disabled={deleting}
            className="p-1.5 rounded-lg text-ink-600 hover:text-crimson-400 hover:bg-ink-800 transition-all disabled:opacity-40"
            title="Delete"
          >
            {deleting
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <Trash2 className="w-4 h-4" />
            }
          </button>
        </div>
      </div>

      {expanded && (
        <div className="px-3 sm:px-4 pb-3 border-t border-ink-800">
          <div className="pt-3 grid grid-cols-2 gap-2 text-xs">
            <div>
              <p className="text-ink-600 mb-0.5">Document ID</p>
              <p className="font-mono text-ink-400 truncate">{doc.id}</p>
            </div>
            <div>
              <p className="text-ink-600 mb-0.5">Scope</p>
              <p className="text-ink-400 capitalize">{doc.scope === "global" ? "Global (all users)" : "Personal (you only)"}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function EmptyState({ scope, onUploadClick }: { scope: Tab; onUploadClick: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 sm:py-16 text-center">
      <div className={`w-12 h-12 sm:w-14 sm:h-14 rounded-2xl flex items-center justify-center mb-4 ${
        scope === "global" ? "bg-amber-500/10" : "bg-jade-500/10"
      }`}>
        {scope === "global"
          ? <Globe className="w-6 h-6 sm:w-7 sm:h-7 text-amber-500/60" />
          : <Building2 className="w-6 h-6 sm:w-7 sm:h-7 text-jade-500/60" />
        }
      </div>
      <p className="text-ink-300 font-medium mb-1">
        {scope === "global" ? "No regulatory documents yet" : "No company documents yet"}
      </p>
      <p className="text-ink-600 text-sm mb-5 max-w-xs px-4">
        {scope === "global"
          ? "Add GDPR, HIPAA, SOX, ISO 27001 or other standards to ground every analysis."
          : "Upload internal policies to give the AI company-specific compliance context."
        }
      </p>
      <button
        onClick={onUploadClick}
        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
          scope === "global"
            ? "bg-amber-500 hover:bg-amber-400 text-ink-950"
            : "bg-jade-600 hover:bg-jade-500 text-white"
        }`}
      >
        <Upload className="w-4 h-4" />
        Upload your first document
      </button>
    </div>
  );
}
