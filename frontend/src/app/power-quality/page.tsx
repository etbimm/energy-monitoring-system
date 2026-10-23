import { Activity, CircleAlert, TriangleAlert, Waves } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  DEVICES,
  getDevicesWithTHD,
  getDevicesWithoutTHDSupport,
  getPanels,
} from "@/lib/mock-data";
import {
  FREQUENCY_THRESHOLDS,
  THD_THRESHOLDS,
  frequencySeverity,
  thdSeverity,
} from "@/lib/meter-models";
import { formatNumber } from "@/lib/format";
import type { Device } from "@/lib/types";

export default function PowerQualityPage() {
  const withTHD = getDevicesWithTHD();
  const withoutTHD = getDevicesWithoutTHDSupport();
  const panels = getPanels();

  const worst = withTHD.reduce<Device | null>(
    (acc, d) =>
      acc === null || (d.thdCurrent ?? 0) > (acc.thdCurrent ?? 0) ? d : acc,
    null,
  );
  const exceed = withTHD.filter(
    (d) => (d.thdCurrent ?? 0) >= THD_THRESHOLDS.warning,
  );

  // Frekuensi: seluruh meter mendukungnya, tapi meter offline tidak punya data
  const live = DEVICES.filter((d) => d.status !== "offline");
  const freqs = live.map((d) => d.frequency);
  const freqMin = freqs.length ? Math.min(...freqs) : null;
  const freqMax = freqs.length ? Math.max(...freqs) : null;
  const freqOff = live.filter(
    (d) => frequencySeverity(d.frequency) !== "ok",
  ).length;

  return (
    <>
      <PageHeader
        title="Power Quality"
        description="Kualitas daya: THD, unbalance, dan detail per fasa"
        action={
          <span className="text-xs text-stone-500">
            THD tersedia pada {withTHD.length} dari {DEVICES.length} power meter
          </span>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <SummaryTile
          label="Meter Termonitor"
          value={String(withTHD.length)}
          unit={`dari ${DEVICES.length}`}
          icon={Waves}
        />
        <SummaryTile
          label="THD Tertinggi"
          value={
            worst && worst.thdCurrent !== null
              ? formatNumber(worst.thdCurrent)
              : "-"
          }
          unit={worst ? "%" : ""}
          icon={Activity}
          tone={
            worst && thdSeverity(worst.thdCurrent) === "critical"
              ? "danger"
              : "default"
          }
        />
        <SummaryTile
          label="Melewati Ambang"
          value={String(exceed.length)}
          unit={`meter ≥ ${THD_THRESHOLDS.warning}%`}
          icon={TriangleAlert}
          tone={exceed.length > 0 ? "danger" : "default"}
        />
        <SummaryTile
          label="Tanpa Dukungan THD"
          value={String(withoutTHD.length)}
          unit="meter"
          icon={CircleAlert}
        />
        <SummaryTile
          label="Rentang Frekuensi"
          value={
            freqMin !== null && freqMax !== null
              ? `${formatNumber(freqMin, 2)}–${formatNumber(freqMax, 2)}`
              : "-"
          }
          unit="Hz"
          icon={Activity}
          tone={freqOff > 0 ? "danger" : "default"}
        />
      </div>

      <Card className="mt-4">
        <CardHeader
          title="Ringkasan THD per Panel"
          subtitle="Nilai THD arus tertinggi pada tiap panel"
        />
        <CardContent>
          <div className="space-y-4">
            {panels.map((p) => {
              const meters = p.devices.filter((d) => d.thdCurrent !== null);
              if (meters.length === 0) return null;
              const maxTHD = Math.max(...meters.map((d) => d.thdCurrent ?? 0));
              const maxTHDu = Math.max(
                ...meters.map((d) => d.thdVoltage ?? 0),
              );
              const sev = thdSeverity(maxTHD);

              return (
                <div key={p.location}>
                  <div className="flex items-baseline justify-between gap-3">
                    <p className="text-sm font-medium text-stone-900">
                      {p.location}
                      <span className="ml-2 text-xs font-normal text-stone-500">
                        {meters.length} meter termonitor
                      </span>
                    </p>
                    <p className="text-sm tabular-nums text-stone-700">
                      <span
                        className={
                          sev === "critical"
                            ? "font-semibold text-brand-700"
                            : sev === "warning"
                              ? "font-semibold text-amber-600"
                              : "text-stone-700"
                        }
                      >
                        {formatNumber(maxTHD)}% THD-I
                      </span>
                      <span className="ml-3 text-xs text-stone-500">
                        {formatNumber(maxTHDu)}% THD-U
                      </span>
                    </p>
                  </div>
                  <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-stone-100">
                    <div
                      className={
                        sev === "critical"
                          ? "h-full bg-brand-600"
                          : sev === "warning"
                            ? "h-full bg-amber-500"
                            : "h-full bg-emerald-500"
                      }
                      style={{
                        width: `${Math.min(100, (maxTHD / THD_THRESHOLDS.critical) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader
          title="Deviasi Frekuensi"
          subtitle={`Toleransi ±${FREQUENCY_THRESHOLDS.warning} Hz dari nominal ${FREQUENCY_THRESHOLDS.nominal} Hz (IEC 61000-4-30)`}
        />
        <CardContent>
          {live.filter((d) => frequencySeverity(d.frequency) !== "ok").length ===
          0 ? (
            <p className="text-sm text-stone-600">
              Semua power meter dalam toleransi frekuensi. Rentang saat ini{" "}
              {freqMin !== null && freqMax !== null
                ? `${formatNumber(freqMin, 2)} – ${formatNumber(freqMax, 2)} Hz`
                : "-"}
              .
            </p>
          ) : (
            <ul className="space-y-2">
              {live
                .filter((d) => frequencySeverity(d.frequency) !== "ok")
                .map((d) => (
                  <li
                    key={d.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm ring-1 ring-amber-200"
                  >
                    <span>
                      <span className="font-medium text-stone-900">
                        {d.name}
                      </span>
                      <span className="ml-2 text-xs text-stone-500">
                        {d.id} - {d.location}
                      </span>
                    </span>
                    <span className="text-xs font-medium tabular-nums text-amber-800">
                      {formatNumber(d.frequency, 2)} Hz (deviasi{" "}
                      {formatNumber(
                        Math.abs(d.frequency - FREQUENCY_THRESHOLDS.nominal),
                        2,
                      )}{" "}
                      Hz)
                    </span>
                  </li>
                ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader
          title="Detail THD per Power Meter"
          subtitle="Hanya meter yang mendukung pengukuran harmonik"
        />
        <CardContent>
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
                {withTHD.map((d) => {
                  const sev = thdSeverity(d.thdCurrent);
                  return (
                    <tr
                      key={d.id}
                      className="border-b border-stone-100 transition-colors hover:bg-brand-50/60"
                    >
                      <td className="whitespace-nowrap py-3 pr-4">
                        <p className="font-medium text-stone-900">{d.name}</p>
                        <p className="text-xs whitespace-nowrap text-stone-500">
                          {d.id} - {d.location}
                        </p>
                      </td>
                      <td className="py-3 pr-4 text-xs text-stone-600">
                        {d.brand}
                      </td>
                      <td className="py-3 pr-4">
                        <StatusBadge status={d.status} />
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums">
                        <ThdBadge value={d.thdCurrent} severity={sev} />
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums text-stone-700">
                        {d.thdVoltage !== null
                          ? `${formatNumber(d.thdVoltage)}%`
                          : "-"}
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums">
                        <span
                          className={
                            frequencySeverity(d.frequency) === "ok"
                              ? "text-stone-700"
                              : "font-semibold text-brand-700"
                          }
                        >
                          {formatNumber(d.frequency, 2)}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums text-stone-600">
                        {d.unbalanceVoltage !== null
                          ? `${formatNumber(d.unbalanceVoltage)}%`
                          : "-"}
                      </td>
                      <td className="py-3 pr-4 text-right tabular-nums text-stone-600">
                        {d.unbalanceCurrent !== null
                          ? `${formatNumber(d.unbalanceCurrent)}%`
                          : "-"}
                      </td>
                      <td className="py-3 text-right tabular-nums text-xs text-stone-500">
                        s/d {d.capabilities.maxHarmonicOrder}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader
          title="Detail Per Fasa"
          subtitle="Nilai L1/L2/L3 untuk power meter yang mengukur per fasa"
        />
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            {DEVICES.filter((d) => d.status !== "offline").map((d) => (
              <PhaseCard key={d.id} device={d} />
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader
          title="Meter Tanpa Data THD"
          subtitle="Model yang tidak mendukung harmonik, atau opsi /H belum terpasang"
        />
        <CardContent>
          <ul className="space-y-2">
            {withoutTHD.map((d) => (
              <li
                key={d.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-stone-50 px-3 py-2 text-sm ring-1 ring-stone-200"
              >
                <span>
                  <span className="font-medium text-stone-900">{d.name}</span>
                  <span className="ml-2 text-xs text-stone-500">
                    {d.id} - {d.brand}
                  </span>
                </span>
                <span className="text-xs text-stone-500">
                  {d.status === "offline"
                    ? "Device offline - tidak ada data"
                    : d.capabilities.thdCurrent
                      ? "Opsi /H belum terpasang"
                      : "Model tanpa dukungan harmonik"}
                </span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </>
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

function PhaseCard({ device: d }: { device: Device }) {
  return (
    <div className="rounded-lg border border-stone-200 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-stone-900">{d.name}</p>
          <p className="truncate text-xs text-stone-500">
            {d.brand} - {d.location}
          </p>
        </div>
        <StatusBadge status={d.status} />
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
            {d.phases.map((p) => (
              <tr key={p.phase} className="border-t border-stone-100">
                <td className="py-1.5 pr-3 font-medium text-stone-700">
                  {p.phase}
                </td>
                <td className="py-1.5 pr-3 text-right tabular-nums text-stone-700">
                  {p.voltage !== null ? formatNumber(p.voltage, 0) : "-"}
                </td>
                <td className="py-1.5 pr-3 text-right tabular-nums text-stone-700">
                  {p.current !== null ? formatNumber(p.current) : "-"}
                </td>
                <td className="py-1.5 pr-3 text-right tabular-nums text-stone-900">
                  {p.power !== null ? formatNumber(p.power) : "-"}
                </td>
                <td className="py-1.5 pr-3 text-right tabular-nums text-stone-600">
                  {p.apparentPower !== null ? formatNumber(p.apparentPower) : "-"}
                </td>
                <td className="py-1.5 pr-3 text-right tabular-nums text-stone-600">
                  {p.reactivePower !== null
                    ? formatNumber(p.reactivePower)
                    : "-"}
                </td>
                <td className="py-1.5 text-right tabular-nums text-stone-600">
                  {p.thdCurrent !== null
                    ? `${formatNumber(p.thdCurrent)}%`
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
  icon: typeof Waves;
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
