"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ForecastBasis, TimeSeriesPoint } from "@/lib/api";

interface ForecastPoint {
  year: number;
  value: number;
}

interface TrendChartProps {
  countryName: string;
  indicatorLabel: string;
  points: TimeSeriesPoint[];
  projected?: ForecastPoint[];
  projectionBasis?: ForecastBasis;
}

type Row = { year: number; value: number | null; forecast?: number | null };

export function TrendChart({
  countryName,
  indicatorLabel,
  points,
  projected = [],
  projectionBasis = "none",
}: TrendChartProps) {
  if (points.length === 0) {
    return (
      <div role="status" className="rounded-lg border border-slate-200 p-6 text-sm text-slate-600">
        No {indicatorLabel} data for {countryName}.
      </div>
    );
  }

  const sorted = [...points].sort((a, b) => a.year - b.year);
  const withData = sorted.filter((p) => p.value !== null);

  // Build the chart rows: observed points carry `value`; projected points carry `forecast`. To make
  // the dashed forecast line start *from* the last observed point (a continuous line, not a floating
  // segment), that last observed point is seeded with a `forecast` equal to its own value.
  const rows: Row[] = sorted.map((p) => ({ year: p.year, value: p.value }));
  const hasForecast = projected.length > 0 && projectionBasis !== "none";
  if (hasForecast && withData.length > 0) {
    const lastObserved = withData[withData.length - 1];
    const seed = rows.find((r) => r.year === lastObserved.year);
    if (seed) seed.forecast = lastObserved.value;
    for (const fp of [...projected].sort((a, b) => a.year - b.year)) {
      rows.push({ year: fp.year, value: null, forecast: fp.value });
    }
  }

  return (
    <div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={rows}>
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
          {hasForecast && (
            <Line
              type="monotone"
              dataKey="forecast"
              name="Forecast"
              stroke="#d97706"
              strokeDasharray="5 4"
              connectNulls
              dot
            />
          )}
        </LineChart>
      </ResponsiveContainer>
      {/* Text alternative to the SVG chart, for screen readers and non-visual clients. */}
      <p className="sr-only">
        {countryName} — {indicatorLabel}, {sorted[0]?.year}–{sorted[sorted.length - 1]?.year}:{" "}
        {withData.map((p) => `${p.year}: ${p.value}`).join(", ")}
        {hasForecast
          ? `. Forecast (${projectionBasis}): ${projected.map((p) => `${p.year}: ${p.value}`).join(", ")}.`
          : ""}
      </p>
    </div>
  );
}
