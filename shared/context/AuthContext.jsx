import React, { createContext, useContext, useState, useEffect } from "react";
const getGatewayUrl = () => {
  if (typeof import.meta !== "undefined" && import.meta.env) {
    return import.meta.env.VITE_GATEWAY_URL || "http://localhost:8080";
  }
  if (typeof process !== "undefined" && process.env) {
    return process.env.EXPO_PUBLIC_GATEWAY_URL || process.env.GATEWAY_URL || "http://localhost:8080";
  }
  return "http://localhost:8080";
};

const AUTH_BASE_URL = `${getGatewayUrl()}/auth`;

const AuthContext = createContext();

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // 1. Check if user is already logged in on mount
  useEffect(() => {
    const checkAuthStatus = async () => {
      const token = localStorage.getItem("access_token");
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`${AUTH_BASE_URL}/me`, {
          headers: {
            "Authorization": token.startsWith("Bearer ") ? token : `Bearer ${token}`,
          },
        });

        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
        } else {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
        }
      } catch (err) {
        console.error("Auth check failed", err);
      } finally {
        setLoading(false);
      }
    };

    checkAuthStatus();
  }, []);

  // 2. Login
  const login = async (username, password) => {
    setError("");
    try {
      const response = await fetch(`${AUTH_BASE_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (response.ok) {
        const userData = data.user || {};
        const tokens = data.tokens || {};
        if (tokens.access_token) {
          localStorage.setItem("access_token", tokens.access_token);
        }
        if (tokens.refresh_token) {
          localStorage.setItem("refresh_token", tokens.refresh_token);
        }
        setUser(userData);
        return true;
      } else {
        setError(data.detail || data.message || data.non_field_errors || "Login failed");
        return false;
      }
    } catch (err) {
      setError("Server unreachable");
      return false;
    }
  };

  // 3. Standard Django Logout
  const logout = async () => {
    const token = localStorage.getItem("access_token");
    try {
      if (token) {
        await fetch(`${AUTH_BASE_URL}/logout`, {
          method: "POST",
          headers: { "Authorization": token.startsWith("Bearer ") ? token : `Bearer ${token}` },
        });
      }
    } finally {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      setUser(null);
    }
  };

  const value = {
    user,
    loading,
    error,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
