import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { BenchmarkResponse } from "@/lib/api";
import { BenchmarkChart } from "../BenchmarkChart";

const BUILT: BenchmarkResponse = {
  model_built: true,
  rows: [
    {
      country_code: "KEN",
      country_name: "Kenya",
      year: 2022,
      actual: 61.4,
      predicted: 58.9,
      residual: 2.5,
      band: "above",
    },
    {
      country_code: "NGA",
      country_name: "Nigeria",
      year: 2022,
      actual: 54.5,
      predicted: 57.1,
      residual: -2.6,
      band: "below",
    },
  ],
};

describe("BenchmarkChart", () => {
  it("renders bars for the built model", () => {
    render(<BenchmarkChart data={BUILT} />);
    expect(screen.getByText(/Kenya:.*above what spending predicts/)).toBeInTheDocument();
    expect(screen.getByText(/Nigeria:.*below what spending predicts/)).toBeInTheDocument();
  });

  it("shows a graceful state when the model isn't built, not an error", () => {
    render(<BenchmarkChart data={{ model_built: false, rows: [] }} />);
    expect(screen.getByRole("status")).toHaveTextContent(/model not built yet/i);
  });

  it("shows a graceful state when there are no rows for the year", () => {
    render(<BenchmarkChart data={{ model_built: true, rows: [] }} />);
    expect(screen.getByRole("status")).toHaveTextContent(/no benchmark rows/i);
  });

  it("never uses causal or blame language (Principle V, FR-003)", () => {
    render(<BenchmarkChart data={BUILT} />);
    const text = document.body.textContent?.toLowerCase() ?? "";
    for (const banned of ["best", "worst", "failing", "fails", "causes", "blame"]) {
      expect(text).not.toContain(banned);
    }
    expect(text).toContain("what spending predicts");
  });
});
