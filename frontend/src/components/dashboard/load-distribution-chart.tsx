"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatNumber } from "@/lib/format";

const COLORS = [
  "#8d1c1c",
  "#a33b3b",
  "#c05a5a",
  "#d98080",
  "#8d4a4a",
  "#b04a4a",
];

const tooltipStyle = {
  backgroundColor: "#ffffff",
  border: "1px solid #e7e5e4",
  borderRadius: "8px",
  fontSize: "12px",
  color: "#0a0a0a",
  boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
};

export function LoadDistributionChart({
  data,
}: {
  data: { name: string; power: number }[];
}) {
  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 5, right: 20, left: 10, bottom: 0 }}
        >
          <XAxis
            type="number"
            stroke="#78716c"
            fontSize={11}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            stroke="#57534e"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            width={130}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            cursor={{ fill: "#f5f5f4" }}
            formatter={(value: number) => [`${formatNumber(value)} kW`, "Daya"]}
          />
          <Bar dataKey="power" radius={[0, 4, 4, 0]} barSize={18}>
            {data.map((entry, i) => (
              <Cell key={entry.name} fill={COLORS[i % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}