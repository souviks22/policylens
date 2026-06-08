"use client";

import { cn } from "@/lib/utils";
import type { ChangeType } from "@/types";
import { Plus, Minus, RefreshCw, FileCheck } from "lucide-react";

interface Props {
  type: ChangeType;
  size?: "sm" | "md";
}

const config: Record<ChangeType, { label: string; icon: React.FC<{ className?: string }>; className: string }> = {
  addition: {
    label: "Addition",
    icon: Plus,
    className: "bg-jade-500/10 text-jade-400 border-jade-500/30",
  },
  deletion: {
    label: "Deletion",
    icon: Minus,
    className: "bg-crimson-500/10 text-crimson-400 border-crimson-500/30",
  },
  modification: {
    label: "Modification",
    icon: RefreshCw,
    className: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  },
  regulatory_update: {
    label: "Regulatory",
    icon: FileCheck,
    className: "bg-sapphire-500/10 text-sapphire-400 border-sapphire-500/30",
  },
  unchanged: {
    label: "Unchanged",
    icon: ((props: { className?: string }) => <span className={props.className}>–</span>) as React.FC<{ className?: string }>,
    className: "bg-ink-800 text-ink-500 border-ink-700",
  },
};

export default function ChangeBadge({ type, size = "md" }: Props) {
  const { label, icon: Icon, className } = config[type] || config.modification;
  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 rounded-md border font-medium",
      className,
      size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs"
    )}>
      <Icon className={size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5"} />
      {label}
    </span>
  );
}
