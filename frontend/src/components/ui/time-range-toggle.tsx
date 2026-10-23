"use client";

import { cn } from "@/lib/utils";

export type TimeRange = "1h" | "24h" | "7d" | "30d";

export function TimeRangeToggle({
  value,
  onChange,
  options,
  className,
}: {
  value: TimeRange;
  onChange: (v: TimeRange) => void;
  options: { label: string; value: TimeRange }[];
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex rounded-lg border border-stone-200 bg-white p-0.5",
        className,
      )}
    >
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={cn(
            "rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
            value === opt.value
              ? "bg-brand-800 text-white"
              : "text-stone-600 hover:bg-brand-50 hover:text-brand-900",
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}