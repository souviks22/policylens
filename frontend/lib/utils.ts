import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { ChangeType, ImpactLevel } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(n: number): string {
  return n.toLocaleString();
}

export function getChangeColor(type: ChangeType): string {
  switch (type) {
    case "addition":
      return "jade";
    case "deletion":
      return "crimson";
    case "modification":
      return "amber";
    case "regulatory_update":
      return "sapphire";
    default:
      return "ink";
  }
}

export function getChangeLabel(type: ChangeType): string {
  switch (type) {
    case "addition":
      return "Addition";
    case "deletion":
      return "Deletion";
    case "modification":
      return "Modification";
    case "regulatory_update":
      return "Regulatory Update";
    default:
      return "Unchanged";
  }
}

export function getImpactColor(level: ImpactLevel): string {
  switch (level) {
    case "high":
      return "text-crimson-600 bg-crimson-50 border-crimson-200";
    case "medium":
      return "text-amber-700 bg-amber-50 border-amber-200";
    case "low":
      return "text-jade-700 bg-jade-50 border-jade-200";
    default:
      return "text-ink-500 bg-ink-50 border-ink-200";
  }
}

export function getImpactDot(level: ImpactLevel): string {
  switch (level) {
    case "high":
      return "bg-crimson-500";
    case "medium":
      return "bg-amber-500";
    case "low":
      return "bg-jade-500";
    default:
      return "bg-ink-300";
  }
}

export function truncate(text: string, max = 200): string {
  if (text.length <= max) return text;
  return text.slice(0, max).trimEnd() + "…";
}
