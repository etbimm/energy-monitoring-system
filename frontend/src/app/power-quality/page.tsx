"use client";

import { Activity, TriangleAlert, Waves } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { PhaseDeviceDetails } from "@/components/dashboard/phase-device-details";
import { ThdDeviceDetails } from "@/components/dashboard/thd-device-details";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { DataState } from "@/components/ui/data-state";
import { DemoDataNotice } from "@/components/ui/demo-data-notice";
import { getPanelsForDevices } from "@/lib/device-data";
import { useEMSData } from "@/lib/use-ems-data";
import {
  FREQUENCY_THRESHOLDS,
  THD_THRESHOLDS,
  frequencySeverity,
  thdSeverity,
} from "@/lib/meter-models";
import { formatNumber } from "@/lib/format";
import type { Device } from "@/lib/types";

export default function PowerQualityPage() {
  const { devices, loading, error, isDemo } = useEMSData();
  const withTHD = devices.filter(
    (device) => device.status !== "offline" && device.capabilities.thdCurrent,
  );
  const panels = getPanelsForDevices(devices);

  const worst = withTHD.reduce<Device | null>(
    (acc, d) =>
      acc === null || (d.thdCurrent ?? 0) > (acc.thdCurrent ?? 0) ? d : acc,
    null,
  );
  const exceed = withTHD.filter(
    (d) => (d.thdCurrent ?? 0) >= THD_THRESHOLDS.warning,
  );

  // Frekuensi: seluruh meter mendukungnya, tapi meter offline tidak punya data
  const live = devices.filter((d) => d.status !== "offline" && d.frequency > 0);
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
            THD termonitor pada {withTHD.length} dari {devices.length} power meter online
          </span>
        }
      />
      {isDemo ? <DemoDataNotice /> : null}
      <DataState loading={loading} error={error} />

      <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
        <SummaryTile
          label="Meter Termonitor"
          value={String(withTHD.length)}
          unit="meter online"
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
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-1 sm:gap-4">
            {panels.map((p) => {
              const meters = p.devices.filter((d) => d.thdCurrent !== null);
              if (meters.length === 0) return null;
              const maxTHD = Math.max(...meters.map((d) => d.thdCurrent ?? 0));
              const voltageReadings = meters
                .map((device) => device.thdVoltage)
                .filter((value): value is number => value !== null);
              const maxTHDu = voltageReadings.length
                ? Math.max(...voltageReadings)
                : null;
              const sev = thdSeverity(maxTHD);

              return (
                <div key={p.location} className="rounded-lg border border-stone-200 p-3 sm:p-4">
                  <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between sm:gap-3">
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
                        {maxTHDu !== null ? `${formatNumber(maxTHDu)}% THD-U` : "- THD-U"}
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
            <ul className="grid grid-cols-2 gap-2 sm:grid-cols-1">
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

      <ThdDeviceDetails
        devices={withTHD}
        locations={panels.map((panel) => panel.location)}
      />

      <PhaseDeviceDetails
        devices={devices.filter((device) => device.status !== "offline")}
        locations={panels.map((panel) => panel.location)}
      />

    </>
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
          ? "min-w-0 border-brand-900 bg-brand-900 p-3 text-white sm:p-5"
          : "min-w-0 border-stone-200 bg-white p-3 text-stone-900 sm:p-5"
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
          <p className="mt-2 text-xl font-semibold tabular-nums sm:text-2xl">
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
