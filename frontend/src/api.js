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

function ensureProtocol(url) {
  if (!url) return url;
  if (!/^https?:\/\//i.test(url)) {
    return url.includes("localhost") || url.startsWith("127.0.0.1") ? `http://${url}` : `https://${url}`;
  }
  return url;
}

const GATEWAY_URL = ensureProtocol(import.meta.env.VITE_GATEWAY_URL) || "http://localhost:8080";
export const API_BASE = import.meta.env.VITE_FINANCE_URL
  ? `${ensureProtocol(import.meta.env.VITE_FINANCE_URL)}`
  : `${GATEWAY_URL}/finance`;
export const AUTH_BASE = import.meta.env.VITE_AUTH_URL
  ? `${ensureProtocol(import.meta.env.VITE_AUTH_URL)}`
  : `${GATEWAY_URL}/auth`;
export const AI_BASE =
  ensureProtocol(import.meta.env.VITE_TORA_URL) ||
  ensureProtocol(import.meta.env.VITE_AI_URL) ||
  `${GATEWAY_URL}/tora`;
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
      const errorBody = await readJsonBody(res);
      const error = buildRequestError(res, errorBody);
      
      // 3. Do NOT retry on 4xx client errors (except 429)
      // These are permanent failures or security lockouts that retries will only worsen.
      if (res.status >= 400 && res.status < 500 && res.status !== 429) {
        throw error;
      }
      
      throw error;
    }

    return res.json();
  } catch (err) {
    // Only retry on:
    // 1. Network errors (TypeError: Failed to fetch)
    // 2. Specific status codes that were thrown (5xx, 429) - though those are handled above
    
    const isNetworkError = err instanceof TypeError;
    const isRetryableStatus = err.status >= 500 || err.status === 429;

    if ((isNetworkError || isRetryableStatus) && retries > 0) {
      const reason = isNetworkError ? "network error" : `status ${err.status}`;
      console.warn(`Retrying ${url} due to ${reason}: ${err.message}. ${retries} attempts left.`);
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
  updateProfile: (body) =>
    apiFetch(`${AUTH_BASE}/me`, { method: "PUT", body: JSON.stringify(body) }),
  changePassword: (body) =>
    apiFetch(`${AUTH_BASE}/change-password`, { method: "POST", body: JSON.stringify(body) }),
  sessions: () =>
    apiFetch(`${AUTH_BASE}/sessions`),
  revokeSession: (id) =>
    apiFetch(`${AUTH_BASE}/sessions/${id}`, { method: "DELETE" }),
};

// ─── Finance ──────────────────────────────────────────────────────────────

export const financeApi = {
  summary: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.period) qs.set("period", params.period);
    if (params.today) qs.set("today", params.today);
    return apiFetch(`${API_BASE}/summary?${qs.toString()}`);
  },

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

// ─── Alerts (proactive insights) ─────────────────────────────────────────────

const PRODUCT_BASE = `${API_BASE}/product`;

export const alertsApi = {
  /** Fetch recent alerts. Pass { unreadOnly: false } to include read alerts. */
  list: ({ unreadOnly = true } = {}) =>
    apiFetch(`${PRODUCT_BASE}/alerts?unread_only=${unreadOnly}`),
  /** Mark a single alert as read. */
  markRead: (alertId) =>
    apiFetch(`${PRODUCT_BASE}/alerts/${alertId}/read`, { method: "POST" }),
};

// ─── AI ───────────────────────────────────────────────────────────────────

export const aiApi = {
  chat: (message) =>
    apiFetch(`${AI_BASE}/chat`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
  /** Submit thumbs up/down feedback on a TORA response. */
  sendFeedback: (body) =>
    apiFetch(`${AI_BASE}/feedback`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

// ─── Tax / ITR ────────────────────────────────────────────────────────────────

export const taxApi = {
  /** Compute both regimes from raw data (no persistence). */
  compute: (body) =>
    apiFetch(`${API_BASE}/tax/compute`, { method: "POST", body: JSON.stringify(body) }),

  /** Run pre-filing audit checks. */
  audit: (body) =>
    apiFetch(`${API_BASE}/tax/audit`, { method: "POST", body: JSON.stringify(body) }),


};

// ─── Tax Constants (FY 2025-26 / AY 2026-27) ─────────────────────────────────

export const TAX_CONSTANTS = {
  CURRENT_AY: "2025-26",
  CURRENT_FY: "FY 2025-26",
  FILING_DEADLINE: "2025-07-31",

  NEW_REGIME_SLABS: [
    { upto: 400000, rate: 0 },
    { upto: 800000, rate: 0.05 },
    { upto: 1200000, rate: 0.10 },
    { upto: 1600000, rate: 0.15 },
    { upto: 2000000, rate: 0.20 },
    { upto: 2400000, rate: 0.25 },
    { upto: Infinity, rate: 0.30 },
  ],
  NEW_REGIME_REBATE_LIMIT: 1200000,   // 87A rebate — zero tax up to ₹12L
  NEW_REGIME_STANDARD_DEDUCTION: 75000,

  OLD_REGIME_SLABS: [
    { upto: 250000, rate: 0 },
    { upto: 500000, rate: 0.05 },
    { upto: 1000000, rate: 0.20 },
    { upto: Infinity, rate: 0.30 },
  ],
  OLD_REGIME_REBATE_LIMIT: 500000,    // 87A rebate for old regime
  OLD_REGIME_STANDARD_DEDUCTION: 50000,

  SURCHARGE_SLABS: [
    { above: 5000000, rate: 0.10 },
    { above: 10000000, rate: 0.15 },
    { above: 20000000, rate: 0.25 },
    { above: 50000000, rate: 0.37 },
  ],
  HEALTH_EDUCATION_CESS: 0.04,

  DEDUCTION_LIMITS: {
    section_80c: 150000,
    nps_80ccd_1b: 50000,
    section_80d_self: 25000,
    section_80d_self_senior: 50000,
    section_80d_parents: 25000,
    section_80d_parents_senior: 50000,
    section_80d_preventive: 5000,
    section_80dd: 75000,
    section_80dd_severe: 125000,
    section_80ddb: 40000,
    section_80ddb_senior: 100000,
    section_80e: Infinity,        // actual interest paid
    section_80eea: 150000,
    section_80gg_annual: 60000,   // min(5k/mo, 25% GTI, actual-10% GTI)
    section_80gga: null,
    section_80tta: 10000,
    section_80ttb: 50000,         // seniors
    section_80g: Infinity,        // varies by fund
    hra_max_metro_pct: 0.50,
    hra_max_non_metro_pct: 0.40,
    home_loan_self_occupied: 200000,
    home_loan_let_out: Infinity,
    family_pension_std_ded: 15000,
  },

  ADVANCE_TAX_SCHEDULE: [
    { due: "2025-06-15", pct: 15, label: "15 Jun 2025" },
    { due: "2025-09-15", pct: 45, label: "15 Sep 2025" },
    { due: "2025-12-15", pct: 75, label: "15 Dec 2025" },
    { due: "2026-03-15", pct: 100, label: "15 Mar 2026" },
  ],

};

