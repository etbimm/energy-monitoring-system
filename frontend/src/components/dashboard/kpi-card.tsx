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
  // accent & danger memakai panel maroon gelap -> font putih
  const dark = tone === "accent" || tone === "danger";
  const toneClass = dark
    ? tone === "danger"
      ? "bg-brand-900 border-brand-900 text-white"
      : "bg-brand-800 border-brand-800 text-white"
    : "border-stone-200 bg-white text-stone-900";

  return (
    <Card className={cn("p-5", toneClass)}>
      <div className="flex items-start justify-between">
        <div>
          <p
            className={cn(
              "text-xs font-medium uppercase tracking-wider",
              dark ? "text-brand-200" : "text-stone-500",
            )}
          >
            {label}
          </p>
          <p
            className={cn(
              "mt-2 text-2xl font-semibold tabular-nums",
              dark ? "text-white" : "text-stone-900",
            )}
          >
            {value}
            {unit ? (
              <span
                className={cn(
                  "ml-1 text-sm font-normal",
                  dark ? "text-brand-200" : "text-stone-500",
                )}
              >
                {unit}
              </span>
            ) : null}
          </p>
          {trend ? (
            <p
              className={cn(
                "mt-1 text-xs font-medium",
                dark
                  ? "text-brand-100"
                  : trend.positive
                    ? "text-emerald-600"
                    : "text-brand-700",
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
            dark ? "bg-white/15" : "bg-brand-50",
          )}
        >
          <Icon
            className={cn("h-4 w-4", dark ? "text-white" : "text-brand-700")}
            aria-hidden
          />
        </div>
      </div>
    </Card>
  );
}