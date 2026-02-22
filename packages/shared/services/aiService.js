import { API_KEY } from "../config/constants";

/**
 * AIService handles interaction with the Gemini API.
 * Optimized for Gemini 2.0 Flash with native JSON mode.
 */

// This will help you verify the .env connection in the browser console
console.log(
  "🚀 Gemini API Key Loaded:",
  API_KEY ? `${API_KEY.slice(0, 6)}...` : "NO",
);

export const AIService = {
  // 1. LOCAL RATE LIMITER
  checkLimit: () => {
    if (typeof window === "undefined") return;
    const key = "smartSpend_ai_usage";
    const now = Date.now();
    const usage = JSON.parse(
      localStorage.getItem(key) || '{"count": 0, "reset": 0}',
    );

    // Reset limit every hour
    if (now > usage.reset) {
      usage.count = 0;
      usage.reset = now + 3600000;
    }

    // Increased to 20 for better testing, but keeps your API safe
    if (usage.count >= 20) {
      throw new Error("AI_LIMIT_REACHED");
    }

    usage.count++;
    localStorage.setItem(key, JSON.stringify(usage));
  },

  // 2. CORE API HANDLER
  ask: async (systemPrompt, userContext, isJsonResponse = false) => {
    if (!API_KEY) throw new Error("AI Service Unavailable: Missing API Key");

    try {
      AIService.checkLimit();
    } catch (e) {
      // Re-throw specific limit error so the UI can show "Cooling Down"
      throw new Error("AI Engine is cooling down. Please try again later.");
    }

    const baseRules = `SYSTEM RULES: 
    1. Act only as an Indian Tax/Finance Expert. 
    2. Do NOT suggest illegal tax evasion. 
    3. Mention specific IT Act sections where applicable. 
    4. Keep responses concise and professional.`;

    const fullPrompt = `${baseRules}\n\nTASK:\n${systemPrompt}\n\nCONTEXT DATA:\n${userContext}`;

    // Basic sanitization
    const safePrompt = fullPrompt.replace(
      /ignore previous instructions/gi,
      "[REDACTED]",
    );

    try {
      // Using v1beta for Gemini 2.0 Flash features like native JSON mode
      const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${API_KEY}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contents: [{ parts: [{ text: safePrompt }] }],
            generationConfig: isJsonResponse
              ? {
                  response_mime_type: "application/json",
                  temperature: 0.2, // Lower temperature for more stable JSON
                }
              : { temperature: 0.7 },
          }),
        },
      );

      if (!response.ok) {
        const errorBody = await response.json();
        console.error("Gemini API Error:", errorBody);
        throw new Error(`AI Service Error: ${response.status}`);
      }

      const data = await response.json();
      const text = data.candidates?.[0]?.content?.parts?.[0]?.text;

      return text || (isJsonResponse ? "[]" : "No insights generated.");
    } catch (e) {
      console.error("AIService.ask failed:", e);
      throw new Error(e.message || "AI Service temporarily unavailable.");
    }
  },

  // 3. STRUCTURED DATA HANDLER
  askForJSON: async (systemPrompt, userContext) => {
    const jsonPrompt = `${systemPrompt}\n\nIMPORTANT: Response must be a valid JSON array or object only.`;

    const raw = await AIService.ask(jsonPrompt, userContext, true);

    try {
      return JSON.parse(raw);
    } catch (e) {
      console.error("AI Service: JSON Parse Failed", {
        error: e,
        rawOutput: raw,
      });
      return []; // Fallback to empty array to prevent UI crashes
    }
  },
};
