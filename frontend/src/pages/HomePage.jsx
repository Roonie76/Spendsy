import React, { useMemo, useState } from "react"; import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  FileText,
  Coins,
  History,
  Scale,
  ArrowRightLeft,
  Landmark,
  AlertTriangle,
  TrendingDown,
  TrendingUp,
  Inbox,
  Calendar,
} from "lucide-react";
import TransactionItem from "../components/domain/TransactionItem";
import { TABS } from "@shared/config/constants";
import { normalizeDate, formatIndianCompact, getCurrentFinancialYear } from "@shared/utils/helpers";
import { TaxService } from "@shared/services/taxService";
import { cn } from "@shared/utils/cn";
import { 
  Sparkles, 
  Activity, 
  Lightbulb, 
  ShieldCheck, 
  TrendingUp as TrendUpIcon, 
  ArrowUpRight,
  ChevronRight
} from "lucide-react";



const HomePage = ({
  transactions,
  wealthItems = [],
  setActiveTab,
  onDelete,
  settings,
  totals,
  theme = "dark",
  taxProfile,
  netWorthHistory = [],
  isLoading = false,
  error = null,
}) => {


  const bouncySpring = { type: "spring", stiffness: 500, damping: 20, mass: 1 };

  // ── Fiscal year ─────────────────────────────────────────────────────────────
  const fiscalYear = useMemo(() => getCurrentFinancialYear(), []);

  // ── Tax data ────────────────────────────────────────────────────────────────
  const taxData = useMemo(() => {
    if (!transactions || transactions.length === 0) return null;
    try {
      return TaxService.calculate(transactions, taxProfile, wealthItems, settings);
    } catch {
      return null;
    }
  }, [transactions, taxProfile, wealthItems, settings]);

  // ── Net worth MoM change ────────────────────────────────────────────────────
  const netWorthChange = useMemo(() => {
    if (!netWorthHistory || netWorthHistory.length < 2) return null;
    const sorted = [...netWorthHistory].sort((a, b) => new Date(a.date) - new Date(b.date));
    const current = parseFloat(sorted[sorted.length - 1]?.net_worth || 0);
    const previous = parseFloat(sorted[sorted.length - 2]?.net_worth || 0);
    if (previous === 0) return null;
    const pct = ((current - previous) / Math.abs(previous)) * 100;
    return { pct: Math.round(pct * 10) / 10, isUp: pct >= 0 };
  }, [netWorthHistory]);



  // ── Metrics ─────────────────────────────────────────────────────────────────
  const metrics = useMemo(() => {
    const txList = Array.isArray(transactions) ? transactions : [];
    const now = new Date();



    // Net worth — always from wealthItems (static, not range-filtered)
    const wealthList = Array.isArray(wealthItems) ? wealthItems : [];
    const netWorth = wealthList.reduce((acc, curr) => {
      const amt = parseFloat(curr.amount || curr.value || 0);
      if (curr.type === "asset") return acc + amt;
      if (curr.type === "liability") return acc - amt;
      return acc;
    }, 0);

    // Monthly expense — current calendar month, for budget bar
    const now2 = new Date();
    const monthlyData = txList.filter(t => {
      const d = normalizeDate(t.date);
      if (!d) return false;
      return d.getMonth() === now2.getMonth() && d.getFullYear() === now2.getFullYear();
    });
    const isCurrentMonth = true; // budget bar always current month
    const localMonthExpense = monthlyData
      .filter(t => t.type === "expense" || t.type === "debit")
      .reduce((acc, t) => acc + (parseFloat(t.amount) || 0), 0);
    const serverExpense = totals?.month_expense || totals?.monthExpense;
    const expense = serverExpense !== undefined ? parseFloat(serverExpense) : localMonthExpense;

    // Today spend
    const todayStr = now.toISOString().slice(0, 10);
    const todayExpense = monthlyData
      .filter(t => {
        if (t.type !== "expense" && t.type !== "debit") return false;
        const d = normalizeDate(t.date);
        return d && d.toISOString().slice(0, 10) === todayStr;
      })
      .reduce((acc, t) => acc + (parseFloat(t.amount) || 0), 0);

    // Tax
    const estimatedTax = taxData ? Math.round(Math.min(taxData.totalTaxNew, taxData.totalTaxOld)) : 0;
    const taxableIncome = taxData ? Math.round(Math.min(taxData.taxableNew, taxData.taxableOld)) : 0;
    const recommendedRegime = taxData?.recommendedRegime || "new";

    // Cards & count
    const cardCount = wealthList.filter(i =>
      String(i?.name || "").toLowerCase().match(/card|visa|mastercard|rupay/)
    ).length;

    return {
      netWorth, expense, todayExpense,
      totalTaxable: taxableIncome, estimatedTax, recommendedRegime,
      count: txList.length, cardCount,
    };
  }, [transactions, wealthItems, totals, taxData]);

  const budget = parseFloat(settings?.monthlyBudget) || 0;
  const hasBudget = settings?.monthlyBudget != null && settings?.monthlyBudget !== "";
  const percentage = budget > 0 ? (metrics.expense / budget) * 100 : 0;
  const cappedPercentage = Math.min(100, percentage);

  // ── Loading ──────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-6 md:space-y-10 animate-pulse" role="status" aria-label="Loading dashboard">
        <div className={cn("h-52 rounded-[2rem]", theme === "dark" ? "bg-white/5" : "bg-slate-100")} />
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-5 space-y-4">
            <div className={cn("h-20 rounded-[1.5rem]", theme === "dark" ? "bg-white/5" : "bg-slate-100")} />
            <div className={cn("h-28 rounded-[1.5rem]", theme === "dark" ? "bg-white/5" : "bg-slate-100")} />
            <div className="grid grid-cols-2 gap-3">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className={cn("h-28 rounded-[1.5rem]", theme === "dark" ? "bg-white/5" : "bg-slate-100")} />
              ))}
            </div>
          </div>
          <div className="lg:col-span-7">
            <div className={cn("h-96 rounded-[2rem]", theme === "dark" ? "bg-white/5" : "bg-slate-100")} />
          </div>
        </div>
        <span className="sr-only">Loading dashboard data...</span>
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center" role="alert">
        <AlertTriangle className={cn("w-12 h-12 mb-4", theme === "dark" ? "text-rose-400" : "text-rose-500")} />
        <h3 className={cn("text-lg font-bold mb-2", theme === "dark" ? "text-white" : "text-slate-900")}>
          Something went wrong
        </h3>
        <p className={cn("text-sm max-w-md", theme === "dark" ? "text-white/50" : "text-slate-500")}>
          We couldn't load your dashboard data. Please try refreshing the page.
        </p>
      </div>
    );
  }

  // ── MetricTile ───────────────────────────────────────────────────────────────
  const MetricTile = ({ title, value, icon: Icon, colorClass, tab, isSpecial = false, subtitle }) => (
    <div className="relative group">
      <div className={cn(
        "pointer-events-none absolute -inset-3 rounded-[3rem] opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-2xl",
        isSpecial ? "bg-blue-500/40"
          : colorClass?.includes("blue") ? "bg-blue-500/30"
            : colorClass?.includes("emerald") ? "bg-emerald-500/30"
              : colorClass?.includes("purple") ? "bg-purple-500/30"
                : "bg-white/20",
      )} />
      <motion.button
        whileHover={{ scale: 1.05, y: -10 }}
        whileTap={{ scale: 0.95 }}
        transition={bouncySpring}
        onClick={() => setActiveTab(tab)}
        aria-label={`${title}: ${value}. Click to view details.`}
        className={cn(
          "relative overflow-hidden p-4 sm:p-6 rounded-[1.5rem] sm:rounded-[2rem] border text-left w-full transition-shadow duration-300",
          isSpecial ? "bg-blue-600 border-blue-400 shadow-blue-500/40"
            : theme === "dark" ? "bg-white/10 border-white/10 backdrop-blur-md shadow-2xl"
              : "bg-white border-white shadow-xl shadow-blue-500/10",
        )}
      >
        <div className={cn("mb-4 p-3 rounded-2xl inline-flex", isSpecial ? "bg-white/20 text-white" : colorClass)} aria-hidden="true">
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className={cn(
            "text-[10px] font-black uppercase tracking-[0.2em] mb-1",
            isSpecial ? "text-blue-100" : theme === "dark" ? "text-blue-400/60" : "text-blue-600",
          )}>
            {title}
          </p>
          <p className={cn(
            "text-xl sm:text-2xl font-black tracking-tighter break-all",
            isSpecial ? "text-white" : theme === "dark" ? "text-white" : "text-indigo-950",
          )}>
            {value}
          </p>
          {subtitle && (
            <p className={cn("text-[10px] mt-1 font-semibold", isSpecial ? "text-blue-200/60" : "opacity-40")}>
              {subtitle}
            </p>
          )}
        </div>
      </motion.button>
    </div>
  );

  const txList = Array.isArray(transactions) ? transactions : [];

  // ── Health Score Calculation ───────────────────────────────────────────────
  const healthScore = useMemo(() => {
    const income = parseFloat(totals?.month_income || totals?.monthIncome || 0);
    const expense = parseFloat(totals?.month_expense || totals?.monthExpense || 0);
    const budget = parseFloat(settings?.monthlyBudget) || 0;
    
    // 1. Savings Rate (40%)
    const savingsRate = income > 0 ? (income - expense) / income : 0;
    const savingsScore = Math.min(100, Math.max(0, savingsRate * 200)); // 50% savings = 100 points
    
    // 2. Budget Adherence (40%)
    let budgetScore = 100;
    if (budget > 0) {
      const ratio = expense / budget;
      budgetScore = Math.max(0, 100 - (ratio > 1 ? (ratio - 1) * 200 : 0));
    }
    
    // 3. Diversification (20%) - Mocked for now based on wealth count
    const wealthCount = wealthItems.length;
    const divScore = Math.min(100, wealthCount * 20); 
    
    const final = Math.round((savingsScore * 0.4) + (budgetScore * 0.4) + (divScore * 0.2));
    return Math.min(100, Math.max(20, final));
  }, [totals, settings, wealthItems]);

  // ── Tora Pulse Insights ───────────────────────────────────────────────────
  const pulseInsights = useMemo(() => {
    const insights = [];
    const budget = parseFloat(settings?.monthlyBudget) || 0;
    const expense = parseFloat(totals?.month_expense || totals?.monthExpense || 0);

    if (budget > 0 && expense > budget) {
      insights.push({
        text: `You've exceeded your monthly budget by ${formatIndianCompact(expense - budget)}.`,
        icon: AlertTriangle,
        color: "text-rose-500",
        bg: "bg-rose-500/10"
      });
    } else if (budget > 0 && expense > budget * 0.8) {
      insights.push({
        text: "Approaching budget limit. Consider pausing non-essential spends.",
        icon: TrendingDown,
        color: "text-amber-500",
        bg: "bg-amber-500/10"
      });
    }

    if (netWorthChange?.isUp) {
      insights.push({
        text: `Impressive! Your net worth is up ${netWorthChange.pct}% this month.`,
        icon: TrendUpIcon,
        color: "text-emerald-500",
        bg: "bg-emerald-500/10"
      });
    }

    insights.push({
      text: "Tora Tip: Tracking daily expenses increases savings by 15% on average.",
      icon: Lightbulb,
      color: "text-blue-500",
      bg: "bg-blue-500/10"
    });

    return insights;
  }, [settings, totals, netWorthChange]);

  const [currentPulseIdx, setCurrentPulseIdx] = useState(0);

  // Auto-cycle insights every 5 seconds
  React.useEffect(() => {
    if (pulseInsights.length <= 1) return;
    const interval = setInterval(() => {
      setCurrentPulseIdx((prev) => (prev + 1) % pulseInsights.length);
    }, 5000);
    return () => clearInterval(interval);
  }, [pulseInsights]);

  return (
    <div className="space-y-6 md:space-y-8 pb-28" role="main" aria-label="Financial dashboard">
      
      {/* ── TOP BANNER: Pulse & Health ────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        
        {/* TORA PULSE */}
        <div className="md:col-span-8">
          <motion.div 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={{ scale: 1.01 }}
            onClick={() => {
              window.dispatchEvent(new CustomEvent("open-tora", { 
                detail: { query: `Tell me more about: ${pulseInsights[currentPulseIdx].text}` } 
              }));
            }}
            className={cn(
              "relative overflow-hidden h-full p-4 rounded-[2rem] border flex items-center gap-4 cursor-pointer group/pulse",
              theme === "dark" ? "bg-white/[0.03] border-white/10 hover:bg-white/[0.05]" : "bg-white border-slate-100 hover:border-blue-200"
            )}
          >
            <div className="flex-shrink-0 w-10 h-10 rounded-2xl bg-blue-500/10 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-blue-500" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-[10px] font-black uppercase tracking-[0.2em] text-blue-500/60">Tora Pulse</span>
                <div className="flex gap-1">
                  {pulseInsights.map((_, i) => (
                    <div 
                      key={i} 
                      className={cn(
                        "w-1 h-1 rounded-full transition-all duration-300",
                        i === currentPulseIdx ? "w-3 bg-blue-500" : "bg-blue-500/20"
                      )} 
                    />
                  ))}
                </div>
              </div>
              <AnimatePresence mode="wait">
                <motion.p 
                  key={currentPulseIdx}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  className={cn(
                    "text-sm font-bold truncate",
                    theme === "dark" ? "text-white" : "text-slate-900"
                  )}
                >
                  {pulseInsights[currentPulseIdx].text}
                </motion.p>
              </AnimatePresence>
            </div>
            <motion.button 
              whileTap={{ scale: 0.9 }}
              onClick={() => {
                setCurrentPulseIdx((prev) => (prev + 1) % pulseInsights.length);
              }}
              className="relative z-10 p-2 hover:bg-white/10 rounded-xl transition-colors shrink-0"
              aria-label="Next insight"
            >
              <ChevronRight className="w-4 h-4 opacity-60" />
            </motion.button>
          </motion.div>
        </div>

        {/* HEALTH SCORE GAUGE */}
        <div className="md:col-span-4">
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className={cn(
              "p-4 rounded-[2rem] border flex items-center justify-between gap-4",
              theme === "dark" ? "bg-white/[0.03] border-white/10" : "bg-white border-slate-100"
            )}
          >
            <div className="flex flex-col">
              <span className="text-[10px] font-black uppercase tracking-[0.2em] text-emerald-500/60 mb-1">Financial Health</span>
              <div className="flex items-baseline gap-1">
                <span className={cn("text-2xl font-black tracking-tighter", theme === "dark" ? "text-white" : "text-slate-900")}>
                  {healthScore}
                </span>
                <span className="text-xs font-bold opacity-30">/100</span>
              </div>
            </div>
            
            <div className="relative w-14 h-14">
              <svg className="w-full h-full transform -rotate-90">
                <circle
                  cx="28"
                  cy="28"
                  r="24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="6"
                  className={theme === "dark" ? "text-white/5" : "text-slate-100"}
                />
                <motion.circle
                  cx="28"
                  cy="28"
                  r="24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="6"
                  strokeDasharray="150"
                  initial={{ strokeDashoffset: 150 }}
                  animate={{ strokeDashoffset: 150 - (150 * healthScore) / 100 }}
                  transition={{ duration: 1.5, ease: "circOut" }}
                  strokeLinecap="round"
                  className={cn(
                    healthScore > 80 ? "text-emerald-500" : healthScore > 50 ? "text-blue-500" : "text-rose-500"
                  )}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <Activity className={cn(
                  "w-4 h-4",
                  healthScore > 80 ? "text-emerald-500" : healthScore > 50 ? "text-blue-500" : "text-rose-500"
                )} />
              </div>
            </div>
          </motion.div>
        </div>
      </div>



      {/* ── MAIN GRID ────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 md:gap-8">

        {/* LEFT COLUMN */}
        <div className="lg:col-span-5 space-y-4 md:space-y-6">

          {/* Monthly Budget Bar */}
          <div
            className={cn(
              "p-5 rounded-[1.5rem] border",
              theme === "dark" ? "bg-white/[0.03] border-white/10" : "bg-white border-slate-100",
            )}
            role="region"
            aria-label="Monthly budget tracker"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Zap className="w-3.5 h-3.5 text-blue-500 fill-blue-500" aria-hidden="true" />
                <span className="text-[10px] font-black uppercase tracking-[0.3em] text-blue-500">
                  Monthly Spend
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn("text-sm font-black", theme === "dark" ? "text-white" : "text-slate-900")}>
                  {formatIndianCompact(metrics.expense)}
                </span>
                {hasBudget && (
                  <span className="text-xs opacity-40 font-bold">
                    / {formatIndianCompact(budget)}
                  </span>
                )}
                <span className={cn(
                  "px-2 py-0.5 rounded-lg text-[9px] font-black uppercase tracking-wider border",
                  !hasBudget
                    ? "bg-blue-500/10 border-blue-500/20 text-blue-500"
                    : percentage >= 100
                      ? "bg-rose-500/10 border-rose-500/20 text-rose-500"
                      : "bg-emerald-500/10 border-emerald-500/20 text-emerald-500",
                )}>
                  {!hasBudget ? "No Limit" : percentage >= 100 ? "Over" : "On Track"}
                </span>
              </div>
            </div>
            <div
              className="relative h-2.5 w-full bg-blue-500/5 rounded-full"
              role="progressbar"
              aria-valuenow={Math.round(cappedPercentage)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Budget usage: ${Math.round(percentage)}%`}
            >
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${cappedPercentage}%` }}
                transition={{ duration: 1.2, ease: "circOut" }}
                className={cn(
                  "h-full rounded-full shadow-lg",
                  budget > 0 && percentage >= 100 ? "bg-rose-500" : "bg-blue-600",
                )}
              />
            </div>
            {budget > 0 && percentage >= 80 && (
              <div className={cn(
                "mt-3 flex items-center gap-2 p-3 rounded-xl border text-xs font-bold",
                percentage >= 100
                  ? "bg-rose-500/10 border-rose-500/20 text-rose-400"
                  : "bg-amber-500/10 border-amber-500/20 text-amber-400",
              )} role="alert">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                {percentage >= 100
                  ? `Over budget by ${formatIndianCompact(metrics.expense - budget)}`
                  : `${Math.round(percentage)}% used — ${formatIndianCompact(budget - metrics.expense)} left`}
              </div>
            )}
            {parseFloat(settings?.dailyBudget) > 0 && (
              <div className={cn(
                "mt-2 flex items-center gap-2 p-3 rounded-xl border text-xs font-bold",
                metrics.todayExpense > parseFloat(settings.dailyBudget)
                  ? "bg-rose-500/10 border-rose-500/20 text-rose-400"
                  : "bg-white/5 border-white/5 text-slate-500",
              )}>
                <TrendingDown className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                Today: {formatIndianCompact(metrics.todayExpense)} / {formatIndianCompact(parseFloat(settings.dailyBudget))} daily
              </div>
            )}
          </div>

          {/* Tax Tile */}
          <MetricTile
            title="Tax Payable"
            value={metrics.estimatedTax > 0 ? formatIndianCompact(metrics.estimatedTax) : "Tax Free"}
            subtitle={taxData ? `${metrics.recommendedRegime === "new" ? "New" : "Old"} Regime · FY ${fiscalYear}` : `FY ${fiscalYear}`}
            icon={Scale}
            colorClass="bg-rose-500/10 text-rose-500"
            tab={TABS.ITR}
          />

          {/* 2×2 grid */}
          <div className="grid grid-cols-2 gap-3 sm:gap-4">
            <MetricTile
              title="Taxable Income"
              value={formatIndianCompact(metrics.totalTaxable)}
              icon={FileText}
              colorClass="bg-blue-500/10 text-blue-500"
              tab={TABS.AUDIT}
            />
            <MetricTile
              title="Net Worth"
              value={formatIndianCompact(metrics.netWorth)}
              subtitle={
                netWorthChange
                  ? `${netWorthChange.isUp ? "+" : ""}${netWorthChange.pct}% vs last month`
                  : wealthItems.length === 0 ? "Add assets to track" : null
              }
              icon={Coins}
              colorClass="bg-emerald-500/10 text-emerald-500"
              tab={TABS.WEALTH}
            />
            <MetricTile
              title="Bank Cards"
              value={metrics.cardCount > 0 ? `${metrics.cardCount} Linked` : "Manage"}
              icon={Landmark}
              colorClass="bg-blue-500/10 text-blue-500"
              tab={TABS.BANK_ACCOUNTS}
            />
            <MetricTile
              title="Entries"
              value={metrics.count.toLocaleString("en-IN")}
              icon={History}
              colorClass="bg-amber-500/10 text-amber-500"
              tab={TABS.HISTORY}
            />
          </div>
        </div>

        {/* RIGHT COLUMN — Recent History */}
        <div className="lg:col-span-7">
          <div className="flex justify-between items-center mb-4 md:mb-6 px-2 sm:px-4">
            <h3 className={cn(
              "font-black text-xl sm:text-2xl tracking-tighter",
              theme === "dark" ? "text-white" : "text-indigo-950",
            )}>
              Recent History
            </h3>
            <motion.button
              whileHover={{ x: 5 }}
              transition={bouncySpring}
              onClick={() => setActiveTab(TABS.HISTORY)}
              aria-label="View full transaction history"
              className="text-[11px] font-black uppercase tracking-[0.2em] flex items-center gap-2 opacity-50 hover:opacity-100 whitespace-nowrap"
            >
              <span className="hidden sm:inline">Full History</span>
              <span className="sm:hidden">All</span>
              <ArrowRightLeft className="w-4 h-4" aria-hidden="true" />
            </motion.button>
          </div>
          <motion.div
            className={cn(
              "p-3 sm:p-6 rounded-[2rem] md:rounded-[3rem] lg:rounded-[3.5rem] border shadow-2xl transition-all",
              theme === "dark"
                ? "bg-white/[0.02] border-white/5 backdrop-blur-md"
                : "bg-white/80 border-white/50 backdrop-blur-xl",
            )}
            role="region"
            aria-label="Recent transactions"
          >
            {txList.length === 0 ? (
              <div className="text-center py-24">
                <Inbox className={cn("w-16 h-16 mx-auto mb-4 stroke-[1px]", theme === "dark" ? "text-white/10" : "text-slate-200")} aria-hidden="true" />
                <p className={cn("text-sm font-bold mb-1", theme === "dark" ? "text-white/30" : "text-slate-400")}>
                  No transactions yet
                </p>
                <p className={cn("text-xs", theme === "dark" ? "text-white/15" : "text-slate-300")}>
                  Add your first transaction or upload a bank statement
                </p>
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setActiveTab(TABS.ADD)}
                  className="mt-4 px-6 py-2 text-xs font-bold uppercase tracking-widest bg-blue-600 text-white rounded-full hover:bg-blue-500 transition-colors"
                >
                  Add Entry
                </motion.button>
              </div>
            ) : (
              <div className="space-y-3">
                {txList.slice(0, 6).map((t, idx) => (
                  <motion.div
                    key={t.uid || t.id || idx}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    whileHover={{ scale: 1.02 }}
                    transition={{ delay: idx * 0.05, ...bouncySpring }}
                  >
                    <TransactionItem item={t} onDelete={onDelete} />
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
