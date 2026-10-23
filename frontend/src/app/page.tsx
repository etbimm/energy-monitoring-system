import { Bolt, PlugZap, Wifi } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { KpiCard } from "@/components/dashboard/kpi-card";
import { PowerChart } from "@/components/dashboard/power-chart";
import { LoadDistributionChart } from "@/components/dashboard/load-distribution-chart";
import { DeviceStatusSummary } from "@/components/dashboard/device-status-summary";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  generateDailyProfile,
  getLoadByDevice,
  getTotals,
} from "@/lib/mock-data";
import { formatNumber } from "@/lib/format";

const OVERVIEW_SERIES = [
  { key: "power" as const, label: "Daya Aktif", unit: "kW", color: "#8d1c1c", variant: "area" as const },
  { key: "energy" as const, label: "Energy", unit: "kWh", color: "#0a0a0a", variant: "line" as const, dashed: true },
];

export default function OverviewPage() {
  const totals = getTotals();
  const profile = generateDailyProfile();
  const loadByDevice = getLoadByDevice();

  return (
    <>
      <PageHeader
        title="Overview"
        description="Ringkasan konsumsi energi seluruh sistem"
        action={
          <span className="text-xs text-stone-500">
            Data dummy - siintegrasi Node-RED
          </span>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Total Daya"
          value={formatNumber(totals.totalPower)}
          unit="kW"
          icon={Bolt}
          tone="accent"
          trend={{ value: "4.2%", positive: true }}
        />
        <KpiCard
          label="Daya Semu"
          value={formatNumber(totals.totalApparentPower)}
          unit="kVA"
          icon={Bolt}
          trend={{ value: "1.9%", positive: false }}
        />
        <KpiCard
          label="Energy Hari Ini"
          value={formatNumber(totals.energyToday)}
          unit="kWh"
          icon={PlugZap}
          trend={{ value: "2.8%", positive: false }}
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
            subtitle="Daya (kW) dan energy kumulatif (kWh) - data dummy"
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
          <DeviceStatusSummary />
        </CardContent>
      </Card>
    </>
  );
}