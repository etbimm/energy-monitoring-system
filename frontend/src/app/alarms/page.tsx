"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { DataState } from "@/components/ui/data-state";
import { DemoDataNotice } from "@/components/ui/demo-data-notice";
import {
  PaginationControls,
  type PageSize,
} from "@/components/ui/pagination-controls";
import { acknowledgeAlarm, getAlarms } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { DEMO_MODE } from "@/lib/demo-mode";
import { ALARMS } from "@/lib/mock-data";
import type { Alarm } from "@/lib/types";

const severityStyles = {
  critical: "border-brand-800 bg-brand-800 text-white",
  warning: "border-amber-300 bg-amber-50 text-amber-900",
  info: "border-stone-200 bg-stone-50 text-stone-700",
};

const severityLabel = {
  critical: "Kritis",
  warning: "Peringatan",
  info: "Info",
};

function getDemoAlarms(current: Alarm[]) {
  return ALARMS.map((alarm) => ({
    ...alarm,
    acknowledged:
      current.find((item) => item.id === alarm.id)?.acknowledged ??
      alarm.acknowledged,
  }));
}

export default function AlarmsPage() {
  const { isAdmin } = useAuth();
  const [alarms, setAlarms] = useState<Alarm[]>(DEMO_MODE ? ALARMS : []);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [isDemo, setIsDemo] = useState(DEMO_MODE);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState<PageSize>(20);
  const [hasNextPage, setHasNextPage] = useState(false);
  const requestSequence = useRef(0);
  const alarmsRef = useRef(alarms);
  alarmsRef.current = alarms;

  const refresh = useCallback(async () => {
    const requestId = ++requestSequence.current;
    try {
      const currentAlarms = await getAlarms(
        false,
        pageSize + 1,
        page * pageSize,
      );
      if (requestId !== requestSequence.current) return;
      if (currentAlarms.length === 0 && DEMO_MODE) {
        const demoAlarms = getDemoAlarms(alarmsRef.current);
        setAlarms(demoAlarms);
        setHasNextPage((page + 1) * pageSize < demoAlarms.length);
        setIsDemo(true);
        setError("Backend belum memiliki alarm. Menampilkan contoh alarm simulasi.");
      } else {
        if (currentAlarms.length === 0 && page > 0) {
          setPage((current) => Math.max(0, current - 1));
          return;
        }
        setAlarms(currentAlarms.slice(0, pageSize));
        setHasNextPage(currentAlarms.length > pageSize);
        setIsDemo(false);
        setError(null);
      }
    } catch (cause) {
      if (requestId !== requestSequence.current) return;
      if (DEMO_MODE) {
        const demoAlarms = getDemoAlarms(alarmsRef.current);
        setAlarms(demoAlarms);
        setHasNextPage((page + 1) * pageSize < demoAlarms.length);
        setIsDemo(true);
      } else {
        setAlarms([]);
        setHasNextPage(false);
        setIsDemo(false);
      }
      setError(cause instanceof Error ? cause.message : "Gagal memuat alarm.");
    } finally {
      if (requestId === requestSequence.current) setLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    void refresh();
    const poll = window.setInterval(() => void refresh(), 15_000);
    return () => window.clearInterval(poll);
  }, [refresh]);

  const visibleAlarms = isDemo
    ? alarms.slice(page * pageSize, (page + 1) * pageSize)
    : alarms;

  async function acknowledge(id: string) {
    if (isDemo) {
      setAlarms((current) =>
        current.map((alarm) =>
          alarm.id === id ? { ...alarm, acknowledged: true } : alarm,
        ),
      );
      return;
    }

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
      {isDemo ? <DemoDataNotice message="menampilkan contoh alarm simulasi. Status acknowledge hanya tersimpan di tampilan demo." /> : null}
      <DataState loading={loading} error={error} />

      {visibleAlarms.length === 0 && !loading && !error ? (
        <p className="rounded-lg border border-stone-200 bg-white px-4 py-6 text-center text-sm text-stone-600">
          Tidak ada alarm aktif.
        </p>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {visibleAlarms.map((alarm) => (
              <Card
                key={alarm.id}
                className={`min-w-0 border p-3 sm:p-4 ${severityStyles[alarm.severity]}`}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="break-words text-sm font-medium">{alarm.message}</p>
                    <p className="mt-1 break-words text-xs opacity-75">
                      {alarm.deviceName} ({alarm.deviceId}) -{" "}
                      {formatDateTime(alarm.timestamp)}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="rounded-full bg-white/20 px-2.5 py-0.5 text-[11px] uppercase tracking-wider">
                      {severityLabel[alarm.severity]}
                    </span>
                    <span className="text-[11px] uppercase tracking-wider opacity-80">
                      {alarm.acknowledged ? "Acknowledged" : "Baru"}
                    </span>
                  </div>
                </div>
                {/* Acknowledge hanya untuk admin (backend juga menolak viewer). */}
                {!alarm.acknowledged && (isAdmin || isDemo) ? (
                  <button
                    type="button"
                    disabled={pendingId === alarm.id}
                    onClick={() => void acknowledge(alarm.id)}
                    className="mt-3 rounded-md border border-amber-700/20 bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-amber-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {pendingId === alarm.id ? "Menyimpan..." : "Acknowledge"}
                  </button>
                ) : null}
              </Card>
            ))}
          </div>
          <PaginationControls
            page={page}
            pageSize={pageSize}
            itemCount={visibleAlarms.length}
            hasNextPage={hasNextPage}
            onPageChange={setPage}
            onPageSizeChange={(nextSize) => {
              setPageSize(nextSize);
              setPage(0);
            }}
          />
        </>
      )}
    </>
  );
}
