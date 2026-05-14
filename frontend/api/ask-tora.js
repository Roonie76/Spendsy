/**
 * Vercel Serverless Function — /api/ask-tora
 *
 * Acts as a proxy between the Spendsy frontend and the local Ollama LLM
 * running on the developer's machine, exposed via an ngrok tunnel.
 *
 * This eliminates the need for a separate Railway AI service deployment.
 */

const OLLAMA_BASE_URL =
  process.env.OLLAMA_BASE_URL ||
  "https://agreement-hardcover-skylight.ngrok-free.dev";

const OLLAMA_MODEL = process.env.MODEL_GEMMA || "gemma4:e2b";

const SYSTEM_PROMPT =
  "You are TORA, a friendly and concise AI financial assistant for the Spendsy app. " +
  "Help the user understand their spending, savings, and financial health. " +
  "Keep answers short and actionable. Do not use markdown unless asked.";

export default async function handler(req, res) {
  // Allow preflight OPTIONS from the Vercel frontend
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");

  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { question } = req.body || {};
  if (!question || !question.trim()) {
    return res.status(400).json({ error: "Question cannot be empty" });
  }

  const ollamaUrl = `${OLLAMA_BASE_URL}/api/chat`;

  try {
    const ollamaRes = await fetch(ollamaUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Bypass ngrok's free-tier browser interstitial page
        "ngrok-skip-browser-warning": "true",
      },
      body: JSON.stringify({
        model: OLLAMA_MODEL,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: question.trim() },
        ],
        stream: false,
        options: {
          temperature: 0.3,
          num_predict: 512,
          num_ctx: 2048,
        },
      }),
    });

    if (!ollamaRes.ok) {
      const errText = await ollamaRes.text();
      console.error("Ollama error:", errText);
      return res
        .status(502)
        .json({ error: "Ollama returned an error", detail: errText });
    }

    const data = await ollamaRes.json();
    const content = data?.message?.content?.trim() || "";

    if (!content) {
      return res.status(502).json({ error: "Empty response from model" });
    }

    return res.status(200).json({ answer: { mode: "chat", content } });
  } catch (err) {
    console.error("TORA proxy error:", err.message);

    if (err.cause?.code === "ECONNREFUSED" || err.message.includes("fetch")) {
      return res.status(503).json({
        error:
          "Cannot reach Ollama. Make sure your ngrok tunnel is running: ngrok http --url=agreement-hardcover-skylight.ngrok-free.dev 11434",
      });
    }

    return res.status(500).json({ error: err.message });
  }
}
