"use client";

import { useEffect, useMemo, useState } from "react";
import { Download } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { PowerChart } from "@/components/dashboard/power-chart";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { DataState } from "@/components/ui/data-state";
import { DemoDataNotice } from "@/components/ui/demo-data-notice";
import {
  DateRangePicker,
  type RangePreset,
} from "@/components/ui/date-range-picker";
import {
  getEnergyTotals,
  getReadings,
  type EnergyTotals,
} from "@/lib/api";
import { DEMO_MODE } from "@/lib/demo-mode";
import { formatNumber } from "@/lib/format";
import { generateProfileForRange } from "@/lib/mock-data";
import { POWER_QUALITY_SERIES } from "@/components/dashboard/power-chart";
import type { TimeSeriesPoint } from "@/lib/types";
import { PLANT_TIME_ZONE, plantDate, plantDayBoundary } from "@/lib/time";

// Tanggal dan batas hari selalu dalam WIB (lihat lib/time.ts).
const isoDate = plantDate;
const dateParam = plantDayBoundary;

function rangeDayCount(from: string, to: string): number {
  const start = Date.parse(`${from}T00:00:00Z`);
  const end = Date.parse(`${to}T00:00:00Z`);
  return Math.floor((end - start) / 86_400_000) + 1;
}

export default function HistoryPage() {
  const now = new Date();
  const [range, setRange] = useState({
    from: isoDate(new Date(now.getTime() - 86_400_000)),
    to: isoDate(now),
    preset: "24h" as RangePreset,
  });
  const [data, setData] = useState<TimeSeriesPoint[]>(() =>
    DEMO_MODE
      ? generateProfileForRange(
          isoDate(new Date(now.getTime() - 86_400_000)),
          isoDate(now),
        )
      : [],
  );
  const [energy, setEnergy] = useState<EnergyTotals | null>(null);
  const [isDemo, setIsDemo] = useState(DEMO_MODE);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    if (!range.from || !range.to || range.from > range.to) {
      setError("Rentang tanggal tidak valid. Pilih tanggal mulai dan akhir yang benar.");
      setLoading(false);
      setData([]);
      setEnergy(null);
      setIsDemo(false);
      return () => {
        active = false;
      };
    }

    setLoading(true);
    const days = rangeDayCount(range.from, range.to);
    let inFlight = false;
    let refreshPending = false;

    const load = async () => {
      if (inFlight) {
        refreshPending = true;
        return;
      }
      inFlight = true;
      try {
        const from = dateParam(range.from);
        const to = dateParam(range.to, true);
        const [points, totals] = await Promise.all([
          getReadings({ from, to, bucket: days <= 2 ? "5m" : "1d" }),
          getEnergyTotals({ from, to }),
        ]);
        if (active) {
          if (points.length === 0 && DEMO_MODE) {
            setData(generateProfileForRange(range.from, range.to));
            setEnergy(null);
            setIsDemo(true);
            setError("Belum ada histori di backend.");
          } else {
            setData(points);
            setEnergy(totals);
            setIsDemo(false);
            setError(null);
          }
        }
      } catch (cause: unknown) {
        if (active) {
          setData(DEMO_MODE ? generateProfileForRange(range.from, range.to) : []);
          setEnergy(null);
          setIsDemo(DEMO_MODE);
          setError(cause instanceof Error ? cause.message : "Gagal memuat histori.");
        }
      } finally {
        inFlight = false;
        if (active) {
          setLoading(false);
          if (refreshPending) {
            refreshPending = false;
            void load();
          }
        }
      }
    };

    void load();
    // Histori cukup disegarkan berkala; tidak perlu reload setiap pesan realtime.
    const poll = window.setInterval(() => void load(), 60_000);

    return () => {
      active = false;
      window.clearInterval(poll);
    };
  }, [range.from, range.to]);

  // Total energi dihitung backend sebagai jumlah delta per meter (meter yang
  // offline di awal/akhir rentang tidak merusak total). Selisih titik pertama
  // dan terakhir hanya dipakai untuk fixture mode demo.
  const demoDelta = (key: "energy" | "energyReactive" | "energyApparent") =>
    isDemo && data.length > 1
      ? Math.max(0, (data[data.length - 1][key] ?? 0) - (data[0][key] ?? 0))
      : 0;
  const totalEnergy = energy?.energyActive ?? demoDelta("energy");
  const totalReactive = energy?.energyReactive ?? demoDelta("energyReactive");
  const totalApparent = energy?.energyApparent ?? demoDelta("energyApparent");
  // Statistik hanya dari titik yang punya nilai (titik kosong tidak dihitung 0).
  const values = (key: "power" | "apparentPower" | "reactivePower") =>
    data.map((point) => point[key]).filter((value): value is number => value !== null);
  const mean = (list: number[]) =>
    list.length ? list.reduce((total, value) => total + value, 0) / list.length : null;
  const maxOf = (list: number[]) => (list.length ? Math.max(...list) : null);
  const peak = maxOf(values("power"));
  const peakApparent = maxOf(values("apparentPower"));
  const peakReactive = maxOf(values("reactivePower"));
  const isDailyRange = rangeDayCount(range.from, range.to) > 2;
  const avg = mean(values("power"));
  const avgApparent = mean(values("apparentPower"));
  const avgPf = avg !== null && avgApparent ? avg / avgApparent : null;
  const csv = useMemo(
    () => [
      ["Timestamp", "V", "A", "kW", "kVAR", "kVA", "PF", "Hz", "kWh", "kVARh", "THD-i"],
      ...data.map((point) => [
        point.timestamp,
        point.voltage,
        point.current,
        point.power,
        point.reactivePower,
        point.apparentPower,
        point.powerFactor,
        point.frequency,
        point.energy,
        point.energyReactive,
        point.thdCurrent ?? "",
      ]),
    ],
    [data],
  );

  function exportCsv() {
    const content = `\uFEFF${csv
      .map((row) =>
        row
          .map((value) => {
            const cell = value === null || value === undefined ? "" : String(value);
            return /[;"\r\n]/.test(cell)
              ? `"${cell.replaceAll('"', '""')}"`
              : cell;
          })
          .join(";"),
      )
      .join("\r\n")}`;
    const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `ems-history-${range.from}-${range.to}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <PageHeader title="History" description="Analitik konsumsi energi" />
      {isDemo ? <DemoDataNotice /> : null}
      <DataState loading={loading} error={error} />

      <Card>
        <CardHeader
          title="Konsumsi Daya"
          subtitle={`${range.from} s/d ${range.to} - ${data.length} titik data`}
          action={<DateRangePicker onChange={setRange} />}
        />
        <CardContent>
          <PowerChart
            data={data}
            series={POWER_QUALITY_SERIES}
            xAxisMode={isDailyRange ? "date" : "time"}
          />
        </CardContent>
      </Card>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-3">
        <SummaryCard label="Total Energy" value={formatNumber(totalEnergy)} unit="kWh" />
        <SummaryCard label="Rata-rata" value={formatNumber(avg)} unit="kW" />
        <SummaryCard label="Beban Puncak" value={formatNumber(peak)} unit="kW" />
        <SummaryCard label="Daya Semu Puncak" value={formatNumber(peakApparent)} unit="kVA" />
        <SummaryCard label="Daya Reaktif Puncak" value={formatNumber(peakReactive)} unit="kVAR" />
        <SummaryCard
          label="PF Rata-rata"
          value={formatNumber(avgPf, 3)}
          unit=""
        />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:gap-4 sm:grid-cols-3">
        <SummaryCard label="Energy Aktif" value={formatNumber(totalEnergy)} unit="kWh" />
        <SummaryCard label="Energy Reaktif" value={formatNumber(totalReactive)} unit="kVARh" />
        <SummaryCard label="Energy Semu" value={formatNumber(totalApparent)} unit="kVAh" />
      </div>

      <Card className="mt-4">
        <CardHeader
          title="Data Historis"
          subtitle="Pembacaan meter incoming pada rentang terpilih"
          action={
            <button
              type="button"
              onClick={exportCsv}
              disabled={data.length === 0}
              className="inline-flex items-center gap-2 rounded-lg border border-stone-300 px-3 py-2 text-xs font-medium text-stone-700 hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Download className="h-4 w-4" aria-hidden />
              Export CSV
            </button>
          }
        />
        <CardContent>
          {data.length === 0 ? (
            <p className="text-sm text-stone-500">Tidak ada data pada rentang tanggal ini.</p>
          ) : (
            <div className="max-h-[480px] overflow-auto">
              <table className="w-full min-w-[960px] text-left text-xs">
                <thead className="sticky top-0 bg-stone-50 text-stone-500">
                  <tr>
                    <th className="px-2 py-2 font-medium">Waktu</th>
                    <th className="px-2 py-2 text-right font-medium">V</th>
                    <th className="px-2 py-2 text-right font-medium">A</th>
                    <th className="px-2 py-2 text-right font-medium">kW</th>
                    <th className="px-2 py-2 text-right font-medium">kVAR</th>
                    <th className="px-2 py-2 text-right font-medium">kVA</th>
                    <th className="px-2 py-2 text-right font-medium">PF</th>
                    <th className="px-2 py-2 text-right font-medium">Hz</th>
                    <th className="px-2 py-2 text-right font-medium">kWh</th>
                    <th className="px-2 py-2 text-right font-medium">kVARh</th>
                    <th className="px-2 py-2 text-right font-medium">THD-i</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((point) => (
                    <tr key={point.timestamp} className="border-t border-stone-100">
                      <td className="whitespace-nowrap px-2 py-2">
                        {new Date(point.timestamp).toLocaleString("id-ID", { timeZone: PLANT_TIME_ZONE })}
                      </td>
                      {[point.voltage, point.current, point.power, point.reactivePower,
                        point.apparentPower, point.powerFactor, point.frequency,
                        point.energy, point.energyReactive].map((value, index) => (
                          <td key={index} className="px-2 py-2 text-right tabular-nums">
                            {formatNumber(value, index === 5 ? 3 : index < 2 || index === 6 ? 2 : 1)}
                          </td>
                        ))}
                      <td className="px-2 py-2 text-right tabular-nums">
                        {point.thdCurrent === null ? "-" : `${formatNumber(point.thdCurrent)}%`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}

function SummaryCard({
  label,
  value,
  unit,
}: {
  label: string;
  value: string;
  unit: string;
}) {
  return (
    <Card className="min-w-0 border-stone-200 bg-white p-3 text-stone-900 sm:p-5">
      <p className="text-xs font-medium uppercase tracking-wider text-stone-500">{label}</p>
      <p className="mt-2 text-xl font-semibold tabular-nums text-brand-800 sm:text-2xl">
        {value}
        {unit ? <span className="ml-1 text-sm font-normal text-stone-500">{unit}</span> : null}
      </p>
    </Card>
  );
}
