"use client";

import { useMemo, useState } from "react";
import { PageHeader } from "@/components/layout/page-header";
import { PowerChart } from "@/components/dashboard/power-chart";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  DateRangePicker,
  type RangePreset,
} from "@/components/ui/date-range-picker";
import { generateProfileForRange } from "@/lib/mock-data";
import { formatNumber } from "@/lib/format";
import { POWER_QUALITY_SERIES } from "@/components/dashboard/power-chart";

function isoDate(d: Date): string {
  const off = d.getTimezoneOffset();
  return new Date(d.getTime() - off * 60_000).toISOString().slice(0, 10);
}

export default function HistoryPage() {
  const now = new Date();
  const [range, setRange] = useState({
    from: isoDate(new Date(now.getTime() - 86400_000)),
    to: isoDate(now),
    preset: "24h" as RangePreset,
  });

  const data = useMemo(
    () => generateProfileForRange(range.from, range.to),
    [range.from, range.to],
  );

  const totalEnergy = data.length ? data[data.length - 1].energy : 0;
  const totalReactive = data.length ? data[data.length - 1].energyReactive : 0;
  const totalApparent = data.length ? data[data.length - 1].energyApparent : 0;
  const peak = data.reduce((m, p) => (p.power > m ? p.power : m), 0);
  const peakApparent = data.reduce((m, p) => (p.apparentPower > m ? p.apparentPower : m), 0);
  const peakReactive = data.reduce((m, p) => (p.reactivePower > m ? p.reactivePower : m), 0);
  const avg = data.length ? totalEnergy / data.length : 0;

  return (
    <>
      <PageHeader title="History" description="Analitik konsumsi energi" />

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

      <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <SummaryCard label="Total Energy" value={formatNumber(totalEnergy)} unit="kWh" />
        <SummaryCard label="Rata-rata" value={formatNumber(avg)} unit="kW" />
        <SummaryCard label="Beban Puncak" value={formatNumber(peak)} unit="kW" />
        <SummaryCard
          label="Daya Semu (kVA)"
          value={formatNumber(peakApparent)}
          unit="kVA"
        />
        <SummaryCard
          label="Daya Reaktif (kVAR)"
          value={formatNumber(peakReactive)}
          unit="kVAR"
        />
        <SummaryCard
          label="PF Rata-rata"
          value={peakApparent > 0 ? formatNumber(peak / peakApparent, 3) : "-"}
          unit=""
        />
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <SummaryCard label="Energy Aktif" value={formatNumber(totalEnergy)} unit="kWh" />
        <SummaryCard label="Energy Reaktif" value={formatNumber(totalReactive)} unit="kVARh" />
        <SummaryCard label="Energy Semu" value={formatNumber(totalApparent)} unit="kVAh" />
      </div>

      <Card className="mt-4">
        <CardHeader title="Data" subtitle="Tabel mentah (belum diimplementasi)" />
        <CardContent>
          <p className="text-sm text-stone-600">
            Nanti halaman ini mengambil data dari backend (TimescaleDB) sesuai
            filter tanggal, plus mendukung export CSV dan perbandingan antar
            periode.
          </p>
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
    <Card className="bg-brand-800 border-brand-800 p-5 text-white">
      <p className="text-xs font-medium uppercase tracking-wider text-brand-200">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold tabular-nums">
        {value}
        {unit ? <span className="ml-1 text-sm font-normal text-brand-200">{unit}</span> : null}
      </p>
    </Card>
  );
}