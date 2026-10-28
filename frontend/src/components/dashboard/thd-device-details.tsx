"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { formatNumber } from "@/lib/format";
import { frequencySeverity, thdSeverity } from "@/lib/meter-models";
import { cn } from "@/lib/utils";
import type { Device } from "@/lib/types";

export function ThdDeviceDetails({
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
        title="Detail THD per Power Meter"
        subtitle="Pilih titik/lokasi untuk melihat detail meter"
      />
      <CardContent>
        <div className="relative max-w-sm">
          <button
            type="button"
            aria-expanded={isOpen}
            aria-controls="thd-location-options"
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
              id="thd-location-options"
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
                      {count > 0 ? `${count} meter THD` : "Tanpa data THD"}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {selectedLocation && selectedDevices.length > 0 ? (
          <div className="mt-4">
            <h4 className="mb-2 text-sm font-semibold text-stone-900">
              {selectedLocation} · {selectedDevices.length} power meter
            </h4>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-stone-200 text-xs uppercase tracking-wider text-stone-500">
                    <th className="py-2 pr-4 font-medium">Device</th>
                    <th className="py-2 pr-4 font-medium">Model</th>
                    <th className="py-2 pr-4 font-medium">Status</th>
                    <th className="py-2 pr-4 text-right font-medium">THD-I</th>
                    <th className="py-2 pr-4 text-right font-medium">THD-U</th>
                    <th className="py-2 pr-4 text-right font-medium">Hz</th>
                    <th className="py-2 pr-4 text-right font-medium">Unbal V</th>
                    <th className="py-2 pr-4 text-right font-medium">Unbal I</th>
                    <th className="py-2 text-right font-medium">Orde</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedDevices.map((device) => (
                    <tr
                      key={device.id}
                      className="border-b border-stone-100 transition-colors hover:bg-brand-50/60"
                    >
                      <td className="whitespace-nowrap py-3 pr-4">
                        <p className="font-medium text-stone-900">{device.name}</p>
                        <p className="whitespace-nowrap text-xs text-stone-500">
                          {device.id} - {device.location}
                        </p>
                      </td>
                      <td className="py-3 pr-4 text-xs text-stone-600">
                        {device.brand}
                      </td>
                      <td className="py-3 pr-4">
                        <StatusBadge status={device.status} />
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums">
                        <ThdBadge
                          value={device.thdCurrent}
                          severity={thdSeverity(device.thdCurrent)}
                        />
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums text-stone-700">
                        {device.thdVoltage !== null
                          ? `${formatNumber(device.thdVoltage)}%`
                          : "-"}
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums">
                        <span
                          className={
                            frequencySeverity(device.frequency) === "ok"
                              ? "text-stone-700"
                              : "font-semibold text-brand-700"
                          }
                        >
                          {formatNumber(device.frequency, 2)}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums text-stone-600">
                        {device.unbalanceVoltage !== null
                          ? `${formatNumber(device.unbalanceVoltage)}%`
                          : "-"}
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums text-stone-600">
                        {device.unbalanceCurrent !== null
                          ? `${formatNumber(device.unbalanceCurrent)}%`
                          : "-"}
                      </td>
                      <td className="py-3 text-right tabular-nums text-xs text-stone-500">
                        {device.capabilities.maxHarmonicOrder > 0
                          ? `s/d ${device.capabilities.maxHarmonicOrder}`
                          : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : selectedLocation ? (
          <p className="mt-4 rounded-lg border border-dashed border-stone-300 px-3 py-4 text-center text-sm text-stone-500">
            Tidak ada power meter dengan data THD di lokasi {selectedLocation}.
          </p>
        ) : (
          <p className="mt-4 rounded-lg border border-dashed border-stone-300 px-3 py-4 text-center text-sm text-stone-500">
            Pilih titik/lokasi untuk menampilkan detail THD.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function ThdBadge({
  value,
  severity,
}: {
  value: number | null;
  severity: "ok" | "warning" | "critical" | "unsupported";
}) {
  if (value === null) {
    return <span className="text-xs text-stone-400">-</span>;
  }
  const className =
    severity === "critical"
      ? "font-semibold text-brand-700"
      : severity === "warning"
        ? "font-semibold text-amber-600"
        : "text-stone-700";
  return <span className={className}>{formatNumber(value)}%</span>;
}
