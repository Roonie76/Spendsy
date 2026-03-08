import { AI_BASE_URL } from "../config/constants";
import { buildAuthHeader } from "../utils/helpers";

const getAuthHeaders = () => {
  const token =
    localStorage.getItem("access_token") ||
    localStorage.getItem("auth_token") ||
    localStorage.getItem("token");
  const header = buildAuthHeader(token);
  if (!header) return {};
  return {
    Authorization: header,
  };
};

const buildUrl = (path) => {
  const base = (AI_BASE_URL || "").replace(/\/$/, "");
  return `${base}/${path.replace(/^\//, "")}`;
};

export const AIService = {
  ask: async (systemPrompt, userContext, isJsonResponse = false) => {
    const response = await fetch(buildUrl("insights"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify({
        prompt: systemPrompt,
        context: userContext,
        response_format: isJsonResponse ? "json" : "text",
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data?.detail || "AI service error");
    }

    if (isJsonResponse) {
      return data.output;
    }
    return data.output || data.raw || "No insights generated.";
  },

  askForJSON: async (systemPrompt, userContext) => {
    try {
      const output = await AIService.ask(systemPrompt, userContext, true);
      if (Array.isArray(output) || typeof output === "object") {
        return output;
      }
      if (typeof output === "string") {
        return JSON.parse(output);
      }
      return [];
    } catch (e) {
      console.error("AI Service: JSON Parse Failed", e);
      return [];
    }
  },

  forecast: async (systemPrompt, userContext) => {
    const response = await fetch(buildUrl("forecast"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify({
        prompt: systemPrompt,
        context: userContext,
        response_format: "json",
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data?.detail || "AI service error");
    }
    return data.output;
  },
};
