"use client";

import { cn, getImpactColor } from "@/lib/utils";
import type { ImpactLevel } from "@/types";

interface Props {
  level: ImpactLevel;
  size?: "sm" | "md";
}

const labels: Record<ImpactLevel, string> = {
  high: "High Impact",
  medium: "Medium Impact",
  low: "Low Impact",
  none: "No Impact",
};

export default function ImpactBadge({ level, size = "md" }: Props) {
  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 rounded-full border font-medium",
      getImpactColor(level),
      size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-xs"
    )}>
      <span className={cn(
        "rounded-full flex-shrink-0",
        size === "sm" ? "w-1.5 h-1.5" : "w-2 h-2",
        level === "high" ? "bg-crimson-500" :
          level === "medium" ? "bg-amber-500" :
            level === "low" ? "bg-jade-500" : "bg-ink-400"
      )} />
      {labels[level]}
    </span>
  );
}
