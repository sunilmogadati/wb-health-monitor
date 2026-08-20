"use client";

import { useState } from "react";
import {
  getBrief,
  getPrediction,
  type CountryBrief,
  type CountrySummary,
  type Performance,
  type Prediction,
} from "@/lib/api";

const YEARS = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022];

// Association language only (Principle V) — never best/worst/failing.
const BAND_LABEL: Record<Performance, string> = {
  above_expected: "above what spending predicts",
  near_expected: "near what spending predicts",
  below_expected: "below what spending predicts",
};

// The ML, made explicit: the model's predicted vs actual life expectancy for a country-year
// (`/predict`) plus a grounded, Claude-written explanation of the value-for-money gap (`/brief`).
export function PredictionPanel({ countries }: { countries: CountrySummary[] }) {
  const [country, setCountry] = useState("");
  const [year, setYear] = useState(2020);
  const [result, setResult] = useState<{ prediction: Prediction; brief: CountryBrief } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!country) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const [prediction, brief] = await Promise.all([
        getPrediction(country, year),
        getBrief(country, year),
      ]);
      setResult({ prediction, brief });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run the model.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3 text-sm text-slate-700">
        <label>
          Country{" "}
          <select
            className="ml-2 rounded border border-slate-300 px-2 py-1"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
          >
            <option value="">Select…</option>
            {countries.map((c) => (
              <option key={c.country_code} value={c.country_code}>
                {c.country_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Year{" "}
          <select
            className="ml-2 rounded border border-slate-300 px-2 py-1"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          >
            {YEARS.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={run}
          disabled={loading || !country}
          className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? "Running…" : "Predict & explain"}
        </button>
      </div>

      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error} <span className="text-slate-500">(data covers 2015–2022 only — the model reads
          each year&apos;s real features, so it can&apos;t predict a future year.)</span>
        </p>
      )}

      {result && (
        <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div className="flex flex-wrap gap-8 text-sm">
            <div>
              <div className="text-xs text-slate-500">Model predicted</div>
              <div className="text-lg font-semibold text-slate-900">
                {result.brief.predicted_life_expectancy.toFixed(1)} yrs
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Actual</div>
              <div className="text-lg font-semibold text-slate-900">
                {result.brief.actual_life_expectancy.toFixed(1)} yrs
              </div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Residual — value for money</div>
              <div className="text-lg font-semibold text-slate-900">
                {result.brief.residual > 0 ? "+" : ""}
                {result.brief.residual.toFixed(1)} yrs · {BAND_LABEL[result.brief.performance_vs_spend]}
              </div>
            </div>
          </div>
          <p className="text-sm text-slate-900">{result.brief.summary}</p>
          <p className="text-xs text-slate-500">
            Model: <span className="font-medium">{result.prediction.model}</span> · features:{" "}
            {Object.keys(result.brief.indicators).join(", ")}
          </p>
        </div>
      )}
    </div>
  );
}
