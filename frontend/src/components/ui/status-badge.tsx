import * as React from "react";
import { cn } from "@/lib/utils";
import type { DeviceStatus } from "@/lib/types";

const styles: Record<DeviceStatus, string> = {
  online: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  warning: "bg-amber-50 text-amber-700 ring-amber-200",
  offline: "bg-brand-100 text-brand-800 ring-brand-300",
};

const dotStyles: Record<DeviceStatus, string> = {
  online: "bg-emerald-500",
  warning: "bg-amber-500",
  offline: "bg-brand-600",
};

const labels: Record<DeviceStatus, string> = {
  online: "Online",
  warning: "Warning",
  offline: "Offline",
};

export function StatusBadge({
  status,
  showLabel = true,
  className,
}: {
  status: DeviceStatus;
  showLabel?: boolean;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset",
        styles[status],
        className,
      )}
    >
      <span className="relative flex h-1.5 w-1.5">
        {status !== "offline" ? (
          <span
            className={cn(
              "absolute inline-flex h-full w-full animate-ping rounded-full opacity-60",
              dotStyles[status],
            )}
          />
        ) : null}
        <span
          className={cn(
            "relative inline-flex h-1.5 w-1.5 rounded-full",
            dotStyles[status],
          )}
        />
      </span>
      {showLabel ? labels[status] : null}
    </span>
  );
}