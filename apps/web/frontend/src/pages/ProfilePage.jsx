import React, { useState, useEffect } from "react";
import { 
  User, 
  Target, 
  IndianRupee, 
  Loader2, 
  ShieldCheck, 
  CreditCard as CreditCardIcon, 
  Briefcase, 
  TrendingUp,
  LogOut,
  ChevronRight,
  Sparkles
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";

const ProfilePage = ({
  user,
  settings,
  onUpdateSettings,
  onSignOut,
  triggerConfirm,
}) => {
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

  // --- Financial Health Score Calculation ---
  const income = parseFloat(localSettings.monthlyIncome || 0);
  const budget = parseFloat(localSettings.monthlyBudget || 0);
  
  // Simple score heuristic: Budget should be < 70% of income
  let score = 0;
  if (income > 0) {
    const ratio = budget / income;
    if (ratio <= 0.5) score = 95;
    else if (ratio <= 0.7) score = 75;
    else if (ratio <= 0.9) score = 50;
    else score = 30;
  }
  
  const scoreColor = score >= 80 ? "#10b981" : score >= 50 ? "#f59e0b" : "#f43f5e";
  const scoreData = [
    { value: score, color: scoreColor },
    { value: 100 - score, color: "rgba(255,255,255,0.05)" }
  ];

  const requestSaveSettings = (e) => {
    e.preventDefault();
    triggerConfirm("Save your financial goals?", async () => {
      setSavingSettings(true);
      const updatedData = {
        monthlyIncome: Number(localSettings.monthlyIncome) || 0,
        monthlyBudget: Number(localSettings.monthlyBudget) || 0,
        dailyBudget: Number(localSettings.dailyBudget) || 0,
      };
      const dummyUnits = { monthlyIncome: 1, monthlyBudget: 1, dailyBudget: 1 };
      await onUpdateSettings(updatedData, dummyUnits);
      setSavingSettings(false);
    });
  };

  const containerVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { duration: 0.6, staggerChildren: 0.1 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, x: -20 },
    visible: { opacity: 1, x: 0 }
  };

  return (
    <motion.div 
      initial="hidden"
      animate="visible"
      variants={containerVariants}
      className="space-y-8 pb-32"
    >
      {/* Premium Header Card */}
      <div className="relative group">
        <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-[2.5rem] blur opacity-25 group-hover:opacity-40 transition duration-1000 group-hover:duration-200"></div>
        <div className="relative bg-black/40 backdrop-blur-2xl p-6 rounded-[2.5rem] border border-white/10 flex items-center space-x-6 overflow-hidden">
          <div className="absolute top-0 right-0 p-4">
             <Sparkles className="w-5 h-5 text-indigo-400 opacity-50 animate-pulse" />
          </div>
          <div className="relative shrink-0">
            <div className="w-20 h-20 bg-gradient-to-br from-indigo-500/30 to-purple-500/30 rounded-[1.5rem] flex items-center justify-center text-indigo-400 border border-white/10 shadow-inner">
              <User className="w-10 h-10" />
            </div>
            <div className="absolute -bottom-1 -right-1 w-7 h-7 bg-emerald-500 rounded-full border-4 border-slate-900 flex items-center justify-center">
              <ShieldCheck className="w-3.5 h-3.5 text-white" />
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-black text-white text-2xl tracking-tight leading-none mb-1 truncate">
              {user?.username || "Financial Pioneer"}
            </h3>
            <p className="text-sm text-slate-400 font-medium truncate">
              {user?.email || "Connect your digital identity"}
            </p>
            <div className="mt-3 flex gap-2">
               <span className="px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[10px] font-bold text-indigo-400 uppercase tracking-tighter">Pro Member</span>
               <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-bold text-emerald-400 uppercase tracking-tighter">Verified</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Health Score Component */}
        <section className="bg-white/5 backdrop-blur-xl p-6 rounded-[2.5rem] border border-white/10 relative overflow-hidden flex flex-col items-center justify-center">
          <div className="text-center mb-4">
            <h4 className="text-sm font-black text-slate-400 uppercase tracking-[0.2em] mb-1">Health Score</h4>
            <p className="text-[10px] text-slate-500 font-bold">Financial Stability Index</p>
          </div>
          
          <div className="h-48 w-48 relative">
            <ResponsiveContainer width="100%" height="100%" minWidth={0}>
              <PieChart>
                <Pie
                  data={scoreData}
                  cx="50%"
                  cy="50%"
                  innerRadius={65}
                  outerRadius={80}
                  startAngle={90}
                  endAngle={450}
                  paddingAngle={0}
                  dataKey="value"
                  stroke="none"
                >
                  {scoreData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-4xl font-black text-white leading-none">{score}</span>
              <span className="text-[10px] font-black uppercase tracking-widest text-slate-500 mt-1">Perfect</span>
            </div>
          </div>
          
          <div className="mt-4 w-full pt-4 border-t border-white/5 grid grid-cols-2 gap-4">
            <div className="text-center">
              <p className="text-[10px] text-slate-500 font-bold uppercase">Savings Rate</p>
              <p className="text-sm font-black text-emerald-400">{(100 - (budget/income*100)).toFixed(0)}%</p>
            </div>
            <div className="text-center">
              <p className="text-[10px] text-slate-500 font-bold uppercase">Risk Level</p>
              <p className="text-sm font-black text-violet-400">Minimal</p>
            </div>
          </div>
        </section>

        {/* Quick Links / Portfolio Map */}
        <section className="space-y-4">
          {[
            { label: "Credit Cards", icon: CreditCardIcon, count: "2 Linked", color: "text-blue-400", bg: "bg-blue-500/10" },
            { label: "Active Loans", icon: Briefcase, count: "1 Active", color: "text-rose-400", bg: "bg-rose-500/10" },
            { label: "Wealth Portfolio", icon: TrendingUp, count: "3 Assets", color: "text-emerald-400", bg: "bg-emerald-500/10" }
          ].map((item, idx) => (
            <motion.div 
              key={idx}
              variants={itemVariants}
              className="bg-white/5 backdrop-blur-xl p-4 rounded-3xl border border-white/10 flex items-center justify-between group cursor-pointer hover:bg-white/10 transition-all border-l-4"
              style={{ borderLeftColor: idx === 0 ? '#3b82f6' : idx === 1 ? '#f43f5e' : '#10b981' }}
            >
              <div className="flex items-center gap-4">
                <div className={`${item.bg} ${item.color} p-3 rounded-2xl`}>
                  <item.icon className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-sm font-black text-white">{item.label}</p>
                  <p className="text-[10px] font-bold text-slate-500">{item.count}</p>
                </div>
              </div>
              <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-white transition-colors" />
            </motion.div>
          ))}
        </section>
      </div>

      {/* Modern Financial Goals Form */}
      <section className="relative">
        <div className="absolute -inset-px bg-gradient-to-b from-white/10 to-transparent rounded-[2.5rem] pointer-events-none"></div>
        <form
          onSubmit={requestSaveSettings}
          className="bg-black/20 p-8 rounded-[2.5rem] border border-white/10 space-y-8 relative z-10"
        >
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-black text-white text-xl flex items-center gap-3">
              <div className="p-2 bg-yellow-400/10 rounded-xl">
                <Target className="w-6 h-6 text-yellow-500" />
              </div> 
              Goal Architecture
            </h3>
          </div>

          <div className="grid grid-cols-1 gap-6">
            {[
              { id: "monthlyIncome", label: "Monthly Revenue", icon: TrendingUp, color: "text-emerald-400" },
              { id: "monthlyBudget", label: "Operating Budget", icon: Briefcase, color: "text-violet-400" },
              { id: "dailyBudget", label: "Daily Threshold", icon: Sparkles, color: "text-amber-400" }
            ].map((field) => (
              <div key={field.id} className="space-y-3">
                <label className="text-[10px] text-slate-600 font-extrabold uppercase tracking-[0.3em] flex items-center gap-2">
                  <field.icon className={`w-3 h-3 ${field.color}`} />
                  {field.label}
                </label>
                <div className="relative group">
                  <div className="absolute left-6 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-white transition-colors">
                    <IndianRupee className="w-5 h-5" />
                  </div>
                  <input
                    type="number"
                    value={localSettings[field.id] || ""}
                    onChange={(e) =>
                      setLocalSettings({ ...localSettings, [field.id]: e.target.value })
                    }
                    className="w-full pl-16 pr-32 py-5 bg-black/40 border-2 border-white/5 rounded-[2rem] text-xl font-black text-white outline-none focus:border-indigo-500/50 focus:bg-indigo-500/5 transition-all placeholder:text-slate-800 shadow-2xl"
                    placeholder="0"
                  />
                  {localSettings[field.id] > 0 && (
                    <div className="absolute right-6 top-1/2 -translate-y-1/2 px-4 py-2 bg-white/5 rounded-2xl border border-white/10 backdrop-blur-md">
                      <span className="text-xs font-black text-indigo-400">
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
            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white py-5 rounded-[2rem] font-black text-lg shadow-2xl shadow-indigo-900/40 transition-all disabled:opacity-50 flex items-center justify-center gap-3 mt-4 overflow-hidden relative"
          >
            {savingSettings ? (
              <>
                <Loader2 className="w-6 h-6 animate-spin" />
                <span className="animate-pulse">Syncing with Cloud...</span>
              </>
            ) : (
              <>
                <span>Update Financial Blueprint</span>
                <ChevronRight className="w-6 h-6" />
              </>
            )}
          </motion.button>
        </form>
      </section>

      {/* Dynamic Sign Out */}
      <motion.button
        whileHover={{ x: 5 }}
        type="button"
        onClick={() => triggerConfirm("Terminate current session?", onSignOut)}
        className="group flex items-center gap-3 text-rose-500/60 hover:text-rose-400 font-black text-sm uppercase tracking-widest transition-all px-4 py-2"
      >
        <div className="p-2 bg-rose-500/5 rounded-xl group-hover:bg-rose-500/10 transition-colors">
          <LogOut className="w-5 h-5" />
        </div>
        Sign Out Securely
      </motion.button>
    </motion.div>
  );
};

export default ProfilePage;
