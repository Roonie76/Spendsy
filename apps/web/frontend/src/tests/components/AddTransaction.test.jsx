import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { vi } from "vitest";
import AddPage from "../../pages/AddPage";

const baseProps = {
  user: { id: 1, username: "demo" },
  authToken: "test-token",
  apiBaseUrl: "http://localhost:8000/api/finance",
  appId: "test",
  setActiveTab: vi.fn(),
  showToast: vi.fn(),
  triggerConfirm: (message, onConfirm) => onConfirm(),
  refreshData: vi.fn(),
};

const fillTransactionForm = () => {
  const amountInput = screen.getByRole("spinbutton");
  const descInput = screen.getByPlaceholderText(/what was this for\?/i);

  fireEvent.click(screen.getByRole("button", { name: /expense/i }));
  fireEvent.change(amountInput, { target: { value: "1200" } });
  fireEvent.change(descInput, { target: { value: "Coffee supplies" } });

  return { amountInput, descInput };
};

describe("AddPage - Add Transaction", () => {
  beforeEach(() => {
    vi.useRealTimers();
    vi.stubGlobal("fetch", vi.fn());
    baseProps.showToast.mockClear();
    baseProps.refreshData.mockClear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the add transaction form", () => {
    // Arrange
    render(<AddPage {...baseProps} />);

    // Act
    const saveButton = screen.getByRole("button", { name: /save transaction/i });

    // Assert
    expect(screen.getByRole("button", { name: /manual/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /upload/i })).toBeInTheDocument();
    expect(saveButton).toBeInTheDocument();
  });

  it("submits the transaction form and clears inputs on success", async () => {
    // Arrange
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    });
    render(<AddPage {...baseProps} />);

    const { amountInput, descInput } = fillTransactionForm();

    // Act
    fireEvent.click(screen.getByRole("button", { name: /save transaction/i }));

    // Assert
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/finance/transactions",
      expect.objectContaining({ method: "POST" }),
    );
    expect(baseProps.showToast).toHaveBeenCalledWith("Added!", "success");
    expect(baseProps.refreshData).toHaveBeenCalled();
    expect(amountInput).toHaveValue(null);
    expect(descInput).toHaveValue("");
  });

  it("shows a loading state during API calls", async () => {
    // Arrange
    let resolveFetch;
    global.fetch.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveFetch = resolve;
        }),
    );

    render(<AddPage {...baseProps} />);
    fillTransactionForm();

    // Act
    fireEvent.click(screen.getByRole("button", { name: /save transaction/i }));

    // Assert
    expect(screen.getByText(/processing/i)).toBeInTheDocument();

    // Cleanup
    resolveFetch({ ok: true, json: async () => ({ ok: true }) });
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  });

  it("shows an error state when the API fails", async () => {
    // Arrange
    global.fetch.mockResolvedValue({
      ok: false,
      json: async () => ({ message: "Failed to save" }),
    });
    render(<AddPage {...baseProps} />);
    fillTransactionForm();

    // Act
    fireEvent.click(screen.getByRole("button", { name: /save transaction/i }));

    // Assert
    await waitFor(() => expect(baseProps.showToast).toHaveBeenCalled());
    expect(baseProps.showToast).toHaveBeenCalledWith(
      expect.stringContaining("Server Error"),
      "error",
    );
  });
});
