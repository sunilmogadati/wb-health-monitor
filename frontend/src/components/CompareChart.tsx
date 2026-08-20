"use client";

import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CompareRow } from "@/lib/api";

const LINE_COLORS = ["#0f766e", "#b45309", "#334155", "#7c3aed", "#0369a1", "#be123c"];

interface Country {
  code: string;
  name: string;
}

/** Pivots flat compare rows into one row per year, one column per country (Recharts' shape). */
export function pivotCompareRows(rows: CompareRow[]): {
  data: Record<string, number | null>[];
  countries: Country[];
} {
  const years = [...new Set(rows.map((r) => r.year))].sort((a, b) => a - b);
  const countryByCode = new Map<string, string>();
  for (const row of rows) countryByCode.set(row.country_code, row.country_name);

  const data = years.map((year) => {
    const point: Record<string, number | null> = { year };
    for (const code of countryByCode.keys()) {
      const match = rows.find((r) => r.year === year && r.country_code === code);
      point[code] = match ? match.value : null;
    }
    return point;
  });

  const countries = [...countryByCode.entries()].map(([code, name]) => ({ code, name }));
  return { data, countries };
}

interface CompareChartProps {
  indicatorLabel: string;
  rows: CompareRow[];
}

export function CompareChart({ indicatorLabel, rows }: CompareChartProps) {
  if (rows.length === 0) {
    return (
      <div role="status" className="rounded-lg border border-slate-200 p-6 text-sm text-slate-600">
        No {indicatorLabel} data for the selected countries.
      </div>
    );
  }

  const { data, countries } = pivotCompareRows(rows);

  return (
    <div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="year" />
          <YAxis domain={["auto", "auto"]} />
          <Tooltip />
          <Legend />
          {countries.map((country, index) => (
            <Line
              key={country.code}
              type="monotone"
              dataKey={country.code}
              name={country.name}
              stroke={LINE_COLORS[index % LINE_COLORS.length]}
              dot
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      {/* Text alternative to the SVG chart, for screen readers and non-visual clients. */}
      <ul className="sr-only">
        {countries.map((country) => (
          <li key={country.code}>{country.name}</li>
        ))}
      </ul>
    </div>
  );
}
