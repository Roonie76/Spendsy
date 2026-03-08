/**
 * api.js - Centralised API client for Spendsy Frontend
 *
 * Uses credentials: "include" so HttpOnly cookies (access_token, refresh_token)
 * are sent automatically. No tokens are stored in localStorage.
 *
 * All responses are expected to be JSON with shape:
 *   { ok: boolean, data: any, message: string, error?: string }
 */

const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || "http://localhost:8080";
export const API_BASE = import.meta.env.VITE_FINANCE_URL
  ? `${import.meta.env.VITE_FINANCE_URL}`
  : `${GATEWAY_URL}/finance`;
export const AUTH_BASE = import.meta.env.VITE_AUTH_URL
  ? `${import.meta.env.VITE_AUTH_URL}`
  : `${GATEWAY_URL}/auth`;
export const AI_BASE = import.meta.env.VITE_AI_URL || `${GATEWAY_URL}/ai`;

/**
 * Core fetch wrapper — always sends cookies, always expects JSON back.
 * Throws on non-2xx so React Query / callers can handle errors uniformly.
 */
export async function apiFetch(url, options = {}) {
  const headers = {
    ...(options.body && !(options.body instanceof FormData)
      ? { "Content-Type": "application/json" }
      : {}),
    ...(options.headers || {}),
  };

  const res = await fetch(url, {
    ...options,
    headers,
    credentials: "include",   // <- HttpOnly cookie auth (replaces localStorage tokens)
  });

  if (!res.ok) {
    let errorBody = {};
    try {
      errorBody = await res.json();
    } catch (_) {}
    const message =
      errorBody.message || errorBody.detail || `Request failed (${res.status})`;
    const error = new Error(message);
    error.status = res.status;
    error.body = errorBody;
    throw error;
  }

  return res.json();
}

// ─── Auth ─────────────────────────────────────────────────────────────────

export const authApi = {
  login: (body) =>
    apiFetch(`${AUTH_BASE}/login`, { method: "POST", body: JSON.stringify(body) }),
  register: (body) =>
    apiFetch(`${AUTH_BASE}/register`, { method: "POST", body: JSON.stringify(body) }),
  logout: () =>
    apiFetch(`${AUTH_BASE}/logout`, { method: "POST" }),
  me: () =>
    apiFetch(`${AUTH_BASE}/me`),
};

// ─── Finance ──────────────────────────────────────────────────────────────

export const financeApi = {
  summary: () => apiFetch(`${API_BASE}/summary`),

  profile: (userId) => apiFetch(`${API_BASE}/profile/${userId}`),
  updateProfile: (userId, body) =>
    apiFetch(`${API_BASE}/profile/${userId}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  /**
   * Cursor-paginated transactions.
   * @param {Object} params - { limit, cursor, search }
   */
  transactions: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.limit) qs.set("limit", params.limit);
    if (params.cursor) qs.set("cursor", params.cursor);
    if (params.search) qs.set("search", params.search);
    return apiFetch(`${API_BASE}/transactions?${qs.toString()}`);
  },

  addTransaction: (body) =>
    apiFetch(`${API_BASE}/transactions`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateTransaction: (id, body) =>
    apiFetch(`${API_BASE}/transactions/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  deleteTransaction: (id) =>
    apiFetch(`${API_BASE}/transactions/${id}`, { method: "DELETE" }),

  wealth: () => apiFetch(`${API_BASE}/wealth`),
  addWealth: (body) =>
    apiFetch(`${API_BASE}/wealth`, { method: "POST", body: JSON.stringify(body) }),
  updateWealth: (id, body) =>
    apiFetch(`${API_BASE}/wealth/${id}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteWealth: (id) =>
    apiFetch(`${API_BASE}/wealth/${id}`, { method: "DELETE" }),

  taxProfile: (userId) => apiFetch(`${API_BASE}/tax-profile/${userId}`),
  updateTaxProfile: (userId, body) =>
    apiFetch(`${API_BASE}/tax-profile/${userId}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  parseStatement: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiFetch(`${API_BASE}/parse-statement`, { method: "POST", body: fd });
  },
};

// ─── AI ───────────────────────────────────────────────────────────────────

export const aiApi = {
  chat: (message) =>
    apiFetch(`${AI_BASE}/chat`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};
