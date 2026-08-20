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
});
