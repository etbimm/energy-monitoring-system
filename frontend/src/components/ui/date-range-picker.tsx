"use client";

import { useState } from "react";
import { Calendar, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export type RangePreset = "24h" | "7d" | "30d" | "custom";

const PRESETS: { label: string; value: RangePreset }[] = [
  { label: "24 Jam", value: "24h" },
  { label: "7 Hari", value: "7d" },
  { label: "30 Hari", value: "30d" },
  { label: "Custom", value: "custom" },
];

function isoDate(d: Date): string {
  const off = d.getTimezoneOffset();
  return new Date(d.getTime() - off * 60_000).toISOString().slice(0, 10);
}

export function DateRangePicker({
  onChange,
  className,
}: {
  onChange: (range: { from: string; to: string; preset: RangePreset }) => void;
  className?: string;
}) {
  const today = new Date();
  const [open, setOpen] = useState(false);
  const [preset, setPreset] = useState<RangePreset>("24h");

  const defaultFrom = isoDate(new Date(today.getTime() - 6 * 86400_000));
  const defaultTo = isoDate(today);
  const [from, setFrom] = useState(defaultFrom);
  const [to, setTo] = useState(defaultTo);

  function applyPreset(p: RangePreset) {
    setPreset(p);
    const now = new Date();
    if (p === "24h") {
      onChange({
        from: isoDate(new Date(now.getTime() - 86400_000)),
        to: isoDate(now),
        preset: p,
      });
      setFrom(isoDate(new Date(now.getTime() - 86400_000)));
      setTo(isoDate(now));
    } else if (p === "7d") {
      const f = isoDate(new Date(now.getTime() - 6 * 86400_000));
      onChange({ from: f, to: isoDate(now), preset: p });
      setFrom(f);
      setTo(isoDate(now));
    } else if (p === "30d") {
      const f = isoDate(new Date(now.getTime() - 29 * 86400_000));
      onChange({ from: f, to: isoDate(now), preset: p });
      setFrom(f);
      setTo(isoDate(now));
    }
    if (p !== "custom") setOpen(false);
  }

  function applyCustom() {
    if (from > to) {
      const tmp = from;
      setFrom(to);
      setTo(tmp);
      onChange({ from: to, to: from, preset: "custom" });
    } else {
      onChange({ from, to, preset: "custom" });
    }
    setOpen(false);
  }

  const activeLabel =
    preset === "custom"
      ? `${from} s/d ${to}`
      : PRESETS.find((p) => p.value === preset)?.label ?? "24 Jam";

  return (
    <div className={cn("relative", className)}>
      {/* Tombol pemicu */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center gap-2 rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-xs font-medium text-stone-700 shadow-sm transition-colors hover:bg-brand-50"
      >
        <Calendar className="h-3.5 w-3.5 text-brand-700" />
        {activeLabel}
        <ChevronDown className="h-3.5 w-3.5 text-stone-400" />
      </button>

      {/* Panel dropdown */}
      {open ? (
        <>
          {/* overlay untuk tutup saat klik luar */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <div className="absolute right-0 z-50 mt-2 w-72 rounded-lg border border-stone-200 bg-white p-3 shadow-lg">
            {/* Preset cepat */}
            <div className="mb-3 grid grid-cols-3 gap-1">
              {PRESETS.filter((p) => p.value !== "custom").map((p) => (
                <button
                  key={p.value}
                  onClick={() => applyPreset(p.value)}
                  className={cn(
                    "rounded-md px-2 py-1 text-xs font-medium transition-colors",
                    preset === p.value
                      ? "bg-brand-800 text-white"
                      : "bg-stone-100 text-stone-600 hover:bg-brand-50",
                  )}
                >
                  {p.label}
                </button>
              ))}
            </div>

            {/* Pilihan tanggal manual */}
            <div className="space-y-2 border-t border-stone-200 pt-3">
              <label className="block text-xs font-medium text-stone-700">
                Dari
                <input
                  type="date"
                  value={from}
                  max={to}
                  onChange={(e) => setFrom(e.target.value)}
                  className="mt-1 w-full rounded-md border border-stone-300 px-2 py-1.5 text-xs text-stone-900 focus:border-brand-700 focus:outline-none"
                />
              </label>
              <label className="block text-xs font-medium text-stone-700">
                Sampai
                <input
                  type="date"
                  value={to}
                  min={from}
                  max={isoDate(new Date())}
                  onChange={(e) => setTo(e.target.value)}
                  className="mt-1 w-full rounded-md border border-stone-300 px-2 py-1.5 text-xs text-stone-900 focus:border-brand-700 focus:outline-none"
                />
              </label>
              <button
                onClick={applyCustom}
                className="w-full rounded-md bg-brand-800 px-2 py-1.5 text-xs font-medium text-white hover:bg-brand-700"
              >
                Terapkan
              </button>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}