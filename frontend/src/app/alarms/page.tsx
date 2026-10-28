"use client";

import { useCallback, useEffect, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { DataState } from "@/components/ui/data-state";
import { acknowledgeAlarm, getAlarms } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { Alarm } from "@/lib/types";

const severityStyles = {
  critical: "border-brand-900 bg-brand-900 text-white",
  warning: "border-amber-300 bg-amber-50 text-amber-900",
  info: "border-stone-200 bg-stone-50 text-stone-700",
};

const severityLabel = {
  critical: "Kritis",
  warning: "Peringatan",
  info: "Info",
};

export default function AlarmsPage() {
  const [alarms, setAlarms] = useState<Alarm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setAlarms(await getAlarms());
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Gagal memuat alarm.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const poll = window.setInterval(() => void refresh(), 15_000);
    return () => window.clearInterval(poll);
  }, [refresh]);

  async function acknowledge(id: string) {
    setPendingId(id);
    try {
      const updated = await acknowledgeAlarm(id);
      setAlarms((current) =>
        current.map((alarm) => (alarm.id === updated.id ? updated : alarm)),
      );
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Gagal acknowledge alarm.");
    } finally {
      setPendingId(null);
    }
  }

  return (
    <>
      <PageHeader title="Alarms" description="Riwayat dan status alarm sistem" />
      <DataState loading={loading} error={error} />

      {alarms.length === 0 && !loading && !error ? (
        <p className="rounded-lg border border-stone-200 bg-white px-4 py-6 text-center text-sm text-stone-600">
          Tidak ada alarm aktif.
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-1">
          {alarms.map((alarm) => (
            <Card
              key={alarm.id}
              className={`min-w-0 border p-3 sm:p-4 ${severityStyles[alarm.severity]}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium">{alarm.message}</p>
                  <p className="mt-1 text-xs opacity-75">
                    {alarm.deviceName} ({alarm.deviceId}) -{" "}
                    {formatDateTime(alarm.timestamp)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded-full bg-white/20 px-2.5 py-0.5 text-[11px] uppercase tracking-wider">
                    {severityLabel[alarm.severity]}
                  </span>
                  <span className="text-[11px] uppercase tracking-wider opacity-80">
                    {alarm.acknowledged ? "Acknowledged" : "Baru"}
                  </span>
                </div>
              </div>
              {!alarm.acknowledged ? (
                <button
                  type="button"
                  disabled={pendingId === alarm.id}
                  onClick={() => void acknowledge(alarm.id)}
                  className="mt-3 rounded-md bg-white/15 px-3 py-1.5 text-xs font-medium hover:bg-white/25 disabled:opacity-50"
                >
                  {pendingId === alarm.id ? "Menyimpan..." : "Acknowledge"}
                </button>
              ) : null}
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
