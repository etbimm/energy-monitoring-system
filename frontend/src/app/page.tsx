"use client";

import { useEffect, useState } from "react";
import { Bolt, PlugZap, Wifi } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { PowerChart } from "@/components/dashboard/power-chart";
import { LoadDistributionChart } from "@/components/dashboard/load-distribution-chart";
import { DeviceStatusSummary } from "@/components/dashboard/device-status-summary";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { DataState } from "@/components/ui/data-state";
import { getReadings } from "@/lib/api";
import { getLoadByPanel } from "@/lib/device-data";
import { useEMSData } from "@/lib/use-ems-data";
import type { TimeSeriesPoint } from "@/lib/types";
import { formatNumber } from "@/lib/format";

const OVERVIEW_SERIES = [
  { key: "power" as const, label: "Daya Aktif", unit: "kW", color: "#8d1c1c", variant: "area" as const },
  { key: "energy" as const, label: "Energy", unit: "kWh", color: "#0a0a0a", variant: "line" as const, dashed: true },
];

export default function OverviewPage() {
  const { devices, summary, loading, error } = useEMSData();
  const [profile, setProfile] = useState<TimeSeriesPoint[]>([]);
  const [readingsError, setReadingsError] = useState<string | null>(null);

  useEffect(() => {
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    let active = true;
    const load = () => {
      const end = new Date();
      return getReadings({
        from: start.toISOString(),
        to: end.toISOString(),
        bucket: "5m",
      })
        .then((points) => {
          if (active) {
            setProfile(points);
            setReadingsError(null);
          }
        })
        .catch((cause: unknown) => {
          if (active) {
            setReadingsError(
              cause instanceof Error ? cause.message : "Gagal memuat grafik.",
            );
          }
        });
    };
    void load();
    const poll = window.setInterval(() => void load(), 15_000);
    return () => {
      active = false;
      window.clearInterval(poll);
    };
  }, []);

  const totals = summary ?? {
    totalPower: 0,
    totalApparentPower: 0,
    totalReactivePower: 0,
    energyToday: 0,
    online: 0,
    warning: 0,
    offline: 0,
    total: 0,
  };
  const loadByDevice = getLoadByPanel(devices);

  return (
    <>
      <PageHeader
        title="Overview"
        description="Ringkasan konsumsi energi seluruh sistem"
        action={
          <span className="text-xs text-stone-500">
            {devices.length} power meter terdaftar
          </span>
        }
      />
      <DataState loading={loading} error={error} />
      {readingsError ? <DataState loading={false} error={readingsError} /> : null}

      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <KpiCard
          label="Total Daya"
          value={formatNumber(totals.totalPower)}
          unit="kW"
          icon={Bolt}
          tone="accent"
        />
        <KpiCard
          label="Daya Semu"
          value={formatNumber(totals.totalApparentPower)}
          unit="kVA"
          icon={Bolt}
        />
        <KpiCard
          label="Energy Hari Ini"
          value={formatNumber(totals.energyToday)}
          unit="kWh"
          icon={PlugZap}
        />
        <KpiCard
          label="Device Online"
          value={`${totals.online}/${totals.total}`}
          icon={Wifi}
          tone={totals.offline > 0 ? "danger" : "default"}
        />
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader
            title="Profil Konsumsi 24 Jam"
            subtitle="Daya (kW) dan energy kumulatif (kWh) - meter incoming"
          />
          <CardContent>
            <PowerChart data={profile} series={OVERVIEW_SERIES} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader
            title="Distribusi Beban"
            subtitle="Kontribusi daya per device"
          />
          <CardContent>
            <LoadDistributionChart data={loadByDevice} />
          </CardContent>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader
          title="Status Device"
          subtitle="Ringkasan kondisi semua power meter"
        />
        <CardContent>
          <DeviceStatusSummary devices={devices} />
        </CardContent>
      </Card>
    </>
  );
}
