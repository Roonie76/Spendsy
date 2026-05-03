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
  LayoutGrid,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
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
  Sankey,
  Layer
} from "recharts";
import { CATEGORIES } from "@shared/config/constants";
import {
  normalizeDate,
  formatIndianCompact,
  formatLocalDate,
} from "@shared/utils/helpers";
import { AIService } from "@shared/services/aiService";
import { downloadCSV } from "@shared/utils/exportUtils";
import { StatsSkeleton } from "../components/ui/Skeletons";

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

// --- SUB-COMPONENT: CUSTOM SANKEY NODE ---
const CustomSankeyNode = ({ x, y, width, height, index, payload, containerWidth }) => {
  const isOut = x > 150; // Simple threshold to flip labels to the left
  return (
    <Layer key={`node-${index}`}>
      <rect x={x} y={y} width={width} height={height} fill="#3b82f6" fillOpacity={0.8} />
      <text
        x={isOut ? x - 10 : x + width + 10}
        y={y + height / 2 + 4}
        textAnchor={isOut ? 'end' : 'start'}
        fill="#94a3b8"
        fontSize="10"
        fontWeight="bold"
        className="uppercase tracking-widest"
      >
        {payload.name}
      </text>
    </Layer>
  );
};

// --- SUB-COMPONENT: SPENDING HEATMAP ---
const SpendingHeatmap = ({ data }) => {
  if (!data || data.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5 justify-center sm:justify-start">
      {data.map((day, idx) => (
        <div
          key={day.date}
          title={`${day.date}: ₹${day.value.toLocaleString()}`}
          className="w-3 h-3 rounded-[2px] transition-all hover:scale-125 cursor-help"
          style={{
            backgroundColor: day.value === 0 
              ? 'rgba(255,255,255,0.05)' 
              : `rgba(59, 130, 246, ${Math.max(0.2, day.intensity)})`,
            boxShadow: day.intensity > 0.8 ? '0 0 8px rgba(59, 130, 246, 0.4)' : 'none'
          }}
        />
      ))}
    </div>
  );
};

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
  let Icon = Sparkles;

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
  const [viewMode, setViewMode] = useState("expense");
  const [range, setRange] = useState("6M");
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [exportStatus, setExportStatus] = useState("idle");
  const [activeTab, setActiveTab] = useState("overview"); // 'overview', 'flow', 'trends'  // --- 1. Sankey Diagram Logic ---
  const sankeyData = useMemo(() => {
    const income = transactions.filter(t => t.type === 'income').reduce((acc, t) => acc + (parseFloat(t.amount) || 0), 0);
    const expenseGroups = transactions.filter(t => t.type === 'expense').reduce((acc, t) => {
      const cat = CATEGORIES.find(c => c.id === t.category)?.name || t.category || 'Other';
      acc[cat] = (acc[cat] || 0) + (parseFloat(t.amount) || 0);
      return acc;
    }, {});

    if (income === 0 && Object.keys(expenseGroups).length === 0) return null;

    const nodes = [{ name: 'Income' }];
    const links = [];
    
    let totalExpense = 0;
    Object.entries(expenseGroups).forEach(([cat, val]) => {
      nodes.push({ name: cat });
      links.push({ source: 0, target: nodes.length - 1, value: val });
      totalExpense += val;
    });

    const savings = Math.max(0, income - totalExpense);
    if (savings > 0 || totalExpense === 0) {
      nodes.push({ name: 'Savings' });
      links.push({ source: 0, target: nodes.length - 1, value: Math.max(1, savings) });
    }

    return { nodes, links };
  }, [transactions]);

  // --- 2. Heatmap Logic (Daily Density) ---
  const heatmapData = useMemo(() => {
    const activity = {};
    transactions.forEach(t => {
      if (t.type !== 'expense') return;
      const d = normalizeDate(t.date);
      if (!d) return;
      const key = d.toISOString().split('T')[0];
      activity[key] = (activity[key] || 0) + (parseFloat(t.amount) || 0);
    });

    const end = new Date();
    const start = new Date();
    start.setMonth(end.getMonth() - 6); // Last 6 months for heatmap

    const data = [];
    const max = Math.max(...Object.values(activity), 1);

    for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
      const key = d.toISOString().split('T')[0];
      const val = activity[key] || 0;
      data.push({
        date: key,
        value: val,
        intensity: val / max
      });
    }
    return data;
  }, [transactions]);
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
    const today = formatLocalDate(new Date());
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
  const suggestions = useMemo(() => {
    const list = [];
    if (comparison.momExpense > 10) {
      list.push({
        type: "alert",
        title: "Spending Surge",
        message: `Your expenses increased by ${comparison.momExpense.toFixed(1)}% compared to last month. Consider reviewing your top categories.`,
        impact: "high"
      });
    } else if (comparison.momExpense < -5) {
      list.push({
        type: "praise",
        title: "Great Savings",
        message: "You've spent significantly less than last month! Keep up the disciplined budgeting.",
        impact: "normal"
      });
    }

    if (pieChartData.data.length > 0) {
      const top = pieChartData.data[0];
      const pct = ((top.value / pieChartData.total) * 100).toFixed(0);
      if (pct > 40) {
        list.push({
          type: "tip",
          title: "Category Heavy",
          message: `${top.name} accounts for ${pct}% of your spending. Diversifying your budget could reduce risk.`,
          impact: "normal"
        });
      }
    }

    if (augmentedNetWorthHistory.length > 1) {
      const last = augmentedNetWorthHistory.at(-1)?.net_worth || 0;
      const prev = augmentedNetWorthHistory.at(-2)?.net_worth || 0;
      if (last > prev) {
        list.push({
          type: "trend",
          title: "Wealth Growth",
          message: "Your net worth is trending upwards. This is a great sign for your long-term financial health.",
          impact: "normal"
        });
      }
    }

    // Default suggestions if list is small
    if (list.length < 2) {
      list.push({
        type: "tip",
        title: "Smart Budgeting",
        message: "Try the 50/30/20 rule: 50% for needs, 30% for wants, and 20% for savings or debt repayment.",
        impact: "normal"
      });
    }

    return list;
  }, [comparison, pieChartData, augmentedNetWorthHistory]);
  const exportAnalytics = () => {
    setExportStatus("loading");
    try {
      // Filter transactions based on the same logic used for charts
      const now = new Date();
      const todayMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      let threshold = new Date(0);
      if (range === "1D") threshold = todayMidnight;
      else if (range === "1W") threshold = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 6);
      else if (range === "1M") threshold = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
      else if (range === "6M") threshold = new Date(now.getFullYear(), now.getMonth() - 6, now.getDate());
      else if (range === "1Y") threshold = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());

      const filteredTransactions = transactions.filter(t => {
        const tDate = normalizeDate(t.date);
        return tDate && tDate >= threshold;
      });

      downloadCSV(filteredTransactions);
      setExportStatus("success");
    } catch (error) {
      console.error("Export failed:", error);
      setExportStatus("error");
    } finally {
      window.setTimeout(() => setExportStatus("idle"), 1800);
    }
  };

  if (isLoading) {
    return <StatsSkeleton />;
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

      {/* --- TAB NAVIGATION --- */}
      <div className="flex bg-white/5 p-1 rounded-2xl border border-white/10 w-fit mx-auto sm:mx-1">
        {[
          { id: 'overview', label: 'Snapshot', icon: LayoutGrid },
          { id: 'flow', label: 'Architecture', icon: RefreshCw },
          { id: 'trends', label: 'History', icon: BarChart3 }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 sm:px-6 py-2.5 rounded-xl text-[10px] sm:text-xs font-bold transition-all ${
              activeTab === tab.id 
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20' 
                : 'text-slate-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Charts */}
        <div className="lg:col-span-8 space-y-6">
          <AnimatePresence mode="wait">
            {activeTab === 'flow' && sankeyData && (
              <motion.div 
                key="flow"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="bg-white/5 backdrop-blur-xl p-6 rounded-[2rem] border border-white/10 overflow-hidden"
              >
                 <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-8">
                  <RefreshCw className="w-4 h-4 text-emerald-400" /> Money Flow Architecture
                </h3>
                <div className="h-80 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <Sankey
                      data={sankeyData}
                      node={<CustomSankeyNode />}
                      link={{ stroke: 'rgba(59, 130, 246, 0.2)' }}
                      margin={{ left: 10, right: 110, top: 20, bottom: 20 }}
                      nodePadding={50}
                    >
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '12px' }}
                        itemStyle={{ color: '#fff', fontSize: '10px', fontWeight: 'bold' }}
                        formatter={(v) => `₹${formatIndianCompact(v)}`}
                      />
                    </Sankey>
                  </ResponsiveContainer>
                </div>
              </motion.div>
            )}

            {activeTab === 'overview' && (
              <motion.div
                key="overview"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                {/* Category Breakdown */}
                <div className="bg-white/5 backdrop-blur-xl p-6 rounded-[2rem] border border-white/10 relative overflow-hidden">
                  <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-6">
                    <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                      <PieChart className="w-4 h-4" /> Category Distribution
                    </h3>
                    <div className="sm:ml-auto flex bg-white/5 rounded-lg p-1 border border-white/10 self-start sm:self-auto">
                      <button
                        onClick={() => setViewMode("expense")}
                        className={`px-3 py-1.5 rounded-md text-[10px] font-bold transition-all ${viewMode === "expense" ? "bg-rose-500/20 text-rose-300" : "text-slate-400"}`}
                      >
                        Expense
                      </button>
                      <button
                        onClick={() => setViewMode("income")}
                        className={`px-3 py-1.5 rounded-md text-[10px] font-bold transition-all ${viewMode === "income" ? "bg-emerald-500/20 text-emerald-300" : "text-slate-400"}`}
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
                        <span className="text-[10px] text-slate-400 font-bold uppercase">
                          Total
                        </span>
                        <span className="text-xl font-bold text-white">
                          {formatIndianCompact(pieChartData.total)}
                        </span>
                      </div>
                    )}
                  </div>
                  <div className="mt-6 grid grid-cols-2 sm:grid-cols-3 gap-3 max-h-40 overflow-y-auto custom-scrollbar pr-2">
                    {pieChartData.data.map((entry, index) => (
                      <button
                        key={index}
                        onClick={() => setSelectedCategory((current) => current === entry.name ? null : entry.name)}
                        className={`flex justify-between items-center text-[10px] bg-white/5 p-3 rounded-xl text-left transition-colors hover:bg-white/10 ${selectedCategory === entry.name ? "ring-1 ring-blue-400/60" : ""}`}
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
                </div>

                {/* Activity Heatmap */}
                <div className="bg-white/5 backdrop-blur-xl p-6 rounded-[2rem] border border-white/10">
                  <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-6">
                    <Zap className="w-4 h-4 text-blue-400" /> Spending Activity Density
                  </h3>
                  <SpendingHeatmap data={heatmapData} />
                  <div className="mt-4 flex items-center gap-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                    <span>Less</span>
                    <div className="flex gap-1">
                      {[0, 0.2, 0.4, 0.6, 0.8].map(v => (
                        <div key={v} className="w-3 h-3 rounded-[2px]" style={{ backgroundColor: `rgba(59, 130, 246, ${Math.max(0.05, v)})` }}></div>
                      ))}
                    </div>
                    <span>More</span>
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'trends' && (
              <motion.div
                key="trends"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                {/* Trend Analysis */}
                <div className="bg-white/5 backdrop-blur-xl p-6 rounded-[2rem] border border-white/10">
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
                    <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                      <BarChart3 className="w-4 h-4 text-emerald-400" /> Trend Analysis
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
                  <div className="h-[280px] w-full">
                    {hasTrendData ? (
                      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                        <BarChart data={trendChartData} barGap={4}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                          <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: 10 }} dy={10} interval={range === "1M" ? 2 : 0} />
                          <YAxis axisLine={false} tickLine={false} tick={{ fill: "#64748b", fontSize: 10 }} tickFormatter={(val) => `₹${val >= 1000 ? (val / 1000).toFixed(0) + "k" : val}`} />
                          <Tooltip cursor={{ fill: "rgba(255,255,255,0.05)", radius: 4 }} content={<CustomTooltip />} />
                          <Bar dataKey="income" name="Income" fill="#10b981" radius={[4, 4, 0, 0]} maxBarSize={20} />
                          <Bar dataKey="expense" name="Expense" fill="#f43f5e" radius={[4, 4, 0, 0]} maxBarSize={20} />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="flex h-full items-center justify-center rounded-xl border border-dashed border-slate-700/50 text-xs text-slate-500">No trend data for this range</div>
                    )}
                  </div>
                </div>

                {/* Net Worth Tracker */}
                <div className="bg-white/5 backdrop-blur-xl p-6 rounded-[2rem] border border-white/10 relative overflow-hidden group">
                  <div className="absolute -top-24 -left-24 w-64 h-64 bg-emerald-500/5 blur-[80px] rounded-full pointer-events-none group-hover:bg-emerald-500/10 transition-colors"></div>
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4 relative z-10">
                    <div>
                      <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-2">
                        <TrendingUp className="w-4 h-4 text-indigo-400" /> Wealth Evolution
                      </h3>
                      <p className="text-2xl font-black text-white tracking-tight">{formatIndianCompact(augmentedNetWorthHistory.at(-1)?.net_worth || 0)}</p>
                    </div>
                    <div className="flex items-center gap-3 text-[10px] font-bold uppercase tracking-widest">
                      <div className="flex items-center gap-1.5 text-emerald-400"><div className="w-2 h-2 rounded-full bg-emerald-500"></div>Assets</div>
                      <div className="flex items-center gap-1.5 text-rose-400"><div className="w-2 h-2 rounded-full bg-rose-500"></div>Liabilities</div>
                    </div>
                  </div>

                  <div className="h-[280px] w-full relative">
                    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                      <AreaChart data={augmentedNetWorthHistory} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorAssets" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                          </linearGradient>
                          <linearGradient id="colorLiabilities" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                            <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                        <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: "#475569", fontSize: 9 }} dy={10} tickFormatter={(val) => new Date(val).toLocaleDateString("en-US", { month: "short", day: "numeric" })} />
                        <YAxis axisLine={false} tickLine={false} tick={{ fill: "#475569", fontSize: 9 }} tickFormatter={(val) => `₹${val >= 1000 ? (val / 1000).toFixed(0) + "k" : val}`} />
                        <Tooltip cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1 }} content={<CustomTooltip />} />
                        <Area type="monotone" dataKey="total_assets" name="Assets" stroke="#10b981" strokeWidth={3} fill="url(#colorAssets)" />
                        <Area type="monotone" dataKey="total_liabilities" name="Liabilities" stroke="#f43f5e" strokeWidth={3} fill="url(#colorLiabilities)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Right Column: Suggestions & Quick Stats */}
        <div className="lg:col-span-4 space-y-6">
          {/* Smart Suggestions */}
          <div className="bg-gradient-to-br from-indigo-500/10 to-purple-500/10 backdrop-blur-xl p-6 rounded-[2rem] border border-white/10 shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/20 blur-[40px] rounded-full"></div>
            <div className="flex items-center gap-2 mb-4 relative z-10">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              <h3 className="font-bold text-white text-lg tracking-tight">Smart Suggestions</h3>
            </div>
            <div className="space-y-3 relative z-10">
              {suggestions.map((suggestion, idx) => (
                <InsightCard key={idx} {...suggestion} />
              ))}
            </div>
          </div>

          {/* Quick Stats Grid */}
          <div className="grid grid-cols-1 gap-4">
            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6 backdrop-blur-md">
              <div className="flex items-center gap-2 mb-4">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <TrendingUp className="w-4 h-4 text-blue-400" />
                </div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">This Month Expense</p>
              </div>
              <p className="text-3xl font-black text-white">{formatIndianCompact(comparison.current.expense)}</p>
              <div className="mt-4 flex items-center gap-2">
                 <span className={`text-xs font-bold ${comparison.momExpense && comparison.momExpense > 0 ? "text-rose-400" : "text-emerald-400"}`}>
                   {comparison.momExpense === null ? "N/A" : `${comparison.momExpense > 0 ? "+" : ""}${comparison.momExpense.toFixed(1)}%`}
                 </span>
                 <span className="text-[10px] text-slate-500 font-bold uppercase">vs Prev Month</span>
              </div>
            </div>

            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6 backdrop-blur-md">
              <div className="flex items-center gap-2 mb-4">
                <div className="p-2 bg-purple-500/10 rounded-lg">
                  <Zap className="w-4 h-4 text-purple-400" />
                </div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">MoM Growth</p>
              </div>
              <p className={`text-3xl font-black ${comparison.momExpense && comparison.momExpense > 0 ? "text-rose-300" : "text-emerald-300"}`}>
                {comparison.momExpense === null ? "N/A" : `${comparison.momExpense.toFixed(1)}%`}
              </p>
              <p className="mt-2 text-[10px] text-slate-500 font-bold uppercase tracking-widest">Monthly momentum</p>
            </div>

            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6 backdrop-blur-md">
              <div className="flex items-center gap-2 mb-4">
                <div className="p-2 bg-emerald-500/10 rounded-lg">
                  <BarChart3 className="w-4 h-4 text-emerald-400" />
                </div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">YoY Trend</p>
              </div>
              <p className={`text-3xl font-black ${comparison.yoyExpense && comparison.yoyExpense > 0 ? "text-rose-300" : "text-emerald-300"}`}>
                {comparison.yoyExpense === null ? "N/A" : `${comparison.yoyExpense.toFixed(1)}%`}
              </p>
              <p className="mt-2 text-[10px] text-slate-500 font-bold uppercase tracking-widest">Yearly Performance</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatsPage;
