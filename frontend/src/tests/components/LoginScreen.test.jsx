import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../api", () => ({
  authApi: {
    login: vi.fn(),
    register: vi.fn(),
  },
}));

vi.mock("@shared/config/constants", () => ({
  APP_VERSION: "test-version",
}));

import { authApi } from "../../api";
import LoginScreen from "../../pages/LoginScreen";


describe("LoginScreen", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows the specific signup conflict returned by the backend", async () => {
    const user = userEvent.setup();
    const onAuthSuccess = vi.fn();
    const showToast = vi.fn();
    authApi.register.mockRejectedValue({
      body: { detail: "Email already exists" },
      message: "Email already exists",
    });

    render(<LoginScreen onAuthSuccess={onAuthSuccess} showToast={showToast} />);

    await user.click(screen.getByRole("button", { name: /need an account\? create one/i }));
    await user.type(screen.getByPlaceholderText(/username/i), " Alice ");
    await user.type(screen.getByPlaceholderText(/email/i), "alice@example.com");
    await user.type(screen.getByPlaceholderText(/password/i), "Password1");
    await user.click(screen.getByRole("button", { name: /sign up/i }));

    expect(await screen.findByText("Email already exists")).toBeInTheDocument();
    expect(showToast).toHaveBeenCalledWith("Email already exists", "error");
    expect(authApi.register).toHaveBeenCalledWith({
      username: "Alice",
      email: "alice@example.com",
      password: "Password1",
    });
  });

  it("prefers the backend login message over the error code", async () => {
    const user = userEvent.setup();
    const onAuthSuccess = vi.fn();
    const showToast = vi.fn();
    authApi.login.mockRejectedValue({
      body: {
        error: "authentication_failed",
        detail: "Invalid username/email or password",
        message: "Invalid username/email or password",
      },
      message: "Invalid username/email or password",
    });

    render(<LoginScreen onAuthSuccess={onAuthSuccess} showToast={showToast} />);

    await user.type(screen.getByPlaceholderText(/username/i), "alice");
    await user.type(screen.getByPlaceholderText(/password/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("Invalid username/email or password")).toBeInTheDocument();
    expect(screen.queryByText("authentication_failed")).not.toBeInTheDocument();
    expect(showToast).toHaveBeenCalledWith("Invalid username/email or password", "error");
  });
});
