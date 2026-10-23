import { Activity, PlugZap, Wifi } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { getPanels, getTotals, TOTAL_METERS } from "@/lib/mock-data";
import { formatNumber, formatTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Device } from "@/lib/types";

export default function RealtimePage() {
  const panels = getPanels();
  const totals = getTotals();

  return (
    <>
      <PageHeader
        title="Real-time"
        description="Nilai terkini setiap power meter"
        action={
          <span className="text-xs text-stone-500">
            Data dummy - siintegrasi Node-RED
          </span>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryTile
          label="Total Daya"
          value={formatNumber(totals.totalPower)}
          unit="kW"
          icon={Activity}
        />
        <SummaryTile
          label="Energy Hari Ini"
          value={formatNumber(totals.energyToday)}
          unit="kWh"
          icon={PlugZap}
        />
        <SummaryTile
          label="Meter Online"
          value={`${totals.online}/${totals.total}`}
          icon={Wifi}
          tone={totals.offline > 0 ? "danger" : "default"}
        />
        <SummaryTile
          label="Total Power Meter"
          value={String(TOTAL_METERS)}
          unit="unit"
          icon={Wifi}
        />
      </div>

      {panels.map((panel) => (
        <Card key={panel.location} className="mt-4">
          <CardHeader
            title={panel.location}
            subtitle={`${panel.brands.join(" / ")} - ${panel.devices.length} power meter`}
            action={
              <div className="text-right">
                <p className="text-sm font-semibold tabular-nums text-stone-900">
                  {formatNumber(panel.power)} kW
                </p>
                <p className="text-[11px] text-stone-500">
                  {formatNumber(panel.apparentPower)} kVA -{" "}
                  {formatNumber(panel.reactivePower)} kVAR
                </p>
                <p className="text-[11px] text-stone-500">
                  {formatNumber(panel.energyActive)} kWh
                </p>
              </div>
            }
          />
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {panel.devices.map((d) => (
                <MeterCard key={d.id} device={d} />
              ))}
            </div>
          </CardContent>
        </Card>
      ))}

      <Card className="mt-4">
        <CardHeader
          title="Catatan integrasi"
          subtitle="Bagian ini akan diisi data live via WebSocket"
        />
        <CardContent>
          <p className="text-sm text-stone-600">
            Nanti nilai di atas akan di-update otomatis setiap 1-2 detik dari
            backend melalui WebSocket. Untuk sekarang masih dummy statis.
          </p>
        </CardContent>
      </Card>
    </>
  );
}

function MeterCard({ device: d }: { device: Device }) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-stone-900">{d.name}</p>
          <p className="truncate text-xs text-stone-500">{d.id}</p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {d.thdCurrent !== null ? (
            <span
              className={cn(
                "rounded px-1.5 py-0.5 text-[10px] font-medium tabular-nums",
                d.thdCurrent >= 8
                  ? "bg-brand-100 text-brand-800 ring-1 ring-brand-300"
                  : d.thdCurrent >= 5
                    ? "bg-amber-50 text-amber-700 ring-1 ring-amber-200"
                    : "bg-stone-100 text-stone-600",
              )}
              title="Total Harmonic Distortion arus"
            >
              THD {formatNumber(d.thdCurrent)}%
            </span>
          ) : null}
          <StatusBadge status={d.status} />
        </div>
      </div>

      {d.status === "offline" ? (
        <div className="mt-4 rounded-lg bg-brand-900 px-3 py-2.5">
          <p className="text-xs font-medium text-white">
            Device offline - tidak ada data
          </p>
          <p className="mt-0.5 text-[11px] text-brand-200">
            Last seen {formatTime(d.lastSeen)}
          </p>
        </div>
      ) : (
        <>
          <div className="mt-4 flex items-baseline gap-1.5">
            <span className="text-2xl font-semibold tabular-nums text-stone-900">
              {formatNumber(d.power)}
            </span>
            <span className="text-xs text-stone-500">kW</span>
            <span className="ml-auto text-xs text-stone-500">
              {formatNumber(d.energyActive)} kWh
            </span>
          </div>

          <div className="mt-3 grid grid-cols-3 gap-2">
            <Metric label="Daya Semu" value={formatNumber(d.apparentPower)} unit="kVA" />
            <Metric label="Reaktif" value={formatNumber(d.reactivePower)} unit="kVAR" />
            <Metric label="PF" value={formatNumber(d.powerFactor, 2)} unit="" />
          </div>

          <div className="mt-2 grid grid-cols-3 gap-2">
            <Metric label="Tegangan" value={formatNumber(d.voltage, 0)} unit="V" />
            <Metric label="Arus" value={formatNumber(d.current)} unit="A" />
            <Metric
              label="Frekuensi"
              value={formatNumber(d.frequency, 2)}
              unit="Hz"
            />
          </div>
        </>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  unit,
}: {
  label: string;
  value: string;
  unit: string;
}) {
  return (
    <div className="rounded-md bg-stone-50 p-2 ring-1 ring-stone-200">
      <p className="text-[10px] uppercase tracking-wider text-stone-500">{label}</p>
      <p className="mt-0.5 text-xs font-semibold tabular-nums text-stone-900">
        {value}
        {unit ? <span className="ml-0.5 text-[10px] text-stone-500">{unit}</span> : null}
      </p>
    </div>
  );
}

function SummaryTile({
  label,
  value,
  unit,
  icon: Icon,
  tone = "default",
}: {
  label: string;
  value: string;
  unit?: string;
  icon: typeof Activity;
  tone?: "default" | "danger";
}) {
  const dark = tone === "danger";
  return (
    <Card
      className={
        dark
          ? "border-brand-900 bg-brand-900 p-5 text-white"
          : "border-stone-200 bg-white p-5 text-stone-900"
      }
    >
      <div className="flex items-start justify-between">
        <div>
          <p
            className={
              dark
                ? "text-xs font-medium uppercase tracking-wider text-brand-200"
                : "text-xs font-medium uppercase tracking-wider text-stone-500"
            }
          >
            {label}
          </p>
          <p className="mt-2 text-2xl font-semibold tabular-nums">
            {value}
            {unit ? (
              <span
                className={
                  dark
                    ? "ml-1 text-sm font-normal text-brand-200"
                    : "ml-1 text-sm font-normal text-stone-500"
                }
              >
                {unit}
              </span>
            ) : null}
          </p>
        </div>
        <div
          className={
            dark ? "rounded-lg bg-white/15 p-2" : "rounded-lg bg-brand-50 p-2"
          }
        >
          <Icon
            className={dark ? "h-4 w-4 text-white" : "h-4 w-4 text-brand-700"}
            aria-hidden
          />
        </div>
      </div>
    </Card>
  );
}
