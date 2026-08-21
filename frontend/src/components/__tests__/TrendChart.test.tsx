import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { TimeSeriesPoint } from "@/lib/api";
import { TrendChart } from "../TrendChart";

const POINTS: TimeSeriesPoint[] = [
  { year: 2015, indicator: "life_expectancy", value: 58.1 },
  { year: 2016, indicator: "life_expectancy", value: null },
  { year: 2017, indicator: "life_expectancy", value: 59.4 },
];

describe("TrendChart", () => {
  it("renders a trend summary naming the country and indicator", () => {
    render(<TrendChart countryName="Kenya" indicatorLabel="Life expectancy" points={POINTS} />);
    expect(screen.getByText(/Kenya — Life expectancy, 2015–2017/)).toBeInTheDocument();
  });

  it("skips the missing value rather than fabricating zero", () => {
    render(<TrendChart countryName="Kenya" indicatorLabel="Life expectancy" points={POINTS} />);
    const summary = screen.getByText(/Kenya — Life expectancy/);
    expect(summary.textContent).toContain("2015: 58.1");
    expect(summary.textContent).toContain("2017: 59.4");
    expect(summary.textContent).not.toContain("2016:");
  });

  it("shows an empty state instead of an empty chart when there is no data", () => {
    render(<TrendChart countryName="Kenya" indicatorLabel="Life expectancy" points={[]} />);
    expect(screen.getByRole("status")).toHaveTextContent(/no life expectancy data for kenya/i);
  });

  it("appends the forecast continuation to the accessible summary when projected points are given", () => {
    render(
      <TrendChart
        countryName="Kenya"
        indicatorLabel="Life expectancy"
        points={POINTS}
        projected={[
          { year: 2023, value: 60.5 },
          { year: 2024, value: 60.9 },
        ]}
        projectionBasis="model"
      />,
    );
    const summary = screen.getByText(/Kenya — Life expectancy/);
    expect(summary.textContent).toContain("Forecast (model)");
    expect(summary.textContent).toContain("2023: 60.5");
  });

  it("omits the forecast when the basis is none", () => {
    render(
      <TrendChart
        countryName="Kenya"
        indicatorLabel="Under-5 mortality"
        points={POINTS}
        projected={[]}
        projectionBasis="none"
      />,
    );
    const summary = screen.getByText(/Kenya — Under-5 mortality/);
    expect(summary.textContent).not.toContain("Forecast");
  });
});
