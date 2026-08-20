import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CompareRow } from "@/lib/api";
import { CompareChart, pivotCompareRows } from "../CompareChart";

const ROWS: CompareRow[] = [
  { country_code: "KEN", country_name: "Kenya", year: 2015, indicator: "life_expectancy", value: 58.1 },
  { country_code: "KEN", country_name: "Kenya", year: 2016, indicator: "life_expectancy", value: 58.9 },
  { country_code: "NGA", country_name: "Nigeria", year: 2015, indicator: "life_expectancy", value: 52.3 },
];

describe("pivotCompareRows", () => {
  it("groups flat rows into one row per year with one column per country", () => {
    const { data, countries } = pivotCompareRows(ROWS);
    expect(countries.map((c) => c.code).sort()).toEqual(["KEN", "NGA"]);
    const year2015 = data.find((d) => d.year === 2015);
    expect(year2015).toMatchObject({ KEN: 58.1, NGA: 52.3 });
    const year2016 = data.find((d) => d.year === 2016);
    // Nigeria has no 2016 row — that must be a gap (null), not a fabricated 0.
    expect(year2016?.NGA).toBeNull();
  });
});

describe("CompareChart", () => {
  it("renders a line and legend entry for each selected country", () => {
    render(<CompareChart indicatorLabel="Life expectancy" rows={ROWS} />);
    expect(screen.getByText("Kenya")).toBeInTheDocument();
    expect(screen.getByText("Nigeria")).toBeInTheDocument();
  });

  it("shows an empty state when no rows are returned", () => {
    render(<CompareChart indicatorLabel="Life expectancy" rows={[]} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
