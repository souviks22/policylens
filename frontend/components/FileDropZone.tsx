"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, CheckCircle, FileText, Loader2 } from "lucide-react";
import { cn, formatNumber } from "@/lib/utils";
import type { UploadedDoc } from "@/types";

interface Props {
  label: string;
  onFile: (file: File) => void;
  uploaded: UploadedDoc | null;
  loading: boolean;
  progress: number;
  accent: "crimson" | "jade";
}

const accentMap = {
  crimson: {
    border: "border-crimson-600",
    bg: "bg-crimson-950/40",
    text: "text-crimson-400",
    ring: "ring-crimson-500/30",
    hover: "hover:border-crimson-500 hover:bg-crimson-950/60",
    bar: "bg-crimson-500",
    check: "text-crimson-400",
  },
  jade: {
    border: "border-jade-600",
    bg: "bg-jade-950/40",
    text: "text-jade-400",
    ring: "ring-jade-500/30",
    hover: "hover:border-jade-500 hover:bg-jade-950/60",
    bar: "bg-jade-500",
    check: "text-jade-400",
  },
};

export default function FileDropZone({ label, onFile, uploaded, loading, progress, accent }: Props) {
  const colors = accentMap[accent];

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles[0]) onFile(acceptedFiles[0]);
  }, [onFile]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
    disabled: loading,
  });

  if (uploaded) {
    return (
      <div className={cn(
        "rounded-xl border-2 p-6 transition-all",
        colors.border, colors.bg,
        "animate-fade-in"
      )}>
        <div className="flex items-start gap-3">
          <CheckCircle className={cn("w-5 h-5 mt-0.5 flex-shrink-0", colors.check)} />
          <div className="flex-1 min-w-0">
            <p className="font-medium text-ink-100 text-sm truncate">{uploaded.filename}</p>
            <div className="flex gap-4 mt-1.5 text-xs text-ink-500">
              <span>{uploaded.pages} page{uploaded.pages !== 1 ? "s" : ""}</span>
              <span>{formatNumber(uploaded.word_count)} words</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="rounded-xl border-2 border-ink-700 bg-ink-900 p-6 animate-fade-in">
        <div className="flex items-center gap-3 mb-4">
          <Loader2 className="w-5 h-5 text-amber-500 animate-spin" />
          <span className="text-sm text-ink-300">Processing PDF…</span>
          <span className="ml-auto text-xs font-mono text-ink-500">{progress}%</span>
        </div>
        <div className="h-1.5 rounded-full bg-ink-800 overflow-hidden">
          <div
            className={cn("h-full rounded-full transition-all duration-300", colors.bar)}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={cn(
        "rounded-xl border-2 border-dashed p-8 text-center cursor-pointer",
        "transition-all duration-200",
        "border-ink-700 bg-ink-900",
        colors.hover,
        isDragActive && [colors.border, colors.bg, `ring-4 ${colors.ring}`],
      )}
    >
      <input {...getInputProps()} />
      <div className="flex flex-col items-center gap-3">
        <div className={cn(
          "w-12 h-12 rounded-xl flex items-center justify-center",
          isDragActive ? [colors.bg, colors.border, "border"] : "bg-ink-800"
        )}>
          {isDragActive ? (
            <FileText className={cn("w-5 h-5", colors.text)} />
          ) : (
            <Upload className="w-5 h-5 text-ink-500" />
          )}
        </div>
        <div>
          <p className="text-sm font-medium text-ink-300">
            {isDragActive ? "Drop to upload" : label}
          </p>
          <p className="text-xs text-ink-600 mt-1">or click to browse · PDF only</p>
        </div>
      </div>
    </div>
  );
}
