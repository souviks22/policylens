"use client";

import { useEffect, useState } from "react";
import type { UploadedDoc } from "@/types";
import { GitCompare } from "lucide-react";

const STEPS = [
  "Extracting text from documents…",
  "Computing paragraph-level diff…",
  "Performing semantic analysis…",
  "Evaluating compliance impact…",
  "Generating executive summary…",
  "Finalizing comparison report…",
];

interface Props {
  doc1: UploadedDoc;
  doc2: UploadedDoc;
}

export default function AnalyzingOverlay({ doc1, doc2 }: Props) {
  const [currentStep, setCurrentStep] = useState(0);
  const [dots, setDots] = useState(".");

  useEffect(() => {
    const stepInterval = setInterval(() => {
      setCurrentStep((s) => (s < STEPS.length - 1 ? s + 1 : s));
    }, 4200);
    return () => clearInterval(stepInterval);
  }, []);

  useEffect(() => {
    const dotInterval = setInterval(() => {
      setDots((d) => (d.length >= 3 ? "." : d + "."));
    }, 500);
    return () => clearInterval(dotInterval);
  }, []);

  return (
    <div className="grain min-h-screen flex flex-col items-center justify-center px-4">
      <div className="max-w-lg w-full">
        {/* Icon */}
        <div className="flex justify-center mb-8">
          <div className="relative">
            <div className="w-20 h-20 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center">
              <GitCompare className="w-9 h-9 text-amber-400 animate-pulse-slow" />
            </div>
            <div className="absolute -inset-3 rounded-3xl border border-amber-500/10 animate-ping" style={{ animationDuration: "2.5s" }} />
          </div>
        </div>

        <h2 className="font-serif text-2xl sm:text-3xl font-bold text-center text-ink-50 mb-2">
          Analyzing Documents
        </h2>
        <p className="text-ink-500 text-center text-sm mb-10">
          AI is comparing <span className="text-ink-300">{doc1.filename}</span> against{" "}
          <span className="text-ink-300">{doc2.filename}</span>
        </p>

        {/* Progress steps */}
        <div className="space-y-3 mb-10">
          {STEPS.map((step, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className={`
                w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-mono
                transition-all duration-500
                ${i < currentStep ? "bg-amber-500 text-ink-950" :
                  i === currentStep ? "border-2 border-amber-500 bg-transparent" :
                  "border border-ink-700 bg-transparent"}
              `}>
                {i < currentStep && "✓"}
              </div>
              <span className={`text-sm transition-colors duration-300 ${
                i < currentStep ? "text-ink-500 line-through" :
                i === currentStep ? "text-ink-100" :
                "text-ink-700"
              }`}>
                {i === currentStep ? `${step.replace("…", "")}${dots}` : step}
              </span>
            </div>
          ))}
        </div>

        {/* Progress bar */}
        <div className="h-1 rounded-full bg-ink-800 overflow-hidden">
          <div
            className="h-full rounded-full bg-amber-500 transition-all duration-700"
            style={{ width: `${((currentStep + 1) / STEPS.length) * 100}%` }}
          />
        </div>
        <p className="text-xs text-ink-600 text-center mt-3">
          This typically takes 15–30 seconds
        </p>
      </div>
    </div>
  );
}
