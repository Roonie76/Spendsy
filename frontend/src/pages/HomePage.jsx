import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
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
  Inbox,
  ChevronLeft,
  ChevronRight,
  Calendar,
} from "lucide-react";
import TransactionItem from "../components/domain/TransactionItem";
import { TABS } from "@shared/config/constants";
import { normalizeDate, formatIndianCompact, getCurrentFinancialYear } from "@shared/utils/helpers";
import { TaxService } from "@shared/services/taxService";
import { cn } from "@shared/utils/cn";

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
  const [selectedDate, setSelectedDate] = useState(new Date());

  const handlePrevMonth = () => {
    setSelectedDate(prev => new Date(prev.getFullYear(), prev.getMonth() - 1, 1));
  };

  const handleNextMonth = () => {
    setSelectedDate(prev => new Date(prev.getFullYear(), prev.getMonth() + 1, 1));
  };

  const isCurrentMonth = useMemo(() => {
    const now = new Date();
    return selectedDate.getMonth() === now.getMonth() && selectedDate.getFullYear() === now.getFullYear();
  }, [selectedDate]);
  // --- Dynamic fiscal year (never hardcoded) ---
  const fiscalYear = useMemo(() => getCurrentFinancialYear(), []);

  // --- Tax calculation via shared TaxService (supports all regimes, surcharge, cess) ---
  const taxData = useMemo(() => {
    if (!transactions || transactions.length === 0) return null;
    try {
      return TaxService.calculate(transactions, taxProfile, wealthItems, settings);
    } catch {
      return null;
    }
  }, [transactions, taxProfile, wealthItems, settings]);

  // --- Net worth change vs last month (calculated, not hardcoded) ---
  const netWorthChange = useMemo(() => {
    if (!netWorthHistory || netWorthHistory.length < 2) return null;
    const sorted = [...netWorthHistory].sort((a, b) => new Date(a.date) - new Date(b.date));
    const current = parseFloat(sorted[sorted.length - 1]?.net_worth || 0);
    const previous = parseFloat(sorted[sorted.length - 2]?.net_worth || 0);
    if (previous === 0) return null;
    const pct = ((current - previous) / Math.abs(previous)) * 100;
    return { pct: Math.round(pct * 10) / 10, isUp: pct >= 0 };
  }, [netWorthHistory]);

  const metrics = useMemo(() => {
    const txList = Array.isArray(transactions) ? transactions : [];
    const now = new Date();
    const currentMonth = selectedDate.getMonth();
    const currentYear = selectedDate.getFullYear();

    // Monthly Expense Calculation (fallback if totals.monthExpense is missing)
    const monthlyData = txList.filter((t) => {
      const d = normalizeDate(t.date);
      if (!d) return false;
      return d.getMonth() === currentMonth && d.getFullYear() === currentYear;
    });

    const localMonthExpense = monthlyData
      .filter((t) => t.type === "expense")
      .reduce((acc, t) => acc + (parseFloat(t.amount) || 0), 0);

    const expense = isCurrentMonth && totals?.monthExpense !== undefined 
      ? totals.monthExpense 
      : localMonthExpense;

    // Net Worth Calculation
    const wealthList = Array.isArray(wealthItems) ? wealthItems : [];
    const netWorth = wealthList.reduce((acc, curr) => {
      const amt = parseFloat(curr.amount || curr.value || 0);
      if (curr.type === "asset") return acc + amt;
      if (curr.type === "liability") return acc - amt;
      return acc;
    }, 0);

    // Use TaxService results (dynamic FY, proper slabs, surcharge, cess, rebate)
    const estimatedTax = taxData
      ? Math.round(Math.min(taxData.totalTaxNew, taxData.totalTaxOld))
      : 0;
    const taxableIncome = taxData
      ? Math.round(Math.min(taxData.taxableNew, taxData.taxableOld))
      : 0;
    const recommendedRegime = taxData?.recommendedRegime || "new";

    // Daily spend (today only)
    const todayStr = now.toISOString().slice(0, 10);
    const todayExpense = monthlyData
      .filter((t) => {
        if (t.type !== "expense") return false;
        const d = normalizeDate(t.date);
        return d && d.toISOString().slice(0, 10) === todayStr;
      })
      .reduce((acc, t) => acc + (parseFloat(t.amount) || 0), 0);

    // Card count from wealthItems (loans/liabilities that represent cards)
    const cardCount = wealthList.filter(
      (i) => String(i?.name || "").toLowerCase().match(/card|visa|mastercard|rupay/)
    ).length;

    return {
      expense,
      todayExpense,
      netWorth,
      totalTaxable: taxableIncome,
      estimatedTax,
      recommendedRegime,
      count: txList.length,
      cardCount,
    };
  }, [transactions, wealthItems, totals, taxData]);

  const budget = parseFloat(settings?.monthlyBudget) || 0;
  const hasBudget = settings?.monthlyBudget !== undefined && settings?.monthlyBudget !== null && settings?.monthlyBudget !== "";
  const percentage = budget > 0 ? (metrics.expense / budget) * 100 : 0;
  const cappedPercentage = Math.min(100, percentage);

  const bouncySpring = { type: "spring", stiffness: 500, damping: 20, mass: 1 };

  // --- Loading skeleton for shimmer effect ---
  if (isLoading) {
    return (
      <div className="space-y-6 md:space-y-10 animate-pulse" role="status" aria-label="Loading dashboard">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 md:gap-8">
          <div className="lg:col-span-5 space-y-4 md:space-y-6">
            <div className={cn("h-64 rounded-[2rem] sm:rounded-[3rem]", theme === "dark" ? "bg-white/5" : "bg-slate-100")} />
            <div className={cn("h-32 rounded-[2rem]", theme === "dark" ? "bg-white/5" : "bg-slate-100")} />
            <div className="grid grid-cols-2 gap-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className={cn("h-28 rounded-[1.5rem]", theme === "dark" ? "bg-white/5" : "bg-slate-100")} />
              ))}
            </div>
          </div>
          <div className="lg:col-span-7">
            <div className={cn("h-8 w-48 rounded-lg mb-6", theme === "dark" ? "bg-white/5" : "bg-slate-100")} />
            <div className={cn("h-96 rounded-[2rem]", theme === "dark" ? "bg-white/5" : "bg-slate-100")} />
          </div>
        </div>
        <span className="sr-only">Loading dashboard data...</span>
      </div>
    );
  }

  // --- Error state ---
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

  const MetricTile = ({
    title,
    value,
    icon: Icon,
    colorClass,
    tab,
    isSpecial = false,
    subtitle,
  }) => (
    <div className="relative group">
      <div
        className={cn(
          "pointer-events-none absolute -inset-3 rounded-[3rem] opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-2xl",
          isSpecial
            ? "bg-blue-500/40"
            : colorClass?.includes("blue")
              ? "bg-blue-500/30"
              : colorClass?.includes("emerald")
                ? "bg-emerald-500/30"
                : colorClass?.includes("purple")
                  ? "bg-purple-500/30"
                  : "bg-white/20",
        )}
      />

      <motion.button
        whileHover={{ scale: 1.05, y: -10 }}
        whileTap={{ scale: 0.95 }}
        transition={bouncySpring}
        onClick={() => setActiveTab(tab)}
        aria-label={`${title}: ${value}. Click to view details.`}
        className={cn(
          "relative overflow-hidden p-4 sm:p-6 rounded-[1.5rem] sm:rounded-[2rem] md:rounded-[2.5rem] border text-left w-full transition-shadow duration-300",
          isSpecial
            ? "bg-blue-600 border-blue-400 shadow-blue-500/40"
            : theme === "dark"
              ? "bg-white/10 border-white/10 backdrop-blur-md shadow-2xl"
              : "bg-white border-white shadow-xl shadow-blue-500/10",
        )}
      >
        <div
          className={cn(
            "mb-4 p-3 rounded-2xl inline-flex",
            isSpecial ? "bg-white/20 text-white" : colorClass,
          )}
          aria-hidden="true"
        >
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p
            className={cn(
              "text-[10px] font-black uppercase tracking-[0.2em] mb-1",
              isSpecial
                ? "text-blue-100"
                : theme === "dark"
                  ? "text-blue-400/60"
                  : "text-blue-600",
            )}
          >
            {title}
          </p>
          <p
            className={cn(
              "text-xl sm:text-2xl font-black tracking-tighter break-all",
              isSpecial
                ? "text-white"
                : theme === "dark"
                  ? "text-white"
                  : "text-indigo-950",
            )}
          >
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

  return (
    <div className="space-y-6 md:space-y-10 pb-28" role="main" aria-label="Financial dashboard">
      {/* Month Selector UI */}
      <div className="flex items-center justify-between bg-white/5 border border-white/10 p-4 rounded-[2rem] backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-blue-500/10 rounded-xl">
            <Calendar className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Selected Period</p>
            <h3 className="text-lg font-black text-white">
              {selectedDate.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}
            </h3>
          </div>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={handlePrevMonth}
            className="p-2 bg-white/5 hover:bg-white/10 rounded-full text-slate-400 hover:text-white transition-colors"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          {!isCurrentMonth && (
            <button 
              onClick={() => setSelectedDate(new Date())}
              className="px-3 py-1 bg-white/5 hover:bg-white/10 rounded-lg text-[10px] font-bold text-slate-400 hover:text-white transition-colors"
            >
              Today
            </button>
          )}
          <button 
            onClick={handleNextMonth}
            className="p-2 bg-white/5 hover:bg-white/10 rounded-full text-slate-400 hover:text-white transition-colors"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 md:gap-8">
        {/* LEFT COLUMN */}
        <div className="lg:col-span-5 space-y-4 md:space-y-6">
          {/* Monthly Spend */}
          <motion.div
            whileHover={{ y: -5 }}
            transition={bouncySpring}
            className={cn(
              "relative overflow-hidden p-6 sm:p-8 rounded-[2rem] sm:rounded-[3rem] md:rounded-[3.5rem] border shadow-2xl",
              theme === "dark"
                ? "bg-white/[0.03] border-white/10 backdrop-blur-3xl"
                : "bg-white border-white",
            )}
            role="region"
            aria-label="Monthly spending summary"
          >
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3 mb-6 md:mb-8">
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="w-3.5 h-3.5 text-blue-500 fill-blue-500" aria-hidden="true" />
                  <span className="text-[10px] font-black uppercase tracking-[0.4em] text-blue-500">
                    Monthly Spend
                  </span>
                </div>
                <h3
                  className={cn(
                    "text-3xl sm:text-4xl md:text-5xl font-black tracking-tighter break-all",
                    theme === "dark" ? "text-white" : "text-indigo-950",
                  )}
                >
                  ₹{metrics.expense.toLocaleString("en-IN")}
                </h3>
                <p className="text-xs font-bold opacity-40 mt-1">
                  {hasBudget
                    ? `Monthly Budget: ${formatIndianCompact(budget)}`
                    : "No budget set"}
                </p>
              </div>
              <div
                className={cn(
                  "self-start px-3 py-1.5 sm:px-4 sm:py-2 rounded-2xl text-[10px] font-black uppercase tracking-widest border whitespace-nowrap",
                  !hasBudget
                    ? "bg-blue-500/10 border-blue-500/20 text-blue-500"
                    : percentage >= 100
                      ? "bg-rose-500/10 border-rose-500/20 text-rose-500"
                      : "bg-emerald-500/10 border-emerald-500/20 text-emerald-500",
                )}
              >
                {!hasBudget
                  ? "No Limit Set"
                  : percentage >= 100
                    ? "Limit Reached"
                    : "On Track"}
              </div>
            </div>
            <div
              className="relative h-4 w-full bg-blue-500/5 rounded-full p-1"
              role="progressbar"
              aria-valuenow={Math.round(cappedPercentage)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Budget usage: ${Math.round(percentage)}%`}
            >
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${cappedPercentage}%` }}
                transition={{ duration: 1.5, ease: "circOut" }}
                className={cn(
                  "h-full rounded-full shadow-lg",
                  budget > 0 && percentage >= 100 ? "bg-rose-500" : "bg-blue-600",
                )}
              />
            </div>

            {/* Budget Alerts */}
            {budget > 0 && percentage >= 80 && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                role="alert"
                className={cn(
                  "mt-5 flex items-center gap-3 p-4 rounded-2xl border",
                  percentage >= 100
                    ? "bg-rose-500/10 border-rose-500/20"
                    : "bg-amber-500/10 border-amber-500/20",
                )}
              >
                <AlertTriangle className={cn("w-4 h-4 shrink-0", percentage >= 100 ? "text-rose-400" : "text-amber-400")} aria-hidden="true" />
                <p className={cn("text-xs font-bold", percentage >= 100 ? "text-rose-400" : "text-amber-400")}>
                  {percentage >= 100
                    ? `Over budget by ${formatIndianCompact(metrics.expense - budget)}`
                    : `${Math.round(percentage)}% of monthly budget used — ${formatIndianCompact(budget - metrics.expense)} remaining`}
                </p>
              </motion.div>
            )}

            {/* Daily Budget Tracker */}
            {parseFloat(settings?.dailyBudget) > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  "mt-3 flex items-center gap-3 p-4 rounded-2xl border",
                  metrics.todayExpense > parseFloat(settings.dailyBudget)
                    ? "bg-rose-500/10 border-rose-500/20"
                    : "bg-white/5 border-white/5",
                )}
              >
                <TrendingDown className={cn("w-4 h-4 shrink-0", metrics.todayExpense > parseFloat(settings.dailyBudget) ? "text-rose-400" : "text-slate-500")} aria-hidden="true" />
                <p className={cn("text-xs font-bold", metrics.todayExpense > parseFloat(settings.dailyBudget) ? "text-rose-400" : "text-slate-500")}>
                  Today: {formatIndianCompact(metrics.todayExpense)} / {formatIndianCompact(parseFloat(settings.dailyBudget))} daily limit
                </p>
              </motion.div>
            )}
          </motion.div>

          {/* ITR Tile — uses TaxService, shows regime */}
          <MetricTile
            title="Tax Payable"
            value={
              metrics.estimatedTax > 0
                ? formatIndianCompact(metrics.estimatedTax)
                : "₹0 (Tax Free)"
            }
            subtitle={taxData ? `${metrics.recommendedRegime === "new" ? "New" : "Old"} Regime · FY ${fiscalYear}` : `FY ${fiscalYear}`}
            icon={Scale}
            colorClass="bg-rose-500/10 text-rose-500"
            tab={TABS.ITR}
          />

          {/* Bottom Grid */}
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
                  : wealthItems.length === 0
                    ? "Add assets to track"
                    : null
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

        {/* RIGHT COLUMN */}
        <div className="lg:col-span-7">
          <div className="flex justify-between items-center mb-4 md:mb-6 px-2 sm:px-4">
            <h3
              className={cn(
                "font-black text-xl sm:text-2xl tracking-tighter",
                theme === "dark" ? "text-white" : "text-indigo-950",
              )}
            >
              Recent History
            </h3>
            <motion.button
              whileHover={{ x: 5, color: "#030303" }}
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
