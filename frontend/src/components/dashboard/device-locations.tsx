"use client";

import { useState } from "react";
import { ChevronDown, MapPin } from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { Card } from "@/components/ui/card";
import { formatTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Device, MeterPanel } from "@/lib/types";

export function DeviceLocations({ panels }: { panels: MeterPanel[] }) {
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null);
  const selectedPanel = panels.find(
    (panel) => panel.location === selectedLocation,
  );

  return (
    <div>
      <div className="mb-3">
        <h2 className="text-sm font-semibold text-stone-900">Titik / Panel</h2>
        <p className="mt-0.5 text-xs text-stone-500">
          Pilih lokasi untuk melihat power meter dan statusnya.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
        {panels.map((panel) => {
          const selected = selectedLocation === panel.location;
          const online = panel.devices.filter((device) => device.status === "online").length;
          const warning = panel.devices.filter((device) => device.status === "warning").length;
          const offline = panel.devices.filter((device) => device.status === "offline").length;

          return (
            <button
              key={panel.location}
              type="button"
              aria-expanded={selected}
              aria-controls="selected-location-devices"
              onClick={() =>
                setSelectedLocation(selected ? null : panel.location)
              }
              className={cn(
                "min-w-0 rounded-xl border p-3 text-left shadow-sm transition-colors sm:p-4",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700 focus-visible:ring-offset-2",
                selected
                  ? "border-brand-700 bg-brand-50 ring-1 ring-brand-700"
                  : "border-stone-200 bg-white hover:border-brand-300 hover:bg-brand-50/50",
              )}
            >
              <span className="flex items-start justify-between gap-2">
                <span className="flex min-w-0 items-center gap-2">
                  <MapPin
                    className="h-4 w-4 shrink-0 text-brand-700"
                    aria-hidden
                  />
                  <span className="truncate text-sm font-semibold text-stone-900">
                    {panel.location}
                  </span>
                </span>
                <ChevronDown
                  className={cn(
                    "h-4 w-4 shrink-0 text-stone-400 transition-transform",
                    selected && "rotate-180 text-brand-700",
                  )}
                  aria-hidden
                />
              </span>
              <span className="mt-2 block text-xs text-stone-500">
                {panel.devices.length} power meter
              </span>
              <span className="mt-2 flex flex-wrap gap-x-2 gap-y-1 text-[10px] font-medium">
                <span className="text-emerald-700">{online} online</span>
                {warning > 0 && (
                  <span className="text-amber-700">{warning} warning</span>
                )}
                {offline > 0 && (
                  <span className="text-brand-700">{offline} offline</span>
                )}
              </span>
            </button>
          );
        })}
      </div>

      {selectedPanel ? (
        <Card id="selected-location-devices" className="mt-4 overflow-hidden">
          <div className="border-b border-stone-200 px-4 py-3 sm:px-5">
            <h3 className="text-sm font-semibold text-stone-900">
              {selectedPanel.location}
            </h3>
            <p className="mt-0.5 text-xs text-stone-500">
              {selectedPanel.devices.length} power meter di lokasi ini
            </p>
          </div>
          <ul className="divide-y divide-stone-100 px-4 sm:px-5">
            {selectedPanel.devices.map((device) => (
              <DeviceRow key={device.id} device={device} />
            ))}
          </ul>
        </Card>
      ) : (
        <p className="mt-4 rounded-lg border border-dashed border-stone-300 px-4 py-5 text-center text-sm text-stone-500">
          Belum ada lokasi dipilih.
        </p>
      )}
    </div>
  );
}

function DeviceRow({ device }: { device: Device }) {
  return (
    <li className="flex min-w-0 items-center justify-between gap-3 py-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-stone-900">
          {device.name}
        </p>
        <p className="mt-0.5 truncate text-xs text-stone-500">
          {device.id} · {device.brand}
        </p>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <StatusBadge status={device.status} />
        <span className="text-[10px] text-stone-400">
          Last seen {formatTime(device.lastSeen)}
        </span>
      </div>
    </li>
  );
}
