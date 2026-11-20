"use client";

import { WifiOff } from "lucide-react";
import type { RealtimeStatus } from "@/lib/use-ems-data";

export function RealtimeConnectionBanner({
  status,
  isDemo,
}: {
  status: RealtimeStatus;
  isDemo: boolean;
}) {
  if (isDemo || status !== "reconnecting") return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="mb-4 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-900"
    >
      <WifiOff className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <p>
        Koneksi WebSocket terputus. Sedang mencoba menyambung kembali; data
        tetap diperbarui melalui polling berkala.
      </p>
    </div>
  );
}
