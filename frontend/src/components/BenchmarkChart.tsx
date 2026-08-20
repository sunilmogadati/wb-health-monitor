"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BenchmarkBand, BenchmarkResponse, BenchmarkRow } from "@/lib/api";

// Association language only (Principle V, FR-003) — never "best"/"worst"/"failing".
const BAND_LABEL: Record<BenchmarkBand, string> = {
  above: "above what spending predicts",
  near: "near what spending predicts",
  below: "below what spending predicts",
};

const BAND_COLOR: Record<BenchmarkBand, string> = {
  above: "#0f766e",
  near: "#64748b",
  below: "#b45309",
};

export function bandLabel(band: BenchmarkBand): string {
  return BAND_LABEL[band];
}

interface BenchmarkChartProps {
  data: BenchmarkResponse;
}

export function BenchmarkChart({ data }: BenchmarkChartProps) {
  if (!data.model_built) {
    return (
      <div
        role="status"
        className="rounded-lg border border-dashed border-slate-300 p-6 text-sm text-slate-600"
      >
        Model not built yet — the value-for-money benchmark will appear once a model has been
        trained (spec 002).
      </div>
    );
  }

  if (data.rows.length === 0) {
    return (
      <div role="status" className="rounded-lg border border-slate-200 p-6 text-sm text-slate-600">
        No benchmark rows for this year.
      </div>
    );
  }

  const sorted = [...data.rows].sort((a, b) => b.residual - a.residual);

  return (
    <div>
      <ResponsiveContainer width="100%" height={Math.max(240, sorted.length * 28)}>
        <BarChart data={sorted} layout="vertical" margin={{ left: 24 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" label={{ value: "Residual (years)", position: "insideBottom", offset: -5 }} />
          <YAxis type="category" dataKey="country_name" width={120} />
          <Tooltip
            formatter={(value, _name, item) => {
              const band = (item?.payload as BenchmarkRow | undefined)?.band;
              const residual = typeof value === "number" ? value.toFixed(1) : value;
              return [`${residual} yrs ${band ? BAND_LABEL[band] : ""}`, "Residual"];
            }}
          />
          <Bar dataKey="residual">
            {sorted.map((row) => (
              <Cell key={row.country_code} fill={BAND_COLOR[row.band]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="mt-2 text-xs text-slate-500">
        Residual = actual − predicted life expectancy. An association with health spending and
        context, not a causal claim or performance judgement.
      </p>
      {/* Text alternative to the SVG chart, for screen readers and non-visual clients. */}
      <ul className="sr-only">
        {sorted.map((row) => (
          <li key={row.country_code}>
            {row.country_name}: {row.residual.toFixed(1)} years {BAND_LABEL[row.band]}
          </li>
        ))}
      </ul>
    </div>
  );
}
