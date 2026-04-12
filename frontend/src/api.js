/**
 * api.js - Centralised API client for Spendsy Frontend
 *
 * Authentication is resilient in local development:
 * - cookies are sent for the FastAPI cookie flow
 * - a stored bearer token is attached as a fallback
 * - one refresh attempt is made on 401 before surfacing the error
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
const ACCESS_TOKEN_KEYS = ["access_token", "auth_token", "token"];
const REFRESH_TOKEN_KEY = "refresh_token";

let refreshPromise = null;
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function storage() {
  return typeof window === "undefined" ? null : window.localStorage;
}

export function getStoredAccessToken() {
  const localStore = storage();
  if (!localStore) return "";

  return ACCESS_TOKEN_KEYS
    .map((key) => localStore.getItem(key))
    .find(Boolean) || "";
}

function getStoredRefreshToken() {
  const localStore = storage();
  return localStore?.getItem(REFRESH_TOKEN_KEY) || "";
}

function storeToken(key, value) {
  const localStore = storage();
  if (!localStore) return;

  if (value) {
    localStore.setItem(key, value);
    return;
  }

  localStore.removeItem(key);
}

function persistTokens(payload = {}) {
  const tokenPayload = payload?.tokens ?? payload;
  const accessToken = tokenPayload?.access_token || payload?.access_token || "";
  const refreshToken = tokenPayload?.refresh_token || payload?.refresh_token || "";

  if (accessToken) {
    storeToken("access_token", accessToken);
    storeToken("token", accessToken);
  }

  if (refreshToken) {
    storeToken(REFRESH_TOKEN_KEY, refreshToken);
  }
}

async function persistAuthResponse(requestPromise) {
  const data = await requestPromise;
  persistTokens(data?.data || data);
  return data;
}

export function clearStoredAuth() {
  const localStore = storage();
  if (!localStore) return;

  [...ACCESS_TOKEN_KEYS, REFRESH_TOKEN_KEY].forEach((key) => {
    localStore.removeItem(key);
  });
}

function buildHeaders(options = {}) {
  const headers = new Headers(options.headers || {});

  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const accessToken = getStoredAccessToken();
  if (accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  return headers;
}

async function readJsonBody(response) {
  try {
    return await response.json();
  } catch (_) {
    return {};
  }
}

function buildRequestError(response, errorBody = {}) {
  const message =
    errorBody.message || errorBody.detail || `Request failed (${response.status})`;
  const error = new Error(message);
  error.status = response.status;
  error.body = errorBody;
  return error;
}

function isRefreshExcluded(url = "") {
  return /\/auth\/(login|register|refresh)(\/)?$/.test(url);
}

async function refreshAccessToken() {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    const refreshToken = getStoredRefreshToken();
    const headers = new Headers();
    const requestOptions = {
      method: "POST",
      headers,
      credentials: "include",
    };

    // Support both the HttpOnly-cookie path and the local-storage fallback path.
    if (refreshToken) {
      headers.set("Content-Type", "application/json");
      requestOptions.body = JSON.stringify({ refresh_token: refreshToken });
    }

    const response = await fetch(`${AUTH_BASE}/refresh`, requestOptions);
    if (!response.ok) {
      clearStoredAuth();
      throw buildRequestError(response, await readJsonBody(response));
    }

    const data = await readJsonBody(response);
    persistTokens(data?.data || data);
    return data;
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

/**
 * Core fetch wrapper with exponential backoff for network failures and 5xx errors.
 * Also handles 401 refresh logic.
 */
export async function apiFetch(url, options = {}, retries = 3, backoff = 1000) {
  const headers = buildHeaders(options);

  try {
    const res = await fetch(url, {
      ...options,
      headers,
      credentials: "include",
    });

    // 1. Handle 401 Unauthorized (Token Refresh)
    if (res.status === 401 && !options._retry && !isRefreshExcluded(url)) {
      try {
        await refreshAccessToken();
        return apiFetch(url, { ...options, _retry: true });
      } catch (_) {
        clearStoredAuth();
      }
    }

    // 2. Handle 5xx / 429 / Network failures with retry
    if ((res.status >= 500 || res.status === 429) && retries > 0) {
      console.warn(`Retrying ${url} due to status ${res.status}. ${retries} attempts left.`);
      await wait(backoff);
      return apiFetch(url, options, retries - 1, backoff * 2);
    }

    if (!res.ok) {
      throw buildRequestError(res, await readJsonBody(res));
    }

    return res.json();
  } catch (err) {
    // TypeError: Failed to fetch (Network Error)
    if (retries > 0) {
      console.warn(`Retrying ${url} due to network error: ${err.message}. ${retries} attempts left.`);
      await wait(backoff);
      return apiFetch(url, options, retries - 1, backoff * 2);
    }
    throw err;
  }
}

// ─── Auth ─────────────────────────────────────────────────────────────────

export const authApi = {
  login: (body) =>
    persistAuthResponse(
      apiFetch(`${AUTH_BASE}/login`, { method: "POST", body: JSON.stringify(body) }),
    ),
  register: (body) =>
    persistAuthResponse(
      apiFetch(`${AUTH_BASE}/register`, { method: "POST", body: JSON.stringify(body) }),
    ),
  refresh: () =>
    persistAuthResponse(
      apiFetch(`${AUTH_BASE}/refresh`, { method: "POST" }),
    ),
  logout: () =>
    apiFetch(`${AUTH_BASE}/logout`, { method: "POST" }).finally(() => {
      clearStoredAuth();
    }),
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

  loans: () => apiFetch(`${API_BASE}/loans`),

  taxProfile: (userId) => apiFetch(`${API_BASE}/tax-profile/${userId}`),

  updateTaxProfile: (userId, body) =>
    apiFetch(`${API_BASE}/tax-profile/${userId}`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  parseDigitalPdf: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiFetch(`${API_BASE}/parse-digital-pdf`, { method: "POST", body: fd });
  },
  
  // Plans (Planner System)
  plans: () => apiFetch(`${API_BASE}/plans`),
  addPlan: (body) => apiFetch(`${API_BASE}/plans`, { method: "POST", body: JSON.stringify(body) }),
  updatePlan: (uid, body) => apiFetch(`${API_BASE}/plans/${uid}`, { method: "PATCH", body: JSON.stringify(body) }),
  deletePlan: (uid) => apiFetch(`${API_BASE}/plans/${uid}`, { method: "DELETE" }),
};

// ─── AI ───────────────────────────────────────────────────────────────────

export const aiApi = {
  chat: (message) =>
    apiFetch(`${AI_BASE}/chat`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};
