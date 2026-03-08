import React, { useState } from "react";
import { Wallet, Eye, EyeOff } from "lucide-react";
import { APP_VERSION } from "../../../../../packages/shared/config/constants";

const LoginScreen = ({ onAuthSuccess, showToast }) => {
  const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || "http://localhost:8080";
  const AUTH_BASE_URL = (import.meta.env.VITE_AUTH_URL || `${GATEWAY_URL}/auth`).replace(/\/$/, "");

  // Local state for the form
  const [isSignup, setIsSignup] = useState(false);
  const [authData, setAuthData] = useState({
    username: "",
    password: "",
    email: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const handleAuth = async (e) => {
    e.preventDefault();
    const endpoint = isSignup ? "register/" : "login/";

    try {
      setErrorMessage("");
      const response = await fetch(`${AUTH_BASE_URL}/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: authData.username,
          password: authData.password,
          email: authData.email || undefined,
        }),
      });
      const data = await response.json();

      if (response.ok) {
        // Support both microservices auth ({ user, tokens }) and Django auth ({ data: { user_id, token, ... } })
        const payload = data?.data ?? data;
        const user = payload?.user ?? payload ?? {};
        const tokens = payload?.tokens ?? {};
        const accessToken =
          tokens?.access_token ||
          payload?.token ||
          payload?.access_token ||
          "";

        if (accessToken) {
          localStorage.setItem("access_token", accessToken);
          localStorage.setItem("token", accessToken);
        }
        if (tokens?.refresh_token) {
          localStorage.setItem("refresh_token", tokens.refresh_token);
        }

        onAuthSuccess({
          id: user.id || payload.user_id,
          username: user.username || payload.username || authData.username,
          email: user.email || payload.email || authData.email,
          token: accessToken,
        });
        showToast(
          isSignup ? "Account created! You're signed in." : `Logged in as ${user.username || authData.username}`,
          "success",
        );
      } else {
        const detail = data.detail || data.error || "Incorrect username or password.";
        setErrorMessage(detail);
        showToast(detail, "error");
      }
    } catch (err) {
      setErrorMessage("Backend unreachable. Please try again.");
      showToast("Backend unreachable", "error");
    }
  };

  return (
    <div className="min-h-screen w-full bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-blue-900 via-slate-900 to-black text-white flex flex-col items-center justify-center p-6">
      <div className="z-10 w-full max-w-sm text-center">
        <div className="w-20 h-20 bg-gradient-to-tr from-blue-500 to-cyan-400 rounded-3xl mx-auto mb-6 flex items-center justify-center transform rotate-6 border border-white/10 shadow-2xl">
          <Wallet className="w-10 h-10 text-white" />
        </div>

        <h1 className="text-4xl font-black text-white mb-2">Spendsy</h1>
        <p className="text-blue-200/70 mb-8 text-sm italic">
          Financial clarity for the modern era.
        </p>

        <div className="bg-white/5 border border-white/10 p-6 rounded-[2rem] backdrop-blur-xl text-left">
          <h2 className="text-xl font-bold mb-4">
            {isSignup ? "Create Account" : "Login"}
          </h2>

          {errorMessage && (
            <div className="mb-3 rounded-xl border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-200">
              {errorMessage}
            </div>
          )}

          <form onSubmit={handleAuth} className="flex flex-col gap-3">
            <input
              placeholder="Username"
              className="bg-black/20 border border-white/10 p-3 rounded-xl focus:border-blue-500 outline-none text-sm"
              required
              onChange={(e) =>
                setAuthData({ ...authData, username: e.target.value })
              }
            />
            {isSignup && (
              <input
                placeholder="Email"
                className="bg-black/20 border border-white/10 p-3 rounded-xl focus:border-blue-500 outline-none text-sm"
                type="email"
                required
                onChange={(e) =>
                  setAuthData({ ...authData, email: e.target.value })
                }
              />
            )}
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Password"
                className="w-full bg-black/20 border border-white/10 p-3 pr-10 rounded-xl focus:border-blue-500 outline-none text-sm"
                required
                onChange={(e) =>
                  setAuthData({ ...authData, password: e.target.value })
                }
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute inset-y-0 right-2 flex items-center text-slate-400 hover:text-white"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>
            <button className="bg-blue-600 py-3 rounded-xl font-bold hover:bg-blue-700 transition-all mt-2 shadow-lg shadow-blue-900/20">
              {isSignup ? "Sign Up" : "Sign In"}
            </button>
          </form>

          <button
            onClick={() => setIsSignup(!isSignup)}
            className="mt-4 text-xs opacity-60 hover:opacity-100 transition-opacity w-full text-center"
          >
            {isSignup
              ? "Already have an account? Login"
              : "Need an account? Create one"}
          </button>
        </div>

        <div className="mt-8 text-[10px] text-slate-500 font-mono uppercase tracking-widest">
          {APP_VERSION}
        </div>
      </div>
    </div>
  );
};

export default LoginScreen;
