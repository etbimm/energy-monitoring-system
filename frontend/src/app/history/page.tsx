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
import { getReadings } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { generateProfileForRange } from "@/lib/mock-data";
import { POWER_QUALITY_SERIES } from "@/components/dashboard/power-chart";
import type { TimeSeriesPoint } from "@/lib/types";

function isoDate(date: Date): string {
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 10);
}

function dateParam(value: string, endOfDay = false): string {
  return new Date(`${value}T${endOfDay ? "23:59:59" : "00:00:00"}`).toISOString();
}

export default function HistoryPage() {
  const now = new Date();
  const [range, setRange] = useState({
    from: isoDate(new Date(now.getTime() - 86_400_000)),
    to: isoDate(now),
    preset: "24h" as RangePreset,
  });
  const [data, setData] = useState<TimeSeriesPoint[]>(() =>
    generateProfileForRange(
      isoDate(new Date(now.getTime() - 86_400_000)),
      isoDate(now),
    ),
  );
  const [isDemo, setIsDemo] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    if (!range.from || !range.to || range.from > range.to) {
      setError("Rentang tanggal tidak valid. Pilih tanggal mulai dan akhir yang benar.");
      setLoading(false);
      setData([]);
      setIsDemo(false);
      return () => {
        active = false;
      };
    }

    setLoading(true);
    const days =
      (new Date(`${range.to}T00:00:00`).getTime() -
        new Date(`${range.from}T00:00:00`).getTime()) /
      86_400_000;
    getReadings({
      from: dateParam(range.from),
      to: dateParam(range.to, true),
      bucket: days <= 2 ? "5m" : "1h",
    })
      .then((points) => {
        if (active) {
          if (points.length === 0) {
            setData(generateProfileForRange(range.from, range.to));
            setIsDemo(true);
            setError("Belum ada histori di backend.");
          } else {
            setData(points);
            setIsDemo(false);
            setError(null);
          }
        }
      })
      .catch((cause: unknown) => {
        if (active) {
          setData(generateProfileForRange(range.from, range.to));
          setIsDemo(true);
          setError(cause instanceof Error ? cause.message : "Gagal memuat histori.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [range.from, range.to]);

  const totalEnergy = data.length > 1
    ? Math.max(0, data[data.length - 1].energy - data[0].energy)
    : 0;
  const totalReactive = data.length > 1
    ? Math.max(0, data[data.length - 1].energyReactive - data[0].energyReactive)
    : 0;
  const totalApparent = data.length > 1
    ? Math.max(0, data[data.length - 1].energyApparent - data[0].energyApparent)
    : 0;
  const peak = data.reduce((maximum, point) => Math.max(maximum, point.power), 0);
  const peakApparent = data.reduce(
    (maximum, point) => Math.max(maximum, point.apparentPower),
    0,
  );
  const peakReactive = data.reduce(
    (maximum, point) => Math.max(maximum, point.reactivePower),
    0,
  );
  const avg = data.length
    ? data.reduce((total, point) => total + point.power, 0) / data.length
    : 0;
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
    const content = csv.map((row) => row.join(",")).join("\r\n");
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
          <PowerChart data={data} series={POWER_QUALITY_SERIES} />
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
          value={peakApparent > 0 ? formatNumber(avg / (data.reduce((sum, point) => sum + point.apparentPower, 0) / data.length), 3) : "-"}
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
                        {new Date(point.timestamp).toLocaleString("id-ID")}
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
    <Card className="min-w-0 border-brand-800 bg-brand-800 p-3 text-white sm:p-5">
      <p className="text-xs font-medium uppercase tracking-wider text-brand-200">{label}</p>
      <p className="mt-2 text-xl font-semibold tabular-nums sm:text-2xl">
        {value}
        {unit ? <span className="ml-1 text-sm font-normal text-brand-200">{unit}</span> : null}
      </p>
    </Card>
  );
}
