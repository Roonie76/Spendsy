import axios from "axios";
import MockAdapter from "axios-mock-adapter";

const fetchTransactions = async () => {
  const response = await axios.get("/transactions");
  return response.data;
};

const createTransaction = async (payload) => {
  const response = await axios.post("/transactions", payload);
  return response.data;
};

describe("Transactions API", () => {
  let mock;

  beforeEach(() => {
    mock = new MockAdapter(axios);
  });

  afterEach(() => {
    mock.restore();
  });

  it("returns transactions on success", async () => {
    // Arrange
    const data = [{ id: 1, title: "Coffee" }];
    mock.onGet("/transactions").reply(200, data);

    // Act
    const result = await fetchTransactions();

    // Assert
    expect(result).toEqual(data);
  });

  it("creates a transaction successfully", async () => {
    // Arrange
    const payload = { title: "Groceries", amount: 120 };
    mock.onPost("/transactions", payload).reply(201, { id: 2, ...payload });

    // Act
    const result = await createTransaction(payload);

    // Assert
    expect(result).toEqual({ id: 2, ...payload });
  });

  it("throws when the API returns an error", async () => {
    // Arrange
    mock.onGet("/transactions").reply(500, { message: "Server error" });

    // Act
    let error;
    try {
      await fetchTransactions();
    } catch (err) {
      error = err;
    }

    // Assert
    expect(error).toBeDefined();
  });
});
