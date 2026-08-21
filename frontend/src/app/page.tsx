"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  type BenchmarkResponse,
  type CompareRow,
  type CountrySummary,
  type ForecastSeriesResponse,
  type TimeSeriesPoint,
  PROJECTABLE_INDICATORS,
  getBenchmark,
  getCompare,
  getCountries,
  getForecastSeries,
  getTimeSeries,
} from "@/lib/api";
import { AgentPanel } from "@/components/AgentPanel";
import { AskPanel } from "@/components/AskPanel";
import { BenchmarkChart } from "@/components/BenchmarkChart";
import { CompareChart } from "@/components/CompareChart";
import { PredictionPanel } from "@/components/PredictionPanel";
import { TrendChart } from "@/components/TrendChart";
import { DEFAULT_INDICATOR, INDICATORS } from "@/lib/constants";

const YEARS = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022];

function indicatorLabel(code: string): string {
  return INDICATORS.find((i) => i.code === code)?.label ?? code;
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800">
      {message}
    </div>
  );
}

function SectionCard({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      {hint ? (
        <p className="mb-4 mt-1 text-xs text-slate-500">{hint}</p>
      ) : (
        <div className="mb-4" />
      )}
      {children}
    </section>
  );
}

export default function DashboardPage() {
  const [countries, setCountries] = useState<CountrySummary[] | null>(null);
  const [countriesError, setCountriesError] = useState<string | null>(null);

  const [benchmarkYear, setBenchmarkYear] = useState(2022);
  const [benchmark, setBenchmark] = useState<BenchmarkResponse | null>(null);
  const [benchmarkError, setBenchmarkError] = useState<string | null>(null);

  const [trendCountry, setTrendCountry] = useState<string>("");
  const [trendIndicator, setTrendIndicator] = useState<string>(DEFAULT_INDICATOR);
  const [trendPoints, setTrendPoints] = useState<TimeSeriesPoint[] | null>(null);
  const [trendForecast, setTrendForecast] = useState<ForecastSeriesResponse | null>(null);
  const [trendError, setTrendError] = useState<string | null>(null);

  const [compareIndicator, setCompareIndicator] = useState<string>(DEFAULT_INDICATOR);
  const [compareCountries, setCompareCountries] = useState<string[]>([]);
  const [compareRows, setCompareRows] = useState<CompareRow[] | null>(null);
  const [compareError, setCompareError] = useState<string | null>(null);

  // Load the country list once; this also doubles as the "is the API reachable at all" check.
  useEffect(() => {
    getCountries()
      .then((data) => {
        setCountries(data);
        if (data.length > 0) {
          setTrendCountry(data[0].country_code);
          setCompareCountries(data.slice(0, 2).map((c) => c.country_code));
        }
      })
      .catch((error: unknown) => {
        setCountriesError(error instanceof Error ? error.message : "Failed to reach the API.");
      });
  }, []);

  useEffect(() => {
    getBenchmark(benchmarkYear)
      .then((data) => {
        setBenchmark(data);
        setBenchmarkError(null);
      })
      .catch((error: unknown) => {
        setBenchmarkError(error instanceof Error ? error.message : "Failed to load the benchmark.");
      });
  }, [benchmarkYear]);

  useEffect(() => {
    if (!trendCountry) return;
    getTimeSeries(trendCountry, trendIndicator)
      .then((data) => {
        setTrendPoints(data);
        setTrendError(null);
      })
      .catch((error: unknown) => {
        setTrendError(error instanceof Error ? error.message : "Failed to load the trend.");
      });
  }, [trendCountry, trendIndicator]);

  // The forecast continuation for the trend chart — only for indicators with a projection path
  // (the model's target + its inputs). A failure here is non-fatal: the observed line still renders.
  // We never reset synchronously; render filters by matching indicator so a stale series can't show.
  useEffect(() => {
    if (!trendCountry || !PROJECTABLE_INDICATORS.has(trendIndicator)) return;
    getForecastSeries(trendCountry, trendIndicator)
      .then((series) => setTrendForecast(series))
      .catch(() => setTrendForecast(null));
  }, [trendCountry, trendIndicator]);

  useEffect(() => {
    if (compareCountries.length === 0) return;
    getCompare(compareCountries, compareIndicator)
      .then((data) => {
        setCompareRows(data);
        setCompareError(null);
      })
      .catch((error: unknown) => {
        setCompareError(error instanceof Error ? error.message : "Failed to load the comparison.");
      });
  }, [compareCountries, compareIndicator]);

  function toggleCompareCountry(code: string) {
    setCompareCountries((current) =>
      current.includes(code) ? current.filter((c) => c !== code) : [...current, code],
    );
  }

  const trendCountryName =
    countries?.find((c) => c.country_code === trendCountry)?.country_name ?? trendCountry;

  // Only use the fetched forecast if it matches the currently-selected indicator (guards against a
  // stale series flashing after the indicator is switched, before the new fetch resolves).
  const activeForecast =
    trendForecast &&
    trendForecast.indicator === trendIndicator &&
    PROJECTABLE_INDICATORS.has(trendIndicator)
      ? trendForecast
      : null;

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-bold text-slate-900">Health &amp; Spending Analytics</h1>
        <p className="text-sm text-slate-600">
          Sub-Saharan Africa, 2015–2022 (World Bank public data). Ask a plain-English question, see
          the model&apos;s prediction for a country, and explore value-for-money, indicator trends, and
          comparisons. Every figure is an <strong>association with health spending — never a causal or
          performance judgement</strong> (&ldquo;above/below what spending predicts&rdquo;, not
          &ldquo;best/worst&rdquo;).
        </p>
      </header>

      {countriesError && (
        <ErrorBanner
          message={`Can't reach the analytics API: ${countriesError}. Check that the API is running and NEXT_PUBLIC_API_BASE is set.`}
        />
      )}

      <SectionCard
        title="Ask AI"
        hint="Ask a plain-English question — you get a grounded answer plus the exact rows behind it. Works for trends, comparisons, and value-for-money."
      >
        <AskPanel />
      </SectionCard>

      <SectionCard
        title="AI agent (multi-step)"
        hint="A LangGraph agent that plans, calls several tools in sequence, then answers — and shows you the steps it took. Use it for multi-part questions (a trend AND a comparison) that the single-shot Ask AI can't chain."
      >
        <AgentPanel />
      </SectionCard>

      <SectionCard
        title="Model prediction &amp; brief"
        hint="For an observed year (2015–2022) the model predicts what life expectancy a country should have given its spending — the gap to actual is the value-for-money residual. For a future year (2023–2028) it projects each input forward and forecasts, clearly labelled as a scenario, not a measurement."
      >
        <PredictionPanel countries={countries ?? []} />
      </SectionCard>

      <SectionCard
        title="Value-for-money benchmark"
        hint="Countries ranked by residual (actual − predicted life expectancy). Right of centre = more life expectancy than spending predicts; left = less. Never best/worst."
      >
        <label className="mb-3 block text-sm text-slate-700">
          Year{" "}
          <select
            className="ml-2 rounded border border-slate-300 px-2 py-1"
            value={benchmarkYear}
            onChange={(e) => setBenchmarkYear(Number(e.target.value))}
          >
            {YEARS.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </label>
        {benchmarkError && <ErrorBanner message={benchmarkError} />}
        {!benchmarkError && benchmark && <BenchmarkChart data={benchmark} />}
        {!benchmarkError && !benchmark && <p className="text-sm text-slate-500">Loading…</p>}
      </SectionCard>

      <SectionCard
        title="Indicator trend"
        hint="One country's indicator over the years. The solid line is observed data; a dashed amber line continues it into the future (2023–2028) — for life expectancy that's the model's forecast, for a model input it's a trend projection. A gap in the solid line is a value the data-quality gate removed."
      >
        <div className="mb-3 flex flex-wrap gap-4 text-sm text-slate-700">
          <label>
            Country{" "}
            <select
              className="ml-2 rounded border border-slate-300 px-2 py-1"
              value={trendCountry}
              onChange={(e) => setTrendCountry(e.target.value)}
            >
              {countries?.map((c) => (
                <option key={c.country_code} value={c.country_code}>
                  {c.country_name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Indicator{" "}
            <select
              className="ml-2 rounded border border-slate-300 px-2 py-1"
              value={trendIndicator}
              onChange={(e) => setTrendIndicator(e.target.value)}
            >
              {INDICATORS.map((i) => (
                <option key={i.code} value={i.code}>
                  {i.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        {trendError && <ErrorBanner message={trendError} />}
        {!trendError && trendPoints && (
          <TrendChart
            countryName={trendCountryName}
            indicatorLabel={indicatorLabel(trendIndicator)}
            points={trendPoints}
            projected={activeForecast?.points}
            projectionBasis={activeForecast?.basis}
          />
        )}
        {!trendError && trendPoints && activeForecast && activeForecast.basis !== "none" && (
          <p className="mt-2 text-xs text-amber-800">
            <span className="font-medium">Dashed = forecast.</span> {activeForecast.caveat}
          </p>
        )}
        {!trendError && trendPoints && !PROJECTABLE_INDICATORS.has(trendIndicator) && (
          <p className="mt-2 text-xs text-slate-500">
            No forecast for this indicator — it is neither the model&apos;s target nor one of its
            inputs, so the model can&apos;t project it.
          </p>
        )}
        {!trendError && !trendPoints && <p className="text-sm text-slate-500">Loading…</p>}
      </SectionCard>

      <SectionCard
        title="Compare countries"
        hint="Several countries on one indicator, over time — select countries below to overlay them."
      >
        <div className="mb-3 space-y-2 text-sm text-slate-700">
          <label className="block">
            Indicator{" "}
            <select
              className="ml-2 rounded border border-slate-300 px-2 py-1"
              value={compareIndicator}
              onChange={(e) => setCompareIndicator(e.target.value)}
            >
              {INDICATORS.map((i) => (
                <option key={i.code} value={i.code}>
                  {i.label}
                </option>
              ))}
            </select>
          </label>
          <fieldset className="flex flex-wrap gap-3">
            <legend className="sr-only">Countries to compare</legend>
            {countries?.map((c) => (
              <label key={c.country_code} className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={compareCountries.includes(c.country_code)}
                  onChange={() => toggleCompareCountry(c.country_code)}
                />
                {c.country_name}
              </label>
            ))}
          </fieldset>
        </div>
        {compareError && <ErrorBanner message={compareError} />}
        {!compareError && compareCountries.length === 0 && (
          <p className="text-sm text-slate-500">Select at least one country to compare.</p>
        )}
        {!compareError && compareCountries.length > 0 && compareRows && (
          <CompareChart indicatorLabel={indicatorLabel(compareIndicator)} rows={compareRows} />
        )}
        {!compareError && compareCountries.length > 0 && !compareRows && (
          <p className="text-sm text-slate-500">Loading…</p>
        )}
      </SectionCard>
    </main>
  );
}
