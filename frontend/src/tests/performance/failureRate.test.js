import axios from "axios";
import MockAdapter from "axios-mock-adapter";

describe("API failure rate", () => {
  let mock;

  beforeEach(() => {
    mock = new MockAdapter(axios);
  });

  afterEach(() => {
    mock.restore();
  });

  it("calculates failure rate over repeated requests", async () => {
    // Arrange
    let counter = 0;
    mock.onGet("/transactions").reply(() => {
      counter += 1;
      if (counter % 3 === 0) {
        return [500, { message: "Error" }];
      }
      return [200, { data: [] }];
    });

    // Act
    const total = 15;
    let failures = 0;
    for (let i = 0; i < total; i += 1) {
      try {
        await axios.get("/transactions");
      } catch {
        failures += 1;
      }
    }
    const failureRate = failures / total;

    // Assert
    expect(failures).toBe(5);
    expect(failureRate).toBeCloseTo(1 / 3, 3);
  });
});
