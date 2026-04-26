import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { 
  Target, 
  IndianRupee, 
  Loader2, 
  TrendingUp, 
  Briefcase, 
  Sparkles, 
  ChevronRight,
  ChevronLeft
} from "lucide-react";

import { formatIndianCompact, normalizeDate } from "@shared/utils/helpers";

const BudgetPage = ({ settings, onUpdateSettings, triggerConfirm, onBack, transactions = [] }) => {
  const categories = [
    "Food", "Travel", "Rent", "Shopping", "Entertainment", "Health", "Investment", "Others"
  ];

  const [localSettings, setLocalSettings] = useState(settings || {});
  const [savingSettings, setSavingSettings] = useState(false);

  useEffect(() => {
    if (settings) {
      setLocalSettings(settings);
    }
  }, [settings]);

  const getReadableUnit = (value) => {
    const val = parseFloat(value);
    if (!val || isNaN(val)) return "0";
    if (val >= 10000000) return `${(val / 10000000).toFixed(2)} Cr`;
    if (val >= 100000) return `${(val / 100000).toFixed(2)} L`;
    if (val >= 1000) return `${(val / 1000).toFixed(1)} K`;
    return val.toLocaleString("en-IN");
  };

  const requestSaveSettings = (e) => {
    e.preventDefault();
    triggerConfirm("Save your financial goals?", async () => {
      setSavingSettings(true);
      const updatedData = {
        monthlyIncome: Number(localSettings.monthlyIncome) || 0,
        monthlyBudget: Number(localSettings.monthlyBudget) || 0,
        dailyBudget: Number(localSettings.dailyBudget) || 0,
        categoryBudgets: localSettings.categoryBudgets || {},
      };
      await onUpdateSettings(updatedData);
      setSavingSettings(false);
    });
  };

  const actualSpending = React.useMemo(() => {
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();

    return transactions.reduce((acc, t) => {
      const d = normalizeDate(t.date);
      if (d && d.getMonth() === currentMonth && d.getFullYear() === currentYear && t.type === "expense") {
        const cat = t.category || "Others";
        acc[cat] = (acc[cat] || 0) + parseFloat(t.amount || 0);
      }
      return acc;
    }, {});
  }, [transactions]);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-8 pb-32"
    >
       <div className="flex items-center gap-4 pb-4 border-b border-white/5">
          <motion.button 
            whileHover={{ scale: 1.05, x: -2 }}
            whileTap={{ scale: 0.95 }}
            onClick={onBack}
            className="p-3 bg-white/5 rounded-2xl hover:bg-white/10 transition-colors shadow-lg"
          >
            <ChevronLeft className="w-5 h-5 text-white" />
          </motion.button>
          <div>
            <h1 className="text-2xl font-black text-white tracking-tight">Financial Goals</h1>
            <p className="text-slate-400 text-[10px] font-black uppercase tracking-widest mt-1">Configure your monthly limits</p>
          </div>
      </div>

       <form
          onSubmit={requestSaveSettings}
          className="bg-black/20 p-5 sm:p-8 rounded-[2rem] sm:rounded-[3rem] border border-white/10 space-y-6 sm:space-y-8 relative overflow-hidden"
        >
          <div className="absolute -inset-px bg-gradient-to-b from-white/10 to-transparent pointer-events-none"></div>

          <div className="grid grid-cols-1 gap-5 sm:gap-8 relative z-10">
            {[
              { id: "monthlyIncome", label: "Monthly Income", icon: TrendingUp, color: "text-emerald-400", glow: "group-focus-within:shadow-[0_0_20px_-5px_rgba(52,211,153,0.3)]" },
              { id: "monthlyBudget", label: "Monthly Budget", icon: Briefcase, color: "text-violet-400", glow: "group-focus-within:shadow-[0_0_20px_-5px_rgba(167,139,250,0.3)]" },
              { id: "dailyBudget", label: "Daily Budget", icon: Sparkles, color: "text-amber-400", glow: "group-focus-within:shadow-[0_0_20px_-5px_rgba(251,191,36,0.3)]" }
            ].map((field) => (
              <div key={field.id} className="space-y-4">
                <label className="text-[11px] text-slate-500 font-black uppercase tracking-[0.4em] flex items-center gap-2.5 ml-2">
                  <field.icon className={`w-3.5 h-3.5 ${field.color}`} />
                  {field.label}
                </label>
                <div className={`relative group transition-all duration-300 rounded-[2rem] sm:rounded-[2.5rem] ${field.glow}`}>
                  <div className="absolute left-4 sm:left-7 top-1/2 -translate-y-1/2 text-slate-600 group-focus-within:text-white transition-colors z-20">
                    <IndianRupee className="w-5 h-5 sm:w-6 sm:h-6" />
                  </div>
                  <input
                    type="number"
                    value={localSettings[field.id] || ""}
                    onChange={(e) =>
                      setLocalSettings({ ...localSettings, [field.id]: e.target.value })
                    }
                    className="w-full pl-11 sm:pl-16 pr-4 sm:pr-36 py-4 sm:py-6 bg-black/40 border-2 border-white/5 rounded-[2rem] sm:rounded-[2.5rem] text-lg sm:text-2xl font-black text-white outline-none focus:border-white/20 focus:bg-white/5 transition-all placeholder:text-slate-800 shadow-inner relative z-10"
                    placeholder="0"
                  />
                  {localSettings[field.id] > 0 && (
                    <div className="hidden sm:block absolute right-6 top-1/2 -translate-y-1/2 px-5 py-2.5 bg-white/10 rounded-2xl border border-white/10 backdrop-blur-xl z-20 shadow-lg">
                      <span className={`text-xs font-black ${field.color}`}>
                        {getReadableUnit(localSettings[field.id])}
                      </span>
                    </div>
                  )}
                  {localSettings[field.id] > 0 && (
                    <div className="sm:hidden mt-2 ml-11">
                      <span className={`text-[10px] font-black ${field.color}`}>
                        {getReadableUnit(localSettings[field.id])}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            type="submit"
            disabled={savingSettings}
            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white py-5 rounded-[2rem] font-black text-lg shadow-2xl shadow-indigo-900/40 transition-all disabled:opacity-50 flex items-center justify-center gap-3 mt-4 relative z-10"
          >
            {savingSettings ? (
              <>
                <Loader2 className="w-6 h-6 animate-spin" />
                <span className="animate-pulse">Syncing with Cloud...</span>
              </>
            ) : (
              <>
                <span>Update Budget Configuration</span>
                <ChevronRight className="w-6 h-6" />
              </>
            )}
          </motion.button>
        </form>

        {/* Category-Level Breakdown */}
        <div className="mt-12 space-y-8">
          <div className="flex justify-between items-end px-2">
            <div>
              <h2 className="text-xl font-black text-white tracking-tight">Category Breakdown</h2>
              <p className="text-slate-400 text-[10px] font-black uppercase tracking-widest mt-1">Allocate your budget by sector</p>
            </div>
            <div className="text-right">
              <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Allocated</p>
              <p className="text-lg font-black text-white">
                {formatIndianCompact(Object.values(localSettings.categoryBudgets || {}).reduce((a, b) => a + Number(b), 0))} / {formatIndianCompact(localSettings.monthlyBudget)}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {categories.map((cat) => {
              const budgetVal = Number((localSettings.categoryBudgets || {})[cat] || 0);
              const actualVal = actualSpending[cat] || 0;
              const pct = budgetVal > 0 ? (actualVal / budgetVal) * 100 : 0;
              const cappedPct = Math.min(100, pct);

              return (
                <div key={cat} className="bg-white/5 border border-white/10 p-6 rounded-[2rem] space-y-4 hover:bg-white/10 transition-colors group/cat">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-black text-white uppercase tracking-wider">{cat}</span>
                    <div className="flex items-center gap-2">
                       <span className="text-[10px] text-slate-500 font-bold">Limit:</span>
                       <input 
                         type="number"
                         value={budgetVal || ""}
                         onChange={(e) => {
                           const newBudgets = { ...(localSettings.categoryBudgets || {}), [cat]: e.target.value };
                           setLocalSettings({ ...localSettings, categoryBudgets: newBudgets });
                         }}
                         className="w-20 px-2 py-1 bg-black/40 border border-white/10 rounded-lg text-[10px] font-black text-white outline-none focus:border-indigo-500/50"
                         placeholder="0"
                       />
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between text-[10px] font-black uppercase tracking-widest">
                      <span className={pct >= 100 ? "text-rose-400" : "text-emerald-400"}>
                        Used: {formatIndianCompact(actualVal)}
                      </span>
                      <span className="text-slate-500">
                        Left: {formatIndianCompact(Math.max(0, budgetVal - actualVal))}
                      </span>
                    </div>
                    <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${cappedPct}%` }}
                        className={`h-full rounded-full ${pct >= 100 ? 'bg-rose-500' : pct >= 80 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
    </motion.div>
  );
};

export default BudgetPage;
