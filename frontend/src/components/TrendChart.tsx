"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TimeSeriesPoint } from "@/lib/api";

interface TrendChartProps {
  countryName: string;
  indicatorLabel: string;
  points: TimeSeriesPoint[];
}

export function TrendChart({ countryName, indicatorLabel, points }: TrendChartProps) {
  if (points.length === 0) {
    return (
      <div role="status" className="rounded-lg border border-slate-200 p-6 text-sm text-slate-600">
        No {indicatorLabel} data for {countryName}.
      </div>
    );
  }

  const sorted = [...points].sort((a, b) => a.year - b.year);
  const withData = sorted.filter((p) => p.value !== null);

  return (
    <div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={sorted}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="year" />
          <YAxis domain={["auto", "auto"]} />
          <Tooltip />
          {/* connectNulls defaults to false: a missing value renders as a gap, not a dip to zero. */}
          <Line
            type="monotone"
            dataKey="value"
            name={`${countryName} — ${indicatorLabel}`}
            stroke="#0f766e"
            dot
          />
        </LineChart>
      </ResponsiveContainer>
      {/* Text alternative to the SVG chart, for screen readers and non-visual clients. */}
      <p className="sr-only">
        {countryName} — {indicatorLabel}, {sorted[0]?.year}–{sorted[sorted.length - 1]?.year}:{" "}
        {withData.map((p) => `${p.year}: ${p.value}`).join(", ")}
      </p>
    </div>
  );
}
