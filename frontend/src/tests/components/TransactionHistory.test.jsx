import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import HistoryPage from "../../pages/HistoryPage";

const transactions = [
  {
    id: 1,
    title: "Coffee",
    amount: 120,
    date: "2025-01-10",
    type: "expense",
    category: "food",
  },
  {
    id: 2,
    title: "Salary",
    amount: 50000,
    date: "2025-01-05",
    type: "income",
    category: "salary",
  },
  {
    id: 3,
    title: "Taxi",
    amount: 300,
    date: "2025-01-11",
    type: "expense",
    category: "transport",
  },
];

const baseProps = {
  transactions,
  onDelete: vi.fn(),
  onBulkDelete: vi.fn(),
  setActiveTab: vi.fn(),
  onUpdate: vi.fn(),
};

describe("HistoryPage - Transaction History", () => {
  beforeEach(() => {
    vi.useRealTimers();
  });

  it("renders the history view with results", () => {
    // Arrange
    render(<HistoryPage {...baseProps} />);

    // Act
    const heading = screen.getByRole("heading", { name: /all transactions/i });

    // Assert
    expect(heading).toBeInTheDocument();
    expect(screen.getByText(/3 results/i)).toBeInTheDocument();
    expect(screen.getByText("Coffee")).toBeInTheDocument();
  });

  it("filters transactions by search term", async () => {
    // Arrange
    const user = userEvent.setup();
    render(<HistoryPage {...baseProps} />);

    // Act
    const searchInput = screen.getByPlaceholderText(/search by name or amount/i);
    await user.type(searchInput, "Coffee");

    // Assert
    expect(screen.getByText("Coffee")).toBeInTheDocument();
    expect(screen.queryByText("Taxi")).not.toBeInTheDocument();
  });

  it("applies filters using the filter modal", async () => {
    // Arrange
    const user = userEvent.setup();
    const { container } = render(<HistoryPage {...baseProps} />);
    const filterButton = Array.from(container.querySelectorAll("button")).find((btn) =>
      btn.querySelector('svg[class*="lucide-funnel"], svg[class*="lucide-sliders-horizontal"]'),
    );
    expect(filterButton).toBeTruthy();

    // Act
    await user.click(filterButton);
    const minInput = screen.getByPlaceholderText(/min/i);
    await user.type(minInput, "1000");
    await user.click(screen.getByRole("button", { name: /apply filters/i }));

    // Assert
    expect(screen.getByText(/1 results/i)).toBeInTheDocument();
    expect(screen.queryByText("Coffee")).not.toBeInTheDocument();
  });
});
