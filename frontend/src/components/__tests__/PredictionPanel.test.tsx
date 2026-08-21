import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { PredictionPanel } from "../PredictionPanel";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof api>();
  return { ...actual, getPrediction: vi.fn(), getBrief: vi.fn(), getForecast: vi.fn() };
});

const COUNTRIES = [{ country_code: "KEN", country_name: "Kenya" }];

describe("PredictionPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows the model's prediction and the brief after running", async () => {
    vi.mocked(api.getPrediction).mockResolvedValue({
      country_code: "KEN",
      country_name: "Kenya",
      year: 2020,
      indicators: { health_spend_pct_gdp: 4.5 },
      predicted_life_expectancy: 62.1,
      actual_life_expectancy: 61.6,
      model: "random_forest",
    });
    vi.mocked(api.getBrief).mockResolvedValue({
      country_code: "KEN",
      country_name: "Kenya",
      year: 2020,
      indicators: { health_spend_pct_gdp: 4.5 },
      predicted_life_expectancy: 62.1,
      actual_life_expectancy: 61.6,
      residual: -0.5,
      performance_vs_spend: "near_expected",
      summary: "Kenya is near what its spending predicts.",
    });

    const user = userEvent.setup();
    render(<PredictionPanel countries={COUNTRIES} />);
    const [countrySelect] = screen.getAllByRole("combobox");
    await user.selectOptions(countrySelect, "KEN");
    await user.click(screen.getByRole("button", { name: /predict & explain/i }));

    expect(await screen.findByText(/62\.1 yrs/)).toBeInTheDocument();
    expect(screen.getByText(/near what spending predicts/)).toBeInTheDocument();
    expect(screen.getByText(/Kenya is near what its spending predicts/)).toBeInTheDocument();
    expect(screen.getByText(/random_forest/)).toBeInTheDocument();
  });

  it("shows a labelled forecast with projected inputs for a future year", async () => {
    vi.mocked(api.getForecast).mockResolvedValue({
      country_code: "KEN",
      country_name: "Kenya",
      year: 2028,
      projected_indicators: { health_spend_pct_gdp: 5.1, internet_pct: 100.0 },
      forecast_life_expectancy: 64.7,
      forecast_low: 58.1,
      forecast_high: 71.3,
      interval_method: "indicative ± model error (cv_rmse), widened with the forecast horizon",
      is_forecast: true,
      based_on_years: [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022],
      caveat: "Forecast, not an observation. Read as a scenario — 'if current trends hold'.",
      model: "random_forest",
    });

    const user = userEvent.setup();
    render(<PredictionPanel countries={COUNTRIES} />);
    const [countrySelect, yearSelect] = screen.getAllByRole("combobox");
    await user.selectOptions(countrySelect, "KEN");
    await user.selectOptions(yearSelect, "2028");
    await user.click(screen.getByRole("button", { name: /forecast & explain/i }));

    expect(await screen.findByText(/64\.7 yrs/)).toBeInTheDocument();
    expect(screen.getByText(/Forecast · 2028/)).toBeInTheDocument();
    expect(screen.getByText(/indicative 58\.1–71\.3/)).toBeInTheDocument();
    expect(screen.getByText(/if current trends hold/)).toBeInTheDocument();
    expect(screen.getByText(/health_spend_pct_gdp:/)).toBeInTheDocument();
    // The forecast path must NOT hit the observed-year endpoints.
    expect(api.getPrediction).not.toHaveBeenCalled();
  });
});
