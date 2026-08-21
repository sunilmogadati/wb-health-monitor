"use client";

import { useState } from "react";
import {
  getBrief,
  getForecast,
  getPrediction,
  type CountryBrief,
  type CountrySummary,
  type ForecastResponse,
  type Performance,
  type Prediction,
} from "@/lib/api";

const OBSERVED_YEARS = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022];
const FUTURE_YEARS = [2023, 2024, 2025, 2026, 2027, 2028];
const LATEST_OBSERVED = 2022;

// Association language only (Principle V) — never best/worst/failing.
const BAND_LABEL: Record<Performance, string> = {
  above_expected: "above what spending predicts",
  near_expected: "near what spending predicts",
  below_expected: "below what spending predicts",
};

// Pretty-print a projected feature value: money vs. percentages vs. rates.
function fmt(feature: string, value: number): string {
  if (feature === "gdp_per_capita") return `$${Math.round(value).toLocaleString()}`;
  if (feature.endsWith("_pct") || feature.includes("spend")) return `${value.toFixed(1)}%`;
  return value.toFixed(2);
}

type ObservedResult = { kind: "observed"; prediction: Prediction; brief: CountryBrief };
type ForecastResult = { kind: "forecast"; forecast: ForecastResponse };
type Result = ObservedResult | ForecastResult;

// The ML, made explicit. For an observed year (≤2022) the model's predicted vs actual life
// expectancy + a Claude-written value-for-money brief (`/predict`+`/brief`). For a FUTURE year the
// model scores *projected* inputs (`/forecast`) — a labelled scenario, never a measurement.
export function PredictionPanel({ countries }: { countries: CountrySummary[] }) {
  const [country, setCountry] = useState("");
  const [year, setYear] = useState(2020);
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isFuture = year > LATEST_OBSERVED;

  async function run() {
    if (!country) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      if (year > LATEST_OBSERVED) {
        const forecast = await getForecast(country, year);
        setResult({ kind: "forecast", forecast });
      } else {
        const [prediction, brief] = await Promise.all([
          getPrediction(country, year),
          getBrief(country, year),
        ]);
        setResult({ kind: "observed", prediction, brief });
      }
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
            <optgroup label="Observed (from the data)">
              {OBSERVED_YEARS.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </optgroup>
            <optgroup label="Forecast (projected inputs)">
              {FUTURE_YEARS.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </optgroup>
          </select>
        </label>
        <button
          type="button"
          onClick={run}
          disabled={loading || !country}
          className="rounded bg-slate-800 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? "Running…" : isFuture ? "Forecast & explain" : "Predict & explain"}
        </button>
      </div>

      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}

      {result?.kind === "observed" && (
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
                {result.brief.residual.toFixed(1)} yrs ·{" "}
                {BAND_LABEL[result.brief.performance_vs_spend]}
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

      {result?.kind === "forecast" && (
        <div className="space-y-3 rounded-lg border border-amber-300 bg-amber-50 p-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded-full bg-amber-200 px-2 py-0.5 text-xs font-semibold text-amber-900">
              Forecast · {result.forecast.year}
            </span>
            <div>
              <span className="text-xs text-slate-500">Forecast life expectancy </span>
              <span className="text-lg font-semibold text-slate-900">
                {result.forecast.forecast_life_expectancy.toFixed(1)} yrs
              </span>
            </div>
          </div>
          <div>
            <div className="mb-1 text-xs font-medium text-slate-600">
              Projected inputs the model scored (extrapolated from{" "}
              {result.forecast.based_on_years[0]}–
              {result.forecast.based_on_years[result.forecast.based_on_years.length - 1]}):
            </div>
            <ul className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-800">
              {Object.entries(result.forecast.projected_indicators).map(([feature, value]) => (
                <li key={feature}>
                  <span className="text-slate-500">{feature}:</span> {fmt(feature, value)}
                </li>
              ))}
            </ul>
          </div>
          <p className="text-xs text-amber-800">{result.forecast.caveat}</p>
          <p className="text-xs text-slate-500">
            Model: <span className="font-medium">{result.forecast.model}</span>
          </p>
        </div>
      )}
    </div>
  );
}
