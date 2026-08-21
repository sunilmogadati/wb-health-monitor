import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { AgentPanel } from "../AgentPanel";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof api>();
  return { ...actual, getAgentAnalyze: vi.fn() };
});

describe("AgentPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows the answer and the steps the agent took", async () => {
    vi.mocked(api.getAgentAnalyze).mockResolvedValue({
      mode: "analyze",
      answer: "Kenya's life expectancy is rising and sits above what its spending predicts.",
      steps: [
        { tool: "country_indicators", summary: "{'country_code': 'KEN', 'year': 2022}" },
        { tool: "value_for_money", summary: "{'indicator': 'life_expectancy', 'year': 2022}" },
      ],
      citations: [
        { country_code: "KEN", country_name: "Kenya", year: 2022, indicator: "life_expectancy", value: 63.5 },
      ],
      grounded: true,
      caveat: "value-for-money framing",
    });

    const user = userEvent.setup();
    render(<AgentPanel />);
    await user.type(screen.getByRole("textbox"), "is kenya improving?");
    await user.click(screen.getByRole("button", { name: /run agent/i }));

    expect(await screen.findByText(/rising and sits above/)).toBeInTheDocument();
    expect(screen.getByText(/Steps the agent took \(2\)/)).toBeInTheDocument();
    expect(screen.getByText(/value_for_money/)).toBeInTheDocument();
  });
});
