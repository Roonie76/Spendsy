//Database needed
// Section 1 Home Page
import React, { useMemo } from "react";
import { motion } from "framer-motion";
import {
  CreditCard,
  Zap,
  FileText,
  PieChart,
  Coins,
  History,
  Scale,
  ArrowRightLeft,
  Landmark,
} from "lucide-react";
import TransactionItem from "../components/domain/TransactionItem";
import { TABS } from "../../../../../packages/shared/config/constants";
import { normalizeDate, formatIndianCompact } from "../../../../../packages/shared/utils/helpers";
import { cn } from "../../../../../packages/shared/utils/cn";

const HomePage = ({
  transactions,
  wealthItems = [], // If this is empty, Net Worth will be 0
  setActiveTab,
  onDelete,
  settings,
  theme = "dark",
}) => {
  // Debugging: Check your console to see if data is actually arriving
  // If this logs "HomePage wealthItems: []", then the parent is not passing data.
  // console.log("HomePage wealthItems:", wealthItems);

const metrics = useMemo(() => {
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();

    // Fiscal Year Logic
    const fyStartYear = currentMonth < 3 ? currentYear - 1 : currentYear;
    const fyStartDate = new Date(fyStartYear, 3, 1);

    // Monthly Expense Calculation
    const monthlyData = transactions.filter((t) => {
      const d = normalizeDate(t.date);
      return d.getMonth() === currentMonth && d.getFullYear() === currentYear;
    });

    const expense = monthlyData
      .filter((t) => t.type === "expense")
      .reduce((acc, t) => acc + (parseFloat(t.amount) || 0), 0);

    // Net Worth Calculation
    const netWorth = wealthItems.reduce((acc, curr) => {
      const amt = parseFloat(curr.amount || curr.value || 0);
      if (curr.type === "asset") return acc + amt;
      if (curr.type === "liability") return acc - amt;
      return acc;
    }, 0);

    // 1. Calculate Total Gross Income
    const totalGrossIncome = transactions
      .filter((t) => {
        const d = normalizeDate(t.date);
        return t.type === "income" && d >= fyStartDate;
      })
      .reduce((acc, t) => acc + (parseFloat(t.amount) || 0), 0);

    // 2. APPLY NEW REGIME DEDUCTION (₹75,000)
    // This makes the "Taxable" tile show 7.25L if income is 8L
    const taxableIncomeValue = Math.max(0, totalGrossIncome - 75000);

    // 3. CALCULATE ESTIMATED TAX (FY 2025-26 New Regime)
    let estimatedTax = 0;
    
    // Rebate Logic: No tax if taxable income <= 12,00,000
    if (taxableIncomeValue > 1200000) {
      let tempIncome = taxableIncomeValue;
      let taxBase = 0;

      // New Slab Math
      if (tempIncome > 400000) taxBase += Math.min(tempIncome - 400000, 400000) * 0.05; // 4-8L
      if (tempIncome > 800000) taxBase += Math.min(tempIncome - 800000, 400000) * 0.10; // 8-12L
      if (tempIncome > 1200000) taxBase += Math.min(tempIncome - 1200000, 400000) * 0.15; // 12-16L
      // ... higher slabs as needed ...

      estimatedTax = taxBase * 1.04; // Add 4% Cess
    }

    return {
      expense,
      netWorth,
      totalTaxable: taxableIncomeValue, // This is now matched to Audit Page
      estimatedTax,
      count: transactions.length,
    };
  }, [transactions, wealthItems]);

  const budget = parseFloat(settings?.monthlyBudget) || 0;
  const percentage =
    budget > 0 ? Math.min(100, (metrics.expense / budget) * 100) : 0;

const bouncySpring = { type: "spring", stiffness: 500, damping: 20, mass: 1 };

const MetricTile = ({
  title,
  value,
  icon: Icon,
  colorClass,
  tab,
  isSpecial = false,
  setActiveTab,
  theme
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
      className={cn(
        "relative overflow-hidden p-6 rounded-[2.5rem] border text-left w-full transition-shadow duration-300",
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
            "text-2xl font-black tracking-tighter",
            isSpecial
              ? "text-white"
              : theme === "dark"
                ? "text-white"
                : "text-indigo-950",
          )}
        >
          {value}
        </p>
      </div>
    </motion.button>
  </div>
);

  return (
    <div className="space-y-10">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* LEFT COLUMN */}
        <div className="lg:col-span-5 space-y-6">
          {/* Monthly Spend */}
          <motion.div
            whileHover={{ y: -5 }}
            transition={bouncySpring}
            className={cn(
              "relative overflow-hidden p-8 rounded-[3.5rem] border shadow-2xl",
              theme === "dark"
                ? "bg-white/[0.03] border-white/10 backdrop-blur-3xl"
                : "bg-white border-white",
            )}
          >
            <div className="flex justify-between items-start mb-8">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="w-3.5 h-3.5 text-blue-500 fill-blue-500" />
                  <span className="text-[10px] font-black uppercase tracking-[0.4em] text-blue-500">
                    Monthly Spend
                  </span>
                </div>
                <h3
                  className={cn(
                    "text-5xl font-black tracking-tighter",
                    theme === "dark" ? "text-white" : "text-indigo-950",
                  )}
                >
                  ₹{metrics.expense.toLocaleString("en-IN")}
                </h3>
                <p className="text-xs font-bold opacity-40 mt-1">
                  Monthly Budget: {formatIndianCompact(budget)}
                </p>
              </div>
              <div
                className={cn(
                  "px-4 py-2 rounded-2xl text-[10px] font-black uppercase tracking-widest border",
                  percentage >= 100
                    ? "bg-rose-500/10 border-rose-500/20 text-rose-500"
                    : "bg-emerald-500/10 border-emerald-500/20 text-emerald-500",
                )}
              >
                {percentage >= 100 ? "Limit Reached" : "On Track"}
              </div>
            </div>
            <div className="relative h-4 w-full bg-blue-500/5 rounded-full p-1">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${percentage}%` }}
                transition={{ duration: 1.5, ease: "circOut" }}
                className={cn(
                  "h-full rounded-full shadow-lg",
                  percentage >= 100 ? "bg-rose-500" : "bg-blue-600",
                )}
              />
            </div>
          </motion.div>

          {/* ITR Tile */}
          <MetricTile
            title="Tax Payable"
            value={
              metrics.estimatedTax > 0
                ? `${formatIndianCompact(metrics.estimatedTax)}`
                : "₹0 (Tax Free)"
            }
            icon={Scale}
            colorClass="bg-rose-500/10 text-rose-500"
            tab={TABS.ITR}
            theme={theme}
          />

          {/* Bottom Grid */}
          <div className="grid grid-cols-2 gap-4">
            <MetricTile
              title="Taxable Income"
              // Corrected: formatIndianCompact adds symbol, so we don't add "₹"
              value={formatIndianCompact(metrics.totalTaxable)}
              icon={FileText}
              colorClass="bg-blue-500/10 text-blue-500"
              tab={TABS.AUDIT}
              theme={theme}
            />
            <MetricTile
              title="Net Worth"
              // Corrected: formatIndianCompact adds symbol, so we don't add "₹"
              value={formatIndianCompact(metrics.netWorth)}
              icon={Coins}
              colorClass="bg-emerald-500/10 text-emerald-500"
              tab={TABS.WEALTH}
              theme={theme}
            />
            <MetricTile
              title="Bank Cards"
              value="Manage"
              icon={Landmark}
              colorClass="bg-blue-500/10 text-blue-500"
              tab={TABS.BANK_ACCOUNTS}
              theme={theme}
            />
            <MetricTile
              title="Entries"
              value={metrics.count}
              icon={History}
              colorClass="bg-amber-500/10 text-amber-500"
              tab={TABS.HISTORY}
              theme={theme}
            />
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="lg:col-span-7">
          <div className="flex justify-between items-center mb-6 px-4">
            <h3
              className={cn(
                "font-black text-2xl tracking-tighter",
                theme === "dark" ? "text-white" : "text-indigo-950",
              )}
            >
              Recent History
            </h3>
            <motion.button
              whileHover={{ x: 5, color: "#030303" }}
              transition={bouncySpring}
              onClick={() => setActiveTab(TABS.HISTORY)}
              className="text-[11px] font-black uppercase tracking-[0.2em] flex items-center gap-2 opacity-50 hover:opacity-100"
            >
              Full History <ArrowRightLeft className="w-4 h-4" />
            </motion.button>
          </div>
          <motion.div
            className={cn(
              "p-6 rounded-[3.5rem] border shadow-2xl transition-all",
              theme === "dark"
                ? "bg-white/[0.02] border-white/5 backdrop-blur-md"
                : "bg-white/80 border-white/50 backdrop-blur-xl",
            )}
          >
            {transactions.length === 0 ? (
              <div className="text-center py-24 opacity-10">
                <CreditCard className="w-20 h-20 mx-auto mb-4 stroke-[1px]" />
                <p className="text-xs font-black uppercase tracking-widest">
                  No Records Found
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {transactions.slice(0, 6).map((t, idx) => (
                  <motion.div
                    key={t.id}
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
