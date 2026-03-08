import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { vi } from "vitest";

describe("API latency performance", () => {
  let mock;

  beforeEach(() => {
    vi.useFakeTimers();
    mock = new MockAdapter(axios, { delayResponse: 120 });
  });

  afterEach(() => {
    mock.restore();
    vi.useRealTimers();
  });

  it("measures response time for a mocked API call", async () => {
    // Arrange
    mock.onGet("/latency").reply(200, { ok: true });
    const start = Date.now();

    // Act
    const request = axios.get("/latency");
    vi.advanceTimersByTime(120);
    await request;
    const duration = Date.now() - start;

    // Assert
    expect(duration).toBeGreaterThanOrEqual(120);
  });
});
