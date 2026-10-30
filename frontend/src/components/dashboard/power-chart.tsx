"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TimeSeriesPoint } from "@/lib/types";
import { formatNumber } from "@/lib/format";

const tooltipStyle = {
  backgroundColor: "#ffffff",
  border: "1px solid #e7e5e4",
  borderRadius: "8px",
  fontSize: "12px",
  color: "#0a0a0a",
  boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
};

function formatAxisTime(value: number): string {
  return new Date(value).toLocaleTimeString("id-ID", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).replace(":", ".");
}

function XAxisTick({
  x = 0,
  y = 0,
  payload,
  mode,
  spansMultipleDays,
}: {
  x?: number;
  y?: number;
  payload?: { value?: number };
  mode: "time" | "date" | "full-day";
  spansMultipleDays: boolean;
}) {
  const timestamp = Number(payload?.value);
  if (!Number.isFinite(timestamp)) return null;

  const date = new Date(timestamp);
  const dateLabel = date.toLocaleDateString("id-ID", {
    day: "2-digit",
    month: "2-digit",
  });

  if (mode === "date") {
    return (
      <g transform={`translate(${x},${y})`}>
        <text textAnchor="middle" fill="#78716c" fontSize={11} dy={14}>
          {dateLabel}
        </text>
      </g>
    );
  }

  if (mode === "full-day") {
    const timeLabel =
      date.getHours() === 23 && date.getMinutes() === 59
        ? "23:59"
        : formatAxisTime(timestamp);
    return (
      <g transform={`translate(${x},${y})`}>
        <text textAnchor="middle" fill="#78716c" fontSize={11} dy={14}>
          {timeLabel}
        </text>
      </g>
    );
  }

  return (
    <g transform={`translate(${x},${y})`}>
      <text textAnchor="middle" fill="#78716c" fontSize={10}>
        {spansMultipleDays ? (
          <>
            <tspan x={0} dy={11}>{dateLabel}</tspan>
            <tspan x={0} dy={13}>{formatAxisTime(timestamp)}</tspan>
          </>
        ) : (
          <tspan x={0} dy={14}>{formatAxisTime(timestamp)}</tspan>
        )}
      </text>
    </g>
  );
}

/** Kunci data yang bisa ditampilkan pada chart */
export type ChartKey =
  | "power"
  | "apparentPower"
  | "reactivePower"
  | "energy"
  | "energyReactive"
  | "energyApparent";

export interface ChartSeries {
  key: ChartKey;
  label: string;
  unit: string;
  color: string;
  /** area = diisi, line = garis saja */
  variant?: "area" | "line";
  dashed?: boolean;
}

/** Seri standar: daya aktif */
export const POWER_SERIES: ChartSeries[] = [
  { key: "power", label: "Daya Aktif", unit: "kW", color: "#8d1c1c", variant: "area" },
];

/** Seri lengkap: kW + kVA + kVAR */
export const POWER_QUALITY_SERIES: ChartSeries[] = [
  { key: "power", label: "Daya Aktif", unit: "kW", color: "#8d1c1c", variant: "area" },
  { key: "apparentPower", label: "Daya Semu", unit: "kVA", color: "#b04a4a", variant: "line" },
  { key: "reactivePower", label: "Daya Reaktif", unit: "kVAR", color: "#d98080", variant: "line" },
];

export function PowerChart({
  data,
  series,
  xAxisMode = "time",
}: {
  data: TimeSeriesPoint[];
  series: ChartSeries[];
  xAxisMode?: "time" | "date" | "full-day";
}) {
  const chartData = data
    .map((point) => ({
      ...point,
      timestampValue: new Date(point.timestamp).getTime(),
    }))
    .filter((point) => Number.isFinite(point.timestampValue))
    .sort((a, b) => a.timestampValue - b.timestampValue)
    .filter(
      (point, index, points) =>
        index === 0 || point.timestampValue !== points[index - 1].timestampValue,
    );
  const firstPointDate = new Date(chartData[0]?.timestampValue ?? Date.now());
  firstPointDate.setHours(0, 0, 0, 0);
  const dayStart = firstPointDate.getTime();
  const dayEnd = new Date(dayStart);
  dayEnd.setHours(23, 59, 59, 999);
  const dayTicks = [0, 6, 12, 18].map(
    (hour) => dayStart + hour * 60 * 60 * 1000,
  );
  dayTicks.push(dayEnd.getTime());
  const firstTimestamp = chartData[0]?.timestampValue;
  const lastTimestamp = chartData[chartData.length - 1]?.timestampValue;
  const spansMultipleDays =
    firstTimestamp !== undefined &&
    lastTimestamp !== undefined &&
    new Date(firstTimestamp).toDateString() !== new Date(lastTimestamp).toDateString();
  const timeDomain =
    firstTimestamp === undefined || lastTimestamp === undefined
      ? [0, 1]
      : firstTimestamp === lastTimestamp
        ? [firstTimestamp - 30 * 60 * 1000, lastTimestamp + 30 * 60 * 1000]
        : [firstTimestamp, lastTimestamp];

  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="powerFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#8d1c1c" stopOpacity={0.28} />
              <stop offset="100%" stopColor="#8d1c1c" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="apparentFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#b04a4a" stopOpacity={0.2} />
              <stop offset="100%" stopColor="#b04a4a" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#e7e5e4" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="timestampValue"
            type="number"
            scale="time"
            domain={
              xAxisMode === "full-day"
                ? [dayStart, dayEnd.getTime()]
                : timeDomain
            }
            ticks={xAxisMode === "full-day" ? dayTicks : undefined}
            tickCount={6}
            tick={
              <XAxisTick
                mode={xAxisMode}
                spansMultipleDays={spansMultipleDays}
              />
            }
            stroke="#78716c"
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="#78716c"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => `${v}`}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            labelStyle={{ color: "#57534e" }}
            labelFormatter={(value) => {
              const timestamp = Number(value);
              if (!Number.isFinite(timestamp)) return String(value);

              const date = new Date(timestamp);
              if (xAxisMode === "date") {
                return date.toLocaleDateString("id-ID", {
                  day: "2-digit",
                  month: "long",
                  year: "numeric",
                });
              }

              const time = formatAxisTime(timestamp);
              if (xAxisMode === "full-day" || !spansMultipleDays) return time;

              const dateLabel = date.toLocaleDateString("id-ID", {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
              });
              return `${dateLabel} ${time}`;
            }}
            formatter={(value: number, name: string) => {
              const s = series.find((x) => x.key === name);
              return [
                `${formatNumber(value)} ${s?.unit ?? ""}`,
                s?.label ?? name,
              ];
            }}
          />
          {series.length > 1 ? <Legend /> : null}
          {series.map((s) =>
            s.variant === "area" ? (
              <Area
                key={s.key}
                type="monotone"
                dataKey={s.key}
                stroke={s.color}
                strokeWidth={2}
                fill={s.key === "power" ? "url(#powerFill)" : "url(#apparentFill)"}
                name={s.key}
                dot={false}
              />
            ) : (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                stroke={s.color}
                strokeWidth={1.8}
                strokeDasharray={s.dashed ? "4 3" : undefined}
                dot={false}
                name={s.key}
              />
            ),
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
