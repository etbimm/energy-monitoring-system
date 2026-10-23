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
}: {
  data: TimeSeriesPoint[];
  series: ChartSeries[];
}) {
  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
            dataKey="label"
            stroke="#78716c"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            interval={2}
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
