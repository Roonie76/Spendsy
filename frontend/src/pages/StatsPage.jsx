// Section 5 Stats Page
import React, { useState, useMemo, useEffect } from "react";
import {
  Download,
  Bot,
  Sparkles,
  Loader2,
  PieChart,
  BarChart3,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Zap,
  RefreshCw,
} from "lucide-react";
import {
  PieChart as RePieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  AreaChart,
  Area,
} from "recharts";
import { CATEGORIES } from "@shared/config/constants";
import {
  normalizeDate,
  formatIndianCompact,
} from "@shared/utils/helpers";
import { AIService } from "@shared/services/aiService";
import { downloadCSV } from "@shared/utils/exportUtils";

// --- CONFIG ---
const COLORS = [
  "#0ea5e9",
  "#22c55e",
  "#eab308",
  "#f97316",
  "#ef4444",
  "#a855f7",
  "#ec4899",
  "#6366f1",
  "#06b6d4",
  "#64748b",
];

// --- SUB-COMPONENT: CUSTOM CHART TOOLTIP ---
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#0f172a] border border-slate-700 p-3 rounded-xl shadow-2xl backdrop-blur-md z-50">
        <p className="text-slate-400 text-[10px] font-bold uppercase tracking-wider mb-2">
          {label}
        </p>
        {payload.map((entry, index) => (
          <div
            key={index}
            className="flex items-center justify-between gap-4 text-xs mb-1"
          >
            <div className="flex items-center gap-2">
              <div
                className="w-1.5 h-1.5 rounded-full"
                style={{ backgroundColor: entry.fill }}
              ></div>
              <span className="text-slate-300 capitalize">{entry.name}</span>
            </div>
            <span className="font-mono font-bold text-white">
              ₹{entry.value.toLocaleString("en-IN")}
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

// --- SUB-COMPONENT: INSIGHT CARD ---
const InsightCard = ({ type, title, message, impact }) => {
  let styles = "bg-slate-800 border-slate-700 text-slate-300";
  let Icon = Bot;

  switch (type) {
    case "alert":
      styles = "bg-rose-500/10 border-rose-500/20 text-rose-200";
      Icon = AlertTriangle;
      break;
    case "tip":
      styles = "bg-blue-500/10 border-blue-500/20 text-blue-200";
      Icon = Zap;
      break;
    case "praise":
      styles = "bg-emerald-500/10 border-emerald-500/20 text-emerald-200";
      Icon = CheckCircle2;
      break;
    case "trend":
      styles = "bg-purple-500/10 border-purple-500/20 text-purple-200";
      Icon = TrendingUp;
      break;
    default:
      break;
  }

  return (
    <div
      className={`p-4 rounded-2xl border ${styles} relative overflow-hidden transition-all hover:scale-[1.01]`}
    >
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <Icon className="w-5 h-5 opacity-80" />
          <h4 className="font-bold text-sm uppercase tracking-wide opacity-90">
            {title}
          </h4>
        </div>
        {impact === "high" && (
          <span className="bg-white/10 text-[10px] font-bold px-2 py-0.5 rounded-full">
            HIGH IMPACT
          </span>
        )}
      </div>
      <p className="text-xs opacity-80 leading-relaxed">{message}</p>
    </div>
  );
};

// --- MAIN PAGE COMPONENT ---
const StatsPage = ({ transactions = [], netWorthHistory = [], wealthItems = [], isLoading = false, error = null, showToast }) => {
  const [aiInsights, setAiInsights] = useState([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState(null);
  const [viewMode, setViewMode] = useState("expense");
  const [range, setRange] = useState("6M");
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [exportStatus, setExportStatus] = useState("idle");

  // Load cached insights on mount
  useEffect(() => {
    try {
      const cached = localStorage.getItem("watchdog_insights");
      if (cached) setAiInsights(JSON.parse(cached));
    } catch {
      setAiInsights([]);
    }
  }, []);

  const pieChartData = useMemo(() => {
    const categoryMap = {};
    let total = 0;

    // Calculate date threshold based on range.
    // All thresholds use local-midnight boundaries so they align with
    // normalizeDate() which also returns local-midnight for YYYY-MM-DD strings.
    const now = new Date();
    // Rewind to start of today (local midnight) so "1D" means today only,
    // not "last 24 clock-hours" which would cut off yesterday's data at odd times.
    const todayMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    let threshold = new Date(0); // Default: all time
    if (range === "1D")  threshold = todayMidnight;
    else if (range === "1W")  threshold = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6);
    else if (range === "1M")  threshold = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
    else if (range === "6M")  threshold = new Date(now.getFullYear(), now.getMonth() - 6, now.getDate());
    else if (range === "1Y")  threshold = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());

    transactions.forEach((t) => {
      const tDate = normalizeDate(t.date);
      if (!tDate || tDate < threshold) return;
      
      if (t.type === viewMode && t.amount) {
        const amt = parseFloat(t.amount);
        const catId = t.category || "uncategorized";
        const catName = CATEGORIES.find((c) => c.id === catId)?.name || catId;
        categoryMap[catName] = (categoryMap[catName] || 0) + amt;
        total += amt;
      }
    });
    return {
      data: Object.entries(categoryMap)
        .map(([name, value]) => ({ name, value }))
        .sort((a, b) => b.value - a.value),
      total,
    };
  }, [transactions, viewMode, range]);

  const selectedCategoryTransactions = useMemo(() => {
    if (!selectedCategory) return [];
    return transactions.filter((t) => {
      if (t.type !== viewMode) return false;
      const catId = t.category || "uncategorized";
      const catName = CATEGORIES.find((c) => c.id === catId)?.name || catId;
      return catName === selectedCategory;
    });
  }, [selectedCategory, transactions, viewMode]);

  const trendChartData = useMemo(() => {
    const dataMap = new Map();
    const getKey = (dateObj, unit) => {
      const y = dateObj.getFullYear(),
        m = dateObj.getMonth(),
        d = dateObj.getDate(),
        h = dateObj.getHours();
      if (unit === "hour") return `${y}-${m}-${d}-${h}`;
      if (unit === "day") return `${y}-${m}-${d}`;
      if (unit === "month") return `${y}-${m}`;
      return "";
    };

    const initData = (count, unit) => {
      for (let i = count - 1; i >= 0; i--) {
        const d = new Date();
        let label = "";
        if (unit === "hour") {
          d.setHours(d.getHours() - i);
          const hr = d.getHours();
          label =
            hr === 0
              ? "12am"
              : hr === 12
                ? "12pm"
                : hr > 12
                  ? `${hr - 12}pm`
                  : `${hr}am`;
        } else if (unit === "day") {
          d.setDate(d.getDate() - i);
          label = d.toLocaleDateString("en-US", {
            weekday: "short",
            day: "numeric",
          });
        } else if (unit === "month") {
          d.setDate(1);
          d.setMonth(d.getMonth() - i);
          label = d.toLocaleDateString("en-US", { month: "short" });
        }
        const key = getKey(d, unit);
        dataMap.set(key, {
          name: label,
          income: 0,
          expense: 0,
          sortKey: d.getTime(),
        });
      }
    };

    let unit = "month";
    if (range === "1D") {
      // Transactions from the backend carry only a date (YYYY-MM-DD) — no time
      // component. Rendering 24 hourly slots would leave every bar empty because
      // normalizeDate() produces local-midnight (hour 0) for all of them.
      // Use 2-day (today + yesterday) granularity instead so the chart is useful.
      initData(2, "day");
      unit = "day";
    } else if (range === "1W") {
      initData(7, "day");
      unit = "day";
    } else if (range === "1M") {
      initData(30, "day");
      unit = "day";
    } else if (range === "6M") {
      initData(6, "month");
      unit = "month";
    } else if (range === "1Y") {
      initData(12, "month");
      unit = "month";
    }

    transactions.forEach((t) => {
      const tDate = normalizeDate(t.date);
      if (!tDate) return;
      const key = getKey(tDate, unit);
      if (dataMap.has(key)) {
        const entry = dataMap.get(key);
        const amt = parseFloat(t.amount);
        if (t.type === "income") entry.income += amt;
        else entry.expense += amt;
      }
    });
    return Array.from(dataMap.values()).sort((a, b) => a.sortKey - b.sortKey);
  }, [transactions, range]);

  const hasTrendData = trendChartData.some((point) => point.income > 0 || point.expense > 0);

  const comparison = useMemo(() => {
    const monthly = new Map();
    transactions.forEach((t) => {
      const d = normalizeDate(t.date);
      if (!d) return;
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      const entry = monthly.get(key) || { income: 0, expense: 0 };
      const amt = Number.parseFloat(t.amount) || 0;
      if (t.type === "income") entry.income += amt;
      if (t.type === "expense") entry.expense += amt;
      monthly.set(key, entry);
    });

    const rows = Array.from(monthly.entries()).sort(([a], [b]) => a.localeCompare(b));
    const current = rows.at(-1)?.[1] || { income: 0, expense: 0 };
    const previous = rows.at(-2)?.[1] || { income: 0, expense: 0 };
    const previousYearKey = rows.at(-1)?.[0]
      ? `${Number(rows.at(-1)[0].slice(0, 4)) - 1}${rows.at(-1)[0].slice(4)}`
      : "";
    const previousYear = monthly.get(previousYearKey) || { income: 0, expense: 0 };
    const pct = (now, before) => before > 0 ? ((now - before) / before) * 100 : null;

    return {
      momExpense: pct(current.expense, previous.expense),
      yoyExpense: pct(current.expense, previousYear.expense),
      current,
      previous,
    };
  }, [transactions]);

  // --- 3. Net Worth Logic ---
  const augmentedNetWorthHistory = useMemo(() => {
    // 1. Calculate current totals from wealthItems
    const currentAssets = wealthItems
      .filter((i) => i.type === "asset")
      .reduce((acc, i) => acc + parseFloat(i.amount || 0), 0);
    const currentLiabilities = wealthItems
      .filter((i) => i.type === "liability")
      .reduce((acc, i) => acc + parseFloat(i.amount || 0), 0);
    const currentNet = currentAssets - currentLiabilities;

    // 2. Combine with actual history
    const baseHistory = [...netWorthHistory];

    // 3. If the last history point isn't today, add a 'virtual' point for today
    const today = new Date().toISOString().split('T')[0];
    const hasToday = baseHistory.some(s => s.date === today);

    if (!hasToday && (currentAssets > 0 || currentLiabilities > 0)) {
      baseHistory.push({
        date: today,
        total_assets: currentAssets,
        total_liabilities: currentLiabilities,
        net_worth: currentNet
      });
    }

    return baseHistory;
  }, [netWorthHistory, wealthItems]);

  // --- 4. THE WATCHDOG ENGINE ---
  const generateAIInsights = async () => {
    if (transactions.length === 0) {
      setAiError("Add some transactions first to see AI insights!");
      return;
    }

    setAiLoading(true);
    setAiError(null);

    try {
      // Create a snapshot of financial health for the AI
      const topCategories = pieChartData.data
        .slice(0, 3)
        .map((c) => `${c.name}: ₹${c.value}`)
        .join(", ");
      const totalIn = transactions
        .filter((t) => t.type === "income")
        .reduce((sum, t) => sum + parseFloat(t.amount), 0);
      const totalOut = transactions
        .filter((t) => t.type === "expense")
        .reduce((sum, t) => sum + parseFloat(t.amount), 0);

      const contextData = JSON.stringify({
        summary: {
          income: totalIn,
          expense: totalOut,
          balance: totalIn - totalOut,
        },
        topExpenses: topCategories,
        transactionCount: transactions.length,
        recentTrend: trendChartData.slice(-3), // Send the last 3 data points
      });

      const systemPrompt = `Act as "The Watchdog", a sharp financial surveillance AI. Analyze the user's spending. 
      Output exactly 3 insights in a JSON array. 
      Types allowed: "alert" (danger), "tip" (advice), "praise" (good habit), "trend" (patterns).
      Impact: "high" or "normal".
      Format: [{ "type": "...", "title": "...", "message": "...", "impact": "..." }]`;

      const jsonInsights = await AIService.askForJSON(
        systemPrompt,
        contextData,
      );

      if (Array.isArray(jsonInsights)) {
        setAiInsights(jsonInsights);
        try {
          localStorage.setItem("watchdog_insights", JSON.stringify(jsonInsights));
        } catch {
          // Cache is opportunistic; the live insight still renders.
        }
      }
    } catch (error) {
      console.error("Watchdog Error:", error);
      if (error.message?.includes("429")) {
        setAiError("Watchdog is resting (Rate Limit). Try again in a minute.");
      } else {
        setAiError("Failed to wake up the Watchdog. Check connection.");
      }
    } finally {
      setAiLoading(false);
    }
  };

  const clearInsights = () => {
    try {
      localStorage.removeItem("watchdog_insights");
    } catch {
      // Ignore storage failures in restricted browsing modes.
    }
    setAiInsights([]);
  };

  const exportAnalytics = () => {
    setExportStatus("loading");
    try {
      downloadCSV([
        ...pieChartData.data.map((row) => ({
          chart: "category_breakdown",
          label: row.name,
          value: row.value,
          type: viewMode,
        })),
        ...trendChartData.map((row) => ({
          chart: "trend",
          label: row.name,
          income: row.income,
          expense: row.expense,
        })),
      ]);
      setExportStatus("success");
    } catch {
      setExportStatus("error");
    } finally {
      window.setTimeout(() => setExportStatus("idle"), 1800);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-4 sm:space-y-6 pb-4 animate-pulse">
        <div className="h-8 w-36 rounded-xl bg-white/10" />
        <div className="h-32 rounded-2xl bg-white/10" />
        <div className="h-80 rounded-2xl bg-white/10" />
        <div className="h-80 rounded-2xl bg-white/10" />
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6 pb-4 animate-in fade-in">
      <div className="flex justify-between items-center px-1">
        <h2 className="text-xl sm:text-2xl font-bold text-white">Analytics</h2>
        <button
          onClick={exportAnalytics}
          disabled={exportStatus === "loading" || transactions.length === 0}
          className="flex items-center gap-2 rounded-xl bg-white/10 px-3 py-2 text-xs font-bold text-emerald-300 transition-colors hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {exportStatus === "loading" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
          Export
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200" role="alert">
          Could not load analytics data.
        </div>
      )}

      {exportStatus === "success" && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-xs text-emerald-200" role="status">
          Analytics export started.
        </div>
      )}
      {exportStatus === "error" && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-xs text-rose-200" role="alert">
          Could not export analytics.
        </div>
      )}

      {/* Watchdog Section */}
      <div className="bg-gradient-to-br from-[#0f172a] to-[#1e1b4b] p-6 rounded-[2rem] border border-white/10 relative overflow-hidden shadow-2xl">
        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 blur-[80px] rounded-full pointer-events-none"></div>
        <div className="flex justify-between items-start mb-6 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Bot className="w-5 h-5 text-indigo-400" />
              <h3 className="font-bold text-white text-lg tracking-tight">
                The Watchdog
              </h3>
            </div>
            <p className="text-xs text-slate-400">
              AI-powered financial surveillance
            </p>
          </div>
          <div className="flex gap-2">
            {aiInsights.length > 0 && !aiLoading && (
              <button
                onClick={clearInsights}
                className="p-2 bg-white/5 hover:bg-white/10 rounded-xl text-slate-400 transition-colors"
                aria-label="Clear Watchdog insights"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={generateAIInsights}
              disabled={aiLoading}
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-lg flex items-center gap-2"
            >
              {aiLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4 text-yellow-300" />
              )}
              {aiLoading
                ? "Analyzing..."
                : aiInsights.length > 0
                  ? "Re-Scan"
                  : "Run Scan"}
            </button>
          </div>
        </div>
        <div className="relative z-10 min-h-[50px]">
          {aiError && (
            <div className="bg-rose-500/10 border border-rose-500/20 p-4 rounded-xl text-xs text-rose-200 text-center">
              {aiError}
            </div>
          )}
          {!aiLoading && !aiError && aiInsights.length === 0 && (
            <div className="text-center py-6 text-slate-500 text-xs border border-dashed border-slate-700 rounded-xl">
              Tap 'Run Scan' to detect anomalies and patterns.
            </div>
          )}
          {aiInsights.length > 0 && (
            <div className="space-y-3 animate-in slide-in-from-bottom-4">
              {aiInsights.map((insight, idx) => (
                <InsightCard key={idx} {...insight} />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">This Month Expense</p>
          <p className="mt-2 text-xl font-black text-white">{formatIndianCompact(comparison.current.expense)}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">MoM Expense</p>
          <p className={`mt-2 text-xl font-black ${comparison.momExpense && comparison.momExpense > 0 ? "text-rose-300" : "text-emerald-300"}`}>
            {comparison.momExpense === null ? "N/A" : `${comparison.momExpense.toFixed(1)}%`}
          </p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">YoY Expense</p>
          <p className={`mt-2 text-xl font-black ${comparison.yoyExpense && comparison.yoyExpense > 0 ? "text-rose-300" : "text-emerald-300"}`}>
            {comparison.yoyExpense === null ? "N/A" : `${comparison.yoyExpense.toFixed(1)}%`}
          </p>
        </div>
      </div>

      {/* Category Breakdown */}
      <div className="bg-white/5 backdrop-blur-xl p-4 sm:p-6 rounded-2xl sm:rounded-[2rem] border border-white/10 relative overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-3">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <PieChart className="w-4 h-4" /> Category Breakdown
          </h3>
          <div className="sm:ml-auto flex bg-white/5 rounded-lg p-1 border border-white/10 self-start sm:self-auto">
            <button
              onClick={() => setViewMode("expense")}
              className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all ${viewMode === "expense" ? "bg-rose-500/20 text-rose-300" : "text-slate-400"}`}
            >
              Expense
            </button>
            <button
              onClick={() => setViewMode("income")}
              className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all ${viewMode === "income" ? "bg-emerald-500/20 text-emerald-300" : "text-slate-400"}`}
            >
              Income
            </button>
          </div>
        </div>
        <div className="h-64 relative">
          {pieChartData.data.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%" minWidth={0}>
              <RePieChart>
                <Pie
                  data={pieChartData.data}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                  stroke="none"
                >
                  {pieChartData.data.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </RePieChart>
            </ResponsiveContainer>
          ) : (
            <div className="absolute inset-0 flex items-center justify-center text-slate-500 text-xs">
              No data available
            </div>
          )}
          {pieChartData.data.length > 0 && (
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-xs text-slate-400 font-bold uppercase">
                Total
              </span>
              <span className="text-xl font-bold text-white">
                {formatIndianCompact(pieChartData.total)}
              </span>
            </div>
          )}
        </div>
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-40 overflow-y-auto custom-scrollbar pr-2">
          {pieChartData.data.map((entry, index) => (
            <button
              key={index}
              onClick={() => setSelectedCategory((current) => current === entry.name ? null : entry.name)}
              className={`flex justify-between items-center text-xs bg-white/5 p-2 rounded-lg text-left transition-colors hover:bg-white/10 ${selectedCategory === entry.name ? "ring-1 ring-blue-400/60" : ""}`}
            >
              <div className="flex items-center gap-2 truncate">
                <div
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: COLORS[index % COLORS.length] }}
                ></div>
                <span className="text-slate-300 truncate">{entry.name}</span>
              </div>
              <span className="font-bold text-slate-200 shrink-0 ml-2">
                {((entry.value / pieChartData.total) * 100).toFixed(0)}%
              </span>
            </button>
          ))}
        </div>
        {selectedCategory && (
          <div className="mt-4 rounded-xl border border-white/10 bg-black/20 p-3">
            <div className="mb-2 flex items-center justify-between gap-3">
              <h4 className="text-xs font-bold uppercase tracking-widest text-slate-400">{selectedCategory}</h4>
              <button onClick={() => setSelectedCategory(null)} className="text-[10px] font-bold text-slate-500 hover:text-white">Clear</button>
            </div>
            <div className="max-h-40 space-y-2 overflow-y-auto pr-1 custom-scrollbar">
              {selectedCategoryTransactions.slice(0, 8).map((transaction) => (
                <div key={transaction.id || `${transaction.title}-${transaction.date}`} className="flex justify-between gap-3 rounded-lg bg-white/5 px-3 py-2 text-xs">
                  <span className="truncate text-slate-300">{transaction.title || transaction.description || "Transaction"}</span>
                  <span className="font-bold text-white">{formatIndianCompact(Number.parseFloat(transaction.amount) || 0)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Trend Analysis */}
      <div className="bg-white/5 backdrop-blur-xl p-4 sm:p-6 rounded-2xl sm:rounded-[2rem] border border-white/10">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
            <BarChart3 className="w-4 h-4" /> Trend Analysis
          </h3>
          <div className="flex bg-black/20 p-1 rounded-xl border border-white/5 overflow-x-auto max-w-full">
            {["1D", "1W", "1M", "6M", "1Y"].map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all whitespace-nowrap ${range === r ? "bg-blue-500 text-white shadow-lg" : "text-slate-500 hover:text-slate-300"}`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
        <div className="h-[300px] w-full">
          {hasTrendData ? (
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <BarChart data={trendChartData} barGap={4}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.05)"
                vertical={false}
              />
              <XAxis
                dataKey="name"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#64748b", fontSize: 10 }}
                dy={10}
                interval={range === "1M" ? 2 : 0}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#64748b", fontSize: 10 }}
                tickFormatter={(val) =>
                  `₹${val >= 1000 ? (val / 1000).toFixed(0) + "k" : val}`
                }
              />
              <Tooltip
                cursor={{ fill: "rgba(255,255,255,0.05)", radius: 4 }}
                content={<CustomTooltip />}
              />
              <Bar
                dataKey="income"
                name="Income"
                fill="#10b981"
                radius={[4, 4, 0, 0]}
                maxBarSize={20}
              />
              <Bar
                dataKey="expense"
                name="Expense"
                fill="#f43f5e"
                radius={[4, 4, 0, 0]}
                maxBarSize={20}
              />
            </BarChart>
          </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-slate-700/50 text-xs text-slate-500">
              No trend data for this range
            </div>
          )}
        </div>
      </div>

      {/* Net Worth History Tracker */}
      <div className="bg-white/5 backdrop-blur-xl p-6 rounded-[2rem] border border-white/10">
        <div className="flex justify-between items-start mb-6 gap-4">
          <div>
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-1">
              <TrendingUp className="w-4 h-4 text-indigo-400" /> Net Worth History
            </h3>
            <p className="text-xs text-slate-500">Assets vs Liabilities over time</p>
          </div>
        </div>

        <div className="h-[300px] w-full relative">
          {augmentedNetWorthHistory && augmentedNetWorthHistory.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%" minWidth={0}>
              <AreaChart data={augmentedNetWorthHistory} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorAssets" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorLiabilities" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis
                  dataKey="date"
                  axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: 10 }} dy={10}
                  tickFormatter={(val) => {
                    const d = new Date(val);
                    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
                  }}
                />
                <YAxis
                  axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: 10 }}
                  tickFormatter={(val) => `₹${val >= 1000 ? (val / 1000).toFixed(0) + "k" : val}`}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px' }}
                  itemStyle={{ fontSize: '12px', fontWeight: 'bold' }}
                  labelStyle={{ color: '#94a3b8', fontSize: '10px', textTransform: 'uppercase', marginBottom: '8px' }}
                  formatter={(value) => [`₹${value.toLocaleString("en-IN")}`, '']}
                  labelFormatter={(label) => new Date(label).toDateString()}
                />
                <Area type="monotone" dataKey="total_assets" name="Assets" stroke="#10b981" strokeWidth={3} fillOpacity={1} fill="url(#colorAssets)" />
                <Area type="monotone" dataKey="total_liabilities" name="Liabilities" stroke="#f43f5e" strokeWidth={3} fillOpacity={1} fill="url(#colorLiabilities)" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 border border-dashed border-slate-700/50 rounded-xl">
              <TrendingUp className="w-8 h-8 mb-2 opacity-50 text-indigo-500" />
              <p className="text-xs font-bold uppercase tracking-widest text-slate-400">No History Available</p>
              <p className="text-[10px] mt-1 text-slate-500 max-w-[250px] text-center">Take a snapshot on the Wealth tab to start tracking your net worth journey.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StatsPage;
