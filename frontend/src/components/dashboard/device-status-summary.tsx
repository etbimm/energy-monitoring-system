import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { DEVICES } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

/**
 * Ringkasan status seluruh power meter untuk halaman Overview.
 *
 * Sengaja TIDAK menampilkan daftar lengkap 18 device (terlalu panjang untuk
 * halaman ringkasan). Yang ditampilkan: hitungan per status + daftar device
 * yang bermasalah saja (warning & offline).
 */
export function DeviceStatusSummary() {
  const online = DEVICES.filter((d) => d.status === "online");
  const warning = DEVICES.filter((d) => d.status === "warning");
  const offline = DEVICES.filter((d) => d.status === "offline");
  const attention = [...warning, ...offline];

  return (
    <div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <CountTile
          label="Online"
          value={online.length}
          total={DEVICES.length}
          dot="bg-emerald-500"
          text="text-emerald-700"
          ring="ring-emerald-200"
        />
        <CountTile
          label="Warning"
          value={warning.length}
          total={DEVICES.length}
          dot="bg-amber-500"
          text="text-amber-700"
          ring="ring-amber-200"
        />
        <CountTile
          label="Offline"
          value={offline.length}
          total={DEVICES.length}
          dot="bg-brand-600"
          text="text-brand-700"
          ring="ring-brand-200"
        />
        <div className="rounded-lg bg-stone-50 p-3 ring-1 ring-stone-200">
          <p className="text-[11px] uppercase tracking-wider text-stone-500">
            Total Meter
          </p>
          <p className="mt-1 flex items-baseline gap-1.5">
            <span className="text-xl font-semibold tabular-nums text-stone-900">
              {DEVICES.length}
            </span>
            <span className="text-[11px] text-stone-500">unit</span>
          </p>
          <p className="mt-1 text-[11px] text-stone-500">
            {online.length} dalam kondisi baik
          </p>
        </div>
      </div>

      <div className="mt-4">
        {attention.length === 0 ? (
          <p className="rounded-lg bg-emerald-50 px-3 py-2.5 text-sm text-emerald-800">
            Seluruh power meter dalam kondisi normal.
          </p>
        ) : (
          <>
            <p className="text-xs font-medium uppercase tracking-wider text-stone-500">
              Perlu perhatian ({attention.length})
            </p>
            <ul className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-1">
              {attention.map((d) => (
                <li
                  key={d.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-stone-50 px-3 py-2 ring-1 ring-stone-200"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-stone-900">
                      {d.name}
                    </p>
                    <p className="truncate text-xs text-stone-500">
                      {d.id} - {d.location}
                    </p>
                  </div>
                  <StatusBadge status={d.status} />
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-stone-200 pt-3">
        <p className="text-xs text-stone-500">
          Ringkasan status seluruh {DEVICES.length} power meter
        </p>
        <Link
          href="/devices"
          className="inline-flex items-center gap-2 rounded-lg bg-brand-800 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-700"
        >
          Lihat Semua Device
          <span className="rounded bg-white/20 px-1.5 py-0.5 text-xs font-bold tabular-nums">
            {DEVICES.length}
          </span>
          <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      </div>
    </div>
  );
}

function CountTile({
  label,
  value,
  total,
  dot,
  text,
  ring,
}: {
  label: string;
  value: number;
  total: number;
  dot: string;
  text: string;
  ring: string;
}) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div className={cn("rounded-lg bg-stone-50 p-3 ring-1", ring)}>
      <p className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-stone-500">
        <span className={cn("h-1.5 w-1.5 rounded-full", dot)} />
        {label}
      </p>
      <p className="mt-1 flex items-baseline gap-1.5">
        <span className={cn("text-xl font-semibold tabular-nums", text)}>
          {value}
        </span>
        <span className="text-[11px] text-stone-500">dari {total}</span>
      </p>
      <p className="mt-1 text-[11px] text-stone-500">{pct}%</p>
    </div>
  );
}
