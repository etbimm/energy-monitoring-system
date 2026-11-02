import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function KpiCard({
  label,
  value,
  unit,
  icon: Icon,
  trend,
  tone = "default",
}: {
  label: string;
  value: string;
  unit?: string;
  icon: LucideIcon;
  trend?: { value: string; positive: boolean };
  tone?: "default" | "accent" | "danger";
}) {
  const highlighted = tone === "accent" || tone === "danger";

  return (
    <Card className="min-w-0 border-stone-200 bg-white p-3 text-stone-900 sm:p-5">
      <div className="flex items-start justify-between">
        <div>
          <p
            className="text-xs font-medium uppercase tracking-wider text-stone-500"
          >
            {label}
          </p>
          <p
            className={cn(
              "mt-2 text-xl font-semibold tabular-nums sm:text-2xl",
              highlighted ? "text-brand-800" : "text-stone-900",
            )}
          >
            {value}
            {unit ? (
              <span
                className="ml-1 text-sm font-normal text-stone-500"
              >
                {unit}
              </span>
            ) : null}
          </p>
          {trend ? (
            <p
              className={cn(
                "mt-1 text-xs font-medium",
                trend.positive ? "text-emerald-600" : "text-brand-700",
              )}
            >
              {trend.positive ? "+" : ""}
              {trend.value} vs kemarin
            </p>
          ) : null}
        </div>
        <div
          className={cn(
            "rounded-lg p-2",
            highlighted ? "bg-brand-100" : "bg-brand-50",
          )}
        >
          <Icon
            className={cn(
              "h-4 w-4",
              tone === "danger" ? "text-brand-900" : "text-brand-700",
            )}
            aria-hidden
          />
        </div>
      </div>
    </Card>
  );
}
