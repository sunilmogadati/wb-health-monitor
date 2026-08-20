import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { PredictionPanel } from "../PredictionPanel";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof api>();
  return { ...actual, getPrediction: vi.fn(), getBrief: vi.fn() };
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
});
