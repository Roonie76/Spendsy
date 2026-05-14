/**
 * Vercel Serverless Function — /api/ask-tora
 *
 * Data-aware AI proxy: fetches the user's financial context from the
 * Railway finance-service, injects it into the system prompt, then
 * forwards the enriched prompt to the local Ollama LLM via ngrok.
 */

const OLLAMA_BASE_URL =
  process.env.OLLAMA_BASE_URL ||
  "https://agreement-hardcover-skylight.ngrok-free.dev";

const FINANCE_SERVICE_URL =
  process.env.FINANCE_SERVICE_URL ||
  "https://finance-service-production-d0ec.up.railway.app";

const INTERNAL_API_KEY =
  process.env.INTERNAL_API_KEY || "internal-dev-key-that-is-long-enough-32c";

const OLLAMA_MODEL = process.env.MODEL_GEMMA || "gemma4:e2b";

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Fetch the full financial context for a user from the finance-service.
 * Returns null on any failure (TORA falls back to generic chat).
 */
async function fetchFinanceContext(userId) {
  if (!userId) return null;
  try {
    const url = `${FINANCE_SERVICE_URL}/internal/finance-context/${userId}`;
    const res = await fetch(url, {
      headers: { "X-Internal-API-Key": INTERNAL_API_KEY },
      signal: AbortSignal.timeout(8000),
    });
    if (!res.ok) {
      console.warn(`Finance context fetch failed: ${res.status}`);
      return null;
    }
    const json = await res.json();
    return json?.data || null;
  } catch (err) {
    console.warn("Finance context fetch error:", err.message);
    return null;
  }
}

/**
 * Build a compact text summary of the user's finances for the system prompt.
 * Keeps it tight to fit within the model's context window.
 */
function buildContextBlock(ctx) {
  if (!ctx) return "";

  const lines = [];

  // Summary
  const s = ctx.summary || {};
  lines.push(`## Financial Summary`);
  lines.push(`- Total Income: ₹${Number(s.income || 0).toLocaleString("en-IN")}`);
  lines.push(`- Total Expenses: ₹${Number(s.expense || 0).toLocaleString("en-IN")}`);
  lines.push(`- Balance: ₹${Number(s.balance || 0).toLocaleString("en-IN")}`);
  lines.push(`- Transaction Count: ${s.transaction_count || 0}`);

  // Wealth
  const w = ctx.wealth || {};
  if (w.net_worth) {
    lines.push(`\n## Net Worth`);
    lines.push(`- Assets: ₹${Number(w.assets || 0).toLocaleString("en-IN")}`);
    lines.push(`- Liabilities: ₹${Number(w.liabilities || 0).toLocaleString("en-IN")}`);
    lines.push(`- Net Worth: ₹${Number(w.net_worth || 0).toLocaleString("en-IN")}`);
  }

  // Monthly trends (compact)
  if (ctx.monthly_trends?.length) {
    lines.push(`\n## Monthly Trends (last ${ctx.monthly_trends.length} months)`);
    for (const m of ctx.monthly_trends) {
      lines.push(`- ${m.period}: Income ₹${Number(m.total_income).toLocaleString("en-IN")}, Expense ₹${Number(m.total_expense).toLocaleString("en-IN")}, Savings ₹${Number(m.net_savings).toLocaleString("en-IN")}`);
    }
  }

  // Recent transactions (last 15 for context, not all 50)
  const txns = (ctx.recent_transactions || []).slice(0, 15);
  if (txns.length) {
    lines.push(`\n## Recent Transactions (latest ${txns.length})`);
    for (const tx of txns) {
      const date = tx.date || "no date";
      const desc = tx.title || tx.description || "Untitled";
      const bal = tx.balance != null ? ` | Bal: ₹${Number(tx.balance).toLocaleString("en-IN")}` : "";
      lines.push(`- [${date}] ${tx.type.toUpperCase()} ₹${Number(tx.amount).toLocaleString("en-IN")} — ${desc} (${tx.category || "uncategorized"})${bal}`);
    }
  }

  // Goals
  if (ctx.goals?.length) {
    lines.push(`\n## Financial Goals`);
    for (const g of ctx.goals) {
      const pct = g.target_amount > 0 ? Math.round((g.current_amount / g.target_amount) * 100) : 0;
      lines.push(`- ${g.title}: ₹${Number(g.current_amount).toLocaleString("en-IN")} / ₹${Number(g.target_amount).toLocaleString("en-IN")} (${pct}%) ${g.is_completed ? "✅" : ""}`);
    }
  }

  // Plans
  if (ctx.plans?.length) {
    lines.push(`\n## Active Plans`);
    for (const p of ctx.plans) {
      lines.push(`- ${p.title}: Target ₹${Number(p.target_amount).toLocaleString("en-IN")}, Save ₹${Number(p.monthly_saving).toLocaleString("en-IN")}/mo, Status: ${p.status}`);
    }
  }

  // Loans
  if (ctx.loans?.length) {
    lines.push(`\n## Active Loans`);
    for (const l of ctx.loans) {
      lines.push(`- ${l.loan_type}: ₹${Number(l.remaining_balance).toLocaleString("en-IN")} remaining, EMI ₹${Number(l.emi_amount).toLocaleString("en-IN")}, Rate ${l.interest_rate}%`);
    }
  }

  return lines.join("\n");
}

// ─── Main Handler ─────────────────────────────────────────────────────────────

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");

  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "POST") return res.status(405).json({ error: "Method not allowed" });

  const { question, user_id } = req.body || {};
  if (!question || !question.trim()) {
    return res.status(400).json({ error: "Question cannot be empty" });
  }

  // 1. Fetch user's financial data from Railway DB
  const finContext = await fetchFinanceContext(user_id);
  const contextBlock = buildContextBlock(finContext);

  // 2. Build system prompt with real data
  const systemPrompt = [
    "You are TORA, a friendly and concise AI financial assistant for the Spendsy app.",
    "Help the user understand their spending, savings, and financial health.",
    "Keep answers short, specific, and actionable.",
    "When the user asks about their finances, use the data provided below.",
    "Always reference actual numbers from their data when answering.",
    "Format currency as ₹ with Indian number formatting.",
    "Do not use markdown formatting unless the user asks for it.",
    contextBlock
      ? `\n--- USER'S FINANCIAL DATA ---\n${contextBlock}\n--- END DATA ---`
      : "\n(No financial data available for this user yet.)",
  ].join("\n");

  // 3. Call Ollama via ngrok
  const ollamaUrl = `${OLLAMA_BASE_URL}/api/chat`;

  try {
    const ollamaRes = await fetch(ollamaUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true",
      },
      body: JSON.stringify({
        model: OLLAMA_MODEL,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: question.trim() },
        ],
        stream: false,
        options: {
          temperature: 0.3,
          num_predict: 512,
          num_ctx: 4096,
        },
      }),
    });

    if (!ollamaRes.ok) {
      const errText = await ollamaRes.text();
      console.error("Ollama error:", errText);
      return res.status(502).json({ error: "Ollama returned an error", detail: errText });
    }

    const data = await ollamaRes.json();
    const content = data?.message?.content?.trim() || "";

    if (!content) {
      return res.status(502).json({ error: "Empty response from model" });
    }

    return res.status(200).json({
      answer: { mode: "chat", content },
      data_loaded: !!finContext,
    });
  } catch (err) {
    console.error("TORA proxy error:", err.message);

    if (err.cause?.code === "ECONNREFUSED" || err.message.includes("fetch")) {
      return res.status(503).json({
        error: "Cannot reach Ollama. Make sure your ngrok tunnel is running.",
      });
    }

    return res.status(500).json({ error: err.message });
  }
}
