/**
 * Typed client for the spec-005 analytics read API. This is the ONLY place the dashboard talks to
 * the network — every component goes through these functions (FR-007), so the endpoint contract
 * lives in one place and the UI never touches the database directly (FR-005, Principle III).
 *
 * Spec 005 hadn't merged when this was built (see specs/006-analytics-dashboard/spec.md "Notes for
 * the plan phase"), so these types are this client's best-effort match to the 005 "Key Entities"
 * contract. The /compare row shape and the always-present `model_built` envelope on /benchmark
 * aren't pinned down verbatim in the spec text — reconcile against the live API once 005 lands.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

export interface CountrySummary {
  country_code: string;
  country_name: string;
}

export interface TimeSeriesPoint {
  year: number;
  indicator: string;
  value: number | null;
}

export interface CompareRow {
  country_code: string;
  country_name: string;
  year: number;
  indicator: string;
  value: number | null;
}

export type BenchmarkBand = "above" | "near" | "below";

export interface BenchmarkRow {
  country_code: string;
  country_name: string;
  year: number;
  actual: number;
  predicted: number;
  residual: number;
  band: BenchmarkBand;
}

export interface BenchmarkResponse {
  model_built: boolean;
  rows: BenchmarkRow[];
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`${path} failed: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export function getCountries(): Promise<CountrySummary[]> {
  return getJson<CountrySummary[]>("/countries");
}

export function getTimeSeries(country: string, indicator: string): Promise<TimeSeriesPoint[]> {
  const params = new URLSearchParams({ country, indicator });
  return getJson<TimeSeriesPoint[]>(`/timeseries?${params.toString()}`);
}

export function getCompare(countries: string[], indicator: string): Promise<CompareRow[]> {
  const params = new URLSearchParams({ countries: countries.join(","), indicator });
  return getJson<CompareRow[]>(`/compare?${params.toString()}`);
}

export function getBenchmark(year: number): Promise<BenchmarkResponse> {
  const params = new URLSearchParams({ year: String(year) });
  return getJson<BenchmarkResponse>(`/benchmark?${params.toString()}`);
}

// --- AI Q&A (spec 004 /ask): a grounded, cited answer over the published mart ---

export interface AskCitation {
  country_code: string;
  country_name: string;
  year: number;
  indicator: string;
  value: number;
}

export interface InsightResponse {
  answer: string;
  citations: AskCitation[];
  caveats: string;
}

export function getAsk(question: string): Promise<InsightResponse> {
  const params = new URLSearchParams({ q: question });
  return getJson<InsightResponse>(`/ask?${params.toString()}`);
}

// --- Model prediction + country brief (spec 002 /predict, /brief) — the ML surfaced directly ---

export type Performance = "above_expected" | "near_expected" | "below_expected";

export interface CountryBrief {
  country_code: string;
  country_name: string;
  year: number;
  indicators: Record<string, number | null>;
  predicted_life_expectancy: number;
  actual_life_expectancy: number;
  residual: number;
  performance_vs_spend: Performance;
  summary: string;
}

export interface Prediction {
  country_code: string;
  country_name: string;
  year: number;
  indicators: Record<string, number | null>;
  predicted_life_expectancy: number;
  actual_life_expectancy: number | null;
  model: string;
}

export function getBrief(country: string, year: number): Promise<CountryBrief> {
  const params = new URLSearchParams({ country, year: String(year) });
  return getJson<CountryBrief>(`/brief?${params.toString()}`);
}

export function getPrediction(country: string, year: number): Promise<Prediction> {
  const params = new URLSearchParams({ country, year: String(year) });
  return getJson<Prediction>(`/predict?${params.toString()}`);
}

// --- Forecast (spec 010 /forecast): project the inputs forward, then predict a FUTURE year ---
// Distinct from /predict: the inputs are themselves projected, so the result is explicitly a
// forecast (`is_forecast`) carrying its projected inputs + a qualitative caveat — never a measurement.

export interface ForecastResponse {
  country_code: string;
  country_name: string;
  year: number;
  projected_indicators: Record<string, number>;
  forecast_life_expectancy: number;
  is_forecast: boolean;
  based_on_years: number[];
  caveat: string;
  model: string;
}

export function getForecast(country: string, year: number): Promise<ForecastResponse> {
  const params = new URLSearchParams({ country, year: String(year) });
  return getJson<ForecastResponse>(`/forecast?${params.toString()}`);
}
