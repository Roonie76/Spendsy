import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import StatsPage from "../../pages/StatsPage";
import { AIService } from "../../../../../../packages/shared/services/aiService";

const transactions = [
  {
    id: 1,
    title: "Salary",
    amount: 80000,
    date: "2025-01-01",
    type: "income",
    category: "salary",
  },
  {
    id: 2,
    title: "Groceries",
    amount: 2500,
    date: "2025-01-02",
    type: "expense",
    category: "food",
  },
  {
    id: 3,
    title: "Fuel",
    amount: 1500,
    date: "2025-01-03",
    type: "expense",
    category: "transport",
  },
];

describe("StatsPage - Dashboard charts", () => {
  beforeEach(() => {
    vi.useRealTimers();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("renders charts and category breakdown", () => {
    // Arrange
    render(<StatsPage transactions={transactions} />);

    // Act
    const breakdown = screen.getByText(/category breakdown/i);

    // Assert
    expect(screen.getByRole("heading", { name: /analytics/i })).toBeInTheDocument();
    expect(breakdown).toBeInTheDocument();
    expect(screen.getByText(/trend analysis/i)).toBeInTheDocument();
    expect(screen.getByText(/food/i)).toBeInTheDocument();
  });

  it("shows loading state while fetching AI insights", async () => {
    // Arrange
    const user = userEvent.setup();
    let resolveInsights;
    vi.spyOn(AIService, "askForJSON").mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveInsights = resolve;
        }),
    );
    render(<StatsPage transactions={transactions} />);

    // Act
    await user.click(screen.getByRole("button", { name: /run scan/i }));

    // Assert
    expect(screen.getByText(/analyzing/i)).toBeInTheDocument();

    resolveInsights([
      {
        type: "tip",
        title: "Keep it up",
        message: "Nice balance",
        impact: "normal",
      },
    ]);

    await waitFor(() => expect(AIService.askForJSON).toHaveBeenCalled());
  });

  it("updates UI on AI success", async () => {
    // Arrange
    const user = userEvent.setup();
    vi.spyOn(AIService, "askForJSON").mockResolvedValue([
      { type: "tip", title: "Smart Spend", message: "Good job", impact: "normal" },
    ]);
    render(<StatsPage transactions={transactions} />);

    // Act
    await user.click(screen.getByRole("button", { name: /run scan/i }));

    // Assert
    expect(await screen.findByText(/smart spend/i)).toBeInTheDocument();
  });

  it("shows an error state on AI failure", async () => {
    // Arrange
    const user = userEvent.setup();
    vi.spyOn(AIService, "askForJSON").mockRejectedValue(new Error("500"));
    render(<StatsPage transactions={transactions} />);

    // Act
    await user.click(screen.getByRole("button", { name: /run scan/i }));

    // Assert
    expect(
      await screen.findByText(/failed to wake up the watchdog/i),
    ).toBeInTheDocument();
  });
});
