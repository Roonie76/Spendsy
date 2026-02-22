import React, { useState } from "react";
import { Wallet } from "lucide-react";
import { APP_VERSION } from "../../../../../packages/shared/config/constants";

const LoginScreen = ({ onAuthSuccess, showToast }) => {
  const API_BASE_URL =`${import.meta.env.VITE_API_URL}/api/finance` || "http://127.0.0.1:8000/api/finance";

  // Local state for the form
  const [isSignup, setIsSignup] = useState(false);
  const [authData, setAuthData] = useState({
    username: "",
    password: "",
    email: "",
  });

  const handleAuth = async (e) => {
    e.preventDefault();
    const endpoint = isSignup ? "/register/" : "/login/";

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(authData),
      });
      const data = await response.json();

      if (response.ok) {
        if (isSignup) {
          showToast("Account created! Please login.", "success");
          setIsSignup(false);
        } else {
          // Pass the user data back up to App.jsx
          onAuthSuccess({
            id: data.user_id,
            username: data.username,
            email: data.email, // This allows App.jsx and ProfilePage to see it
          });
          showToast(`Logged in as ${data.username}`, "success");
        }
      } else {
        showToast(data.error || "Auth failed", "error");
      }
    } catch (err) {
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

          <form onSubmit={handleAuth} className="flex flex-col gap-3">
            <input
              placeholder="Username"
              className="bg-black/20 border border-white/10 p-3 rounded-xl focus:border-blue-500 outline-none text-sm"
              onChange={(e) =>
                setAuthData({ ...authData, username: e.target.value })
              }
            />
            {isSignup && (
              <input
                placeholder="Email"
                className="bg-black/20 border border-white/10 p-3 rounded-xl focus:border-blue-500 outline-none text-sm"
                onChange={(e) =>
                  setAuthData({ ...authData, email: e.target.value })
                }
              />
            )}
            <input
              type="password"
              placeholder="Password"
              className="bg-black/20 border border-white/10 p-3 rounded-xl focus:border-blue-500 outline-none text-sm"
              onChange={(e) =>
                setAuthData({ ...authData, password: e.target.value })
              }
            />
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
