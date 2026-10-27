"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Device } from "@/lib/types";

export function PhaseDeviceDetails({
  devices,
  locations,
}: {
  devices: Device[];
  locations: string[];
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null);
  const selectedDevices = devices.filter(
    (device) => device.location === selectedLocation,
  );

  return (
    <Card className="mt-4">
      <CardHeader
        title="Detail Per Fasa"
        subtitle="Pilih titik/lokasi untuk melihat nilai L1/L2/L3"
      />
      <CardContent>
        <div className="relative max-w-sm">
          <button
            type="button"
            aria-expanded={isOpen}
            aria-controls="phase-location-options"
            onClick={() => setIsOpen((open) => !open)}
            className="flex w-full items-center justify-between gap-3 rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-left text-sm text-stone-700 shadow-sm hover:border-brand-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700"
          >
            <span className={selectedLocation ? "font-medium text-stone-900" : "text-stone-500"}>
              {selectedLocation ?? "Pilih titik/lokasi"}
            </span>
            <ChevronDown
              className={cn("h-4 w-4 shrink-0 transition-transform", isOpen && "rotate-180")}
              aria-hidden
            />
          </button>

          {isOpen && (
            <div
              id="phase-location-options"
              className="absolute inset-x-0 top-full z-20 mt-1 max-h-64 overflow-y-auto rounded-lg border border-stone-200 bg-white p-1 shadow-lg"
            >
              {locations.map((location) => {
                const count = devices.filter(
                  (device) => device.location === location,
                ).length;
                return (
                  <button
                    key={location}
                    type="button"
                    onClick={() => {
                      setSelectedLocation(location);
                      setIsOpen(false);
                    }}
                    className={cn(
                      "flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm hover:bg-brand-50",
                      selectedLocation === location
                        ? "bg-brand-50 font-medium text-brand-900"
                        : "text-stone-700",
                    )}
                  >
                    <span>{location}</span>
                    <span className="text-xs text-stone-500">
                      {count > 0 ? `${count} device` : "Tidak ada device online"}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {selectedLocation && selectedDevices.length > 0 ? (
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            {selectedDevices.map((device) => (
              <PhaseCard key={device.id} device={device} />
            ))}
          </div>
        ) : selectedLocation ? (
          <p className="mt-4 rounded-lg border border-dashed border-stone-300 px-3 py-4 text-center text-sm text-stone-500">
            Tidak ada device online di lokasi {selectedLocation}.
          </p>
        ) : (
          <p className="mt-4 rounded-lg border border-dashed border-stone-300 px-3 py-4 text-center text-sm text-stone-500">
            Pilih titik/lokasi untuk menampilkan detail per fasa.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function PhaseCard({ device }: { device: Device }) {
  return (
    <div className="rounded-lg border border-stone-200 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-stone-900">
            {device.name}
          </p>
          <p className="truncate text-xs text-stone-500">
            {device.brand} - {device.location}
          </p>
        </div>
        <StatusBadge status={device.status} />
      </div>

      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="text-stone-500">
              <th className="py-1 pr-3 font-medium">Fasa</th>
              <th className="py-1 pr-3 text-right font-medium">V</th>
              <th className="py-1 pr-3 text-right font-medium">A</th>
              <th className="py-1 pr-3 text-right font-medium">kW</th>
              <th className="py-1 pr-3 text-right font-medium">kVA</th>
              <th className="py-1 pr-3 text-right font-medium">kVAR</th>
              <th className="py-1 text-right font-medium">THD-I</th>
            </tr>
          </thead>
          <tbody>
            {device.phases.map((phase) => (
              <tr key={phase.phase} className="border-t border-stone-100">
                <td className="py-1.5 pr-3 font-medium text-stone-700">
                  {phase.phase}
                </td>
                <td className="py-1.5 pr-3 text-right tabular-nums text-stone-700">
                  {phase.voltage !== null ? formatNumber(phase.voltage, 0) : "-"}
                </td>
                <td className="py-1.5 pr-3 text-right tabular-nums text-stone-700">
                  {phase.current !== null ? formatNumber(phase.current) : "-"}
                </td>
                <td className="py-1.5 pr-3 text-right tabular-nums text-stone-900">
                  {phase.power !== null ? formatNumber(phase.power) : "-"}
                </td>
                <td className="py-1.5 pr-3 text-right tabular-nums text-stone-600">
                  {phase.apparentPower !== null
                    ? formatNumber(phase.apparentPower)
                    : "-"}
                </td>
                <td className="py-1.5 pr-3 text-right tabular-nums text-stone-600">
                  {phase.reactivePower !== null
                    ? formatNumber(phase.reactivePower)
                    : "-"}
                </td>
                <td className="py-1.5 text-right tabular-nums text-stone-600">
                  {phase.thdCurrent !== null
                    ? `${formatNumber(phase.thdCurrent)}%`
                    : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
