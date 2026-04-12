import React from "react";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { vi } from "vitest";
import { detectPdfType } from "../../utils/pdf/detectPdfType";
import AddPage from "../../pages/AddPage";
import StatementHub from "../../components/ui/StatementHub";
import { OCR_CONVERTER_URL } from "../../components/upload/OcrUnsupportedModal";

vi.mock("../../utils/pdf/detectPdfType", () => ({
  detectPdfType: vi.fn(),
}));

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
  const amountInput = screen.getByPlaceholderText("0");
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
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true, data: [] }),
    });
    detectPdfType.mockReset();
    detectPdfType.mockResolvedValue("digital");
    baseProps.showToast.mockClear();
    baseProps.refreshData.mockClear();
    vi.spyOn(window, "open").mockImplementation(() => null);
  });

  afterEach(() => {
    window.open.mockRestore();
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
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /save transaction/i }));
      await Promise.resolve();
    });

    // Assert
    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/finance/transactions",
      expect.objectContaining({ method: "POST" }),
    );
    expect(baseProps.showToast).toHaveBeenCalledWith("Added!", "success");
    expect(baseProps.refreshData).toHaveBeenCalled();
    expect(amountInput).toHaveValue("");
    expect(descInput).toHaveValue("");
  });

  it("shows a loading state during API calls", async () => {
    // Arrange
    let resolveFetch;
    global.fetch.mockImplementation(
      (url) => {
        if (String(url).includes("/transactions")) {
          return new Promise((resolve) => {
            resolveFetch = resolve;
          });
        }

        return Promise.resolve({
          ok: true,
          json: async () => ({ ok: true, data: [] }),
        });
      },
    );

    render(<AddPage {...baseProps} />);
    fillTransactionForm();

    // Act
    fireEvent.click(screen.getByRole("button", { name: /save transaction/i }));

    // Assert
    expect(screen.getByText(/processing/i)).toBeInTheDocument();

    // Cleanup
    await act(async () => {
      resolveFetch({ ok: true, json: async () => ({ ok: true }) });
      await Promise.resolve();
    });

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/finance/transactions",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows an error state when the API fails", async () => {
    vi.useFakeTimers();

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
    await act(async () => {
      await vi.advanceTimersByTimeAsync(8000);
    });

    expect(baseProps.showToast).toHaveBeenCalled();
    expect(baseProps.showToast).toHaveBeenCalledWith(
      expect.stringContaining("Server Error"),
      "error",
    );

    vi.useRealTimers();
  });

  it("refreshes shared data after a successful statement upload", async () => {
    global.fetch.mockImplementation((url) => {
      if (String(url).includes("/statements/history")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ ok: true, data: [] }),
        });
      }

      if (String(url).includes("/parse-digital-pdf")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            ok: true,
            data: {
              transactions: [
                {
                  id: 999,
                  amount: "430.00",
                  type: "expense",
                  description: "Parsed digital PDF transaction",
                  date: "2023-07-19",
                },
              ],
              saved_count: 1,
            },
          }),
        });
      }

      return Promise.resolve({
        ok: true,
        json: async () => ({ ok: true, data: [] }),
      });
    });

    const { container } = render(
      <StatementHub
        user={baseProps.user}
        apiBaseUrl={baseProps.apiBaseUrl}
        showToast={baseProps.showToast}
        refreshData={baseProps.refreshData}
      />,
    );

    const fileInput = container.querySelector('input[type="file"]');
    const file = new File(["dummy pdf"], "statement.pdf", { type: "application/pdf" });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [file] } });
    });

    await waitFor(() => expect(baseProps.refreshData).toHaveBeenCalled());
    expect(baseProps.showToast).toHaveBeenCalledWith(
      "Digital PDF processed! Synced 1 transactions.",
      "success",
    );
  }, 10000);

  it("blocks OCR PDFs and shows the unsupported-format modal", async () => {
    detectPdfType.mockResolvedValue("ocr");

    const { container } = render(
      <StatementHub
        user={baseProps.user}
        apiBaseUrl={baseProps.apiBaseUrl}
        showToast={baseProps.showToast}
        refreshData={baseProps.refreshData}
      />,
    );

    const fileInput = container.querySelector('input[type="file"]');
    const file = new File(["scanned pdf"], "scan.pdf", { type: "application/pdf" });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [file] } });
    });

    expect(await screen.findByText(/OCR format not supported/i)).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalledWith(
      expect.stringContaining("/parse-digital-pdf"),
      expect.anything(),
    );
    expect(baseProps.refreshData).not.toHaveBeenCalled();
  });

  it("opens the converter from the OCR modal", async () => {
    detectPdfType.mockResolvedValue("ocr");

    const { container } = render(
      <StatementHub
        user={baseProps.user}
        apiBaseUrl={baseProps.apiBaseUrl}
        showToast={baseProps.showToast}
        refreshData={baseProps.refreshData}
      />,
    );

    const fileInput = container.querySelector('input[type="file"]');
    const file = new File(["scanned pdf"], "scan.pdf", { type: "application/pdf" });

    await act(async () => {
      fireEvent.change(fileInput, { target: { files: [file] } });
    });

    fireEvent.click(await screen.findByRole("button", { name: /open converter/i }));
    expect(window.open).toHaveBeenCalledWith(
      OCR_CONVERTER_URL,
      "_blank",
      "noopener,noreferrer",
    );
  });
});
