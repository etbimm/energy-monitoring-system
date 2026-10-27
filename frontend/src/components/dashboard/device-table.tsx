import { StatusBadge } from "@/components/ui/status-badge";
import { formatTime } from "@/lib/format";
import type { Device } from "@/lib/types";

/**
 * Tabel identitas device.
 *
 * Sengaja TIDAK menampilkan nilai pengukuran (daya, kVA, kVAR, energy, V/I,
 * PF, Hz) karena seluruh nilai tersebut sudah tersedia di menu Real-time.
 * Menu ini berfungsi sebagai daftar inventaris + status koneksi.
 */
export function DeviceTable({ devices }: { devices: Device[] }) {
  return (
    <div className="hidden overflow-x-auto sm:block">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-stone-200 text-xs uppercase tracking-wider text-stone-500">
            <th className="py-2 pr-4 font-medium">Device</th>
            <th className="py-2 pr-4 font-medium">Merk</th>
            <th className="py-2 pr-4 font-medium">Status</th>
            <th className="py-2 text-right font-medium">Last seen</th>
          </tr>
        </thead>
        <tbody>
          {devices.map((d) => (
            <tr
              key={d.id}
              className="border-b border-stone-100 transition-colors hover:bg-brand-50/60"
            >
              <td className="whitespace-nowrap py-3 pr-4">
                <p className="font-medium text-stone-900">{d.name}</p>
                <p className="text-xs whitespace-nowrap text-stone-500">
                  {d.id} - {d.location}
                </p>
              </td>
              <td className="whitespace-nowrap py-3 pr-4 text-xs text-stone-600">
                {d.brand}
              </td>
              <td className="py-3 pr-4">
                <StatusBadge status={d.status} />
              </td>
              <td className="whitespace-nowrap py-3 text-right tabular-nums text-xs text-stone-500">
                {formatTime(d.lastSeen)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Versi card untuk layar HP, menggantikan tabel yang melebar */
export function DeviceCards({ devices }: { devices: Device[] }) {
  return (
    <ul className="grid grid-cols-2 gap-3 sm:hidden">
      {devices.map((d) => (
        <li
          key={d.id}
          className="min-w-0 rounded-lg border border-stone-200 bg-stone-50 p-3"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-stone-900">{d.name}</p>
              <p className="truncate text-xs text-stone-500">
                {d.id} - {d.location}
              </p>
              <p className="mt-0.5 truncate text-xs text-stone-500">{d.brand}</p>
            </div>
            <StatusBadge status={d.status} />
          </div>

          <p className="mt-2 text-right text-[11px] text-stone-400">
            Last seen {formatTime(d.lastSeen)}
          </p>
        </li>
      ))}
    </ul>
  );
}
