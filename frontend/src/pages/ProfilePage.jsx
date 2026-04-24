import React, { useState, useEffect } from "react";
import { 
  User, 
  Target, 
  ShieldCheck, 
  Briefcase, 
  LogOut,
  ChevronRight,
  Sparkles,
  Settings as SettingsIcon,
  Landmark
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { TABS } from "@shared/config/constants";
import { TierBadge, FeatureComparison } from "../components/ui/TierBadge";

const ProfilePage = ({
  user,
  settings,
  wealthItems = [],
  transactions = [],
  onUpdateSettings,
  onSignOut,
  triggerConfirm,
  setActiveTab
}) => {
  const [localSettings, setLocalSettings] = useState(settings || {});

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
  // Default to 0 if no data
  let score = 0;
  let savingsRate = 0;
  
  if (income > 0) {
    const ratio = budget / income;
    savingsRate = Math.max(0, 100 - (ratio * 100));
    
    if (ratio <= 0.5) score = 95;
    else if (ratio <= 0.7) score = 75;
    else if (ratio <= 0.9) score = 50;
    else score = 30;
  }
  
  const scoreColor = score >= 80 ? "#10b981" : score >= 50 ? "#f59e0b" : "#f43f5e";
  const scoreData = [
    { value: score, color: scoreColor },
    { value: 100 - score, color: "rgba(255,255,255,0.03)" }
  ];


  // --- Dynamic Category Counts ---
  const loanCount = wealthItems.filter(i => i.type === "liability" || i.is_loan).length;

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
      <div className="bg-gradient-to-br from-indigo-900/60 to-slate-900/60 backdrop-blur-3xl border border-white/20 p-5 sm:p-8 rounded-[2rem] sm:rounded-[3rem] shadow-[0_25px_50px_-12px_rgba(0,0,0,0.5)] relative overflow-hidden group">
        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/20 blur-[120px] rounded-full -translate-y-1/2 translate-x-1/2 group-hover:bg-indigo-400/30 transition-colors duration-700"></div>
        <div className="absolute bottom-0 left-0 w-64 h-64 bg-purple-500/10 blur-[100px] rounded-full translate-y-1/2 -translate-x-1/2"></div>

        <div className="relative z-10 flex justify-between items-start gap-3">
          <div className="flex items-center gap-4 sm:gap-8 min-w-0">
            <div className="relative shrink-0">
              <motion.div
                whileHover={{ scale: 1.05, rotate: 2 }}
                className="w-20 h-20 sm:w-28 sm:h-28 rounded-2xl sm:rounded-3xl bg-gradient-to-br from-indigo-500 via-indigo-600 to-purple-700 flex items-center justify-center shadow-[0_20px_40px_-10px_rgba(0,0,0,0.5)] relative z-10 overflow-hidden"
              >
                <User className="w-10 h-10 sm:w-14 sm:h-14 text-white" />
                <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                   <Sparkles className="w-8 h-8 text-white/50" />
                </div>
              </motion.div>
              <div className="absolute -bottom-1 -right-1 w-7 h-7 sm:w-10 sm:h-10 bg-emerald-500 rounded-xl sm:rounded-2xl border-2 sm:border-4 border-[#0f172a] shadow-lg flex items-center justify-center z-20">
                 <ShieldCheck className="w-3.5 h-3.5 sm:w-5 sm:h-5 text-white" />
              </div>
            </div>

            <div className="min-w-0">
              <h2 className="text-xl sm:text-3xl font-black text-white tracking-tight truncate">{user?.username || "Admin"}</h2>
              <p className="text-slate-400 font-bold flex items-center gap-2 mt-1 text-xs sm:text-base truncate">
                {user?.email || "user@example.com"}
              </p>
              <div className="mt-3 flex gap-2 flex-wrap">
                 <TierBadge tier={user?.tier || "free"} showLabel={true} size="sm" />
                 <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-bold text-emerald-400 uppercase tracking-tighter">Verified</span>
              </div>
            </div>
          </div>

          <motion.button
            whileHover={{ rotate: 90, scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={() => setActiveTab(TABS.SETTINGS)}
            className="shrink-0 p-2 sm:p-3 bg-white/5 rounded-xl sm:rounded-2xl border border-white/10 text-slate-400 hover:text-white transition-all shadow-xl"
          >
            <SettingsIcon className="w-5 h-5 sm:w-6 sm:h-6" />
          </motion.button>
        </div>
      </div>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Health Score Component */}
        <section className="bg-white/5 backdrop-blur-2xl p-5 sm:p-8 rounded-[2rem] sm:rounded-[3rem] border border-white/10 relative overflow-hidden flex flex-col items-center justify-center group">
          <div className="absolute -inset-px bg-gradient-to-b from-indigo-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
          
          <div className="text-center mb-6">
            <h4 className="text-xs font-black text-slate-400 uppercase tracking-[0.3em] mb-1">Financial Health</h4>
            <div className="h-1 w-12 bg-indigo-500/30 mx-auto rounded-full"></div>
          </div>
          
          <div className="h-52 w-52 relative">
            {/* Outer Glow Ring */}
            <div 
              className="absolute inset-4 rounded-full blur-2xl opacity-20"
              style={{ backgroundColor: scoreColor }}
            ></div>
            
            <ResponsiveContainer width="100%" height="100%" minWidth={0}>
              <PieChart>
                <Pie
                  data={scoreData}
                  cx="50%"
                  cy="50%"
                  innerRadius={70}
                  outerRadius={85}
                  startAngle={90}
                  endAngle={450}
                  paddingAngle={0}
                  dataKey="value"
                  stroke="none"
                >
                  {scoreData.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={entry.color} 
                      className={index === 0 ? "drop-shadow-[0_0_8px_rgba(16,185,129,0.5)]" : ""}
                    />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <motion.span 
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="text-5xl font-black text-white tracking-tighter"
              >
                {score}
              </motion.span>
              <span className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500 mt-1">
                {score >= 90 ? "Excellent" : score >= 70 ? "Stable" : score >= 50 ? "Average" : "At Risk"}
              </span>
            </div>
          </div>
          
          <div className="mt-6 w-full pt-6 border-t border-white/10 grid grid-cols-2 gap-4">
            <div className="text-center group/stat">
              <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1 group-hover/stat:text-indigo-400 transition-colors">Savings Rate</p>
              <p className="text-lg font-black text-emerald-400">{savingsRate.toFixed(0)}%</p>
            </div>
            <div className="text-center group/stat">
              <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1 group-hover/stat:text-indigo-400 transition-colors">Risk Level</p>
              <p className="text-lg font-black text-violet-400">Low</p>
            </div>
          </div>
        </section>

        {/* Quick Links / Portfolio Map */}
        <section className="space-y-4">
          {[
            { label: "Bank Accounts", icon: Landmark, count: "Debit & Credit", color: "text-blue-400", bg: "bg-blue-500/10", border: "border-l-blue-500", onClick: () => setActiveTab(TABS.BANK_ACCOUNTS) },
            { label: "Active Loans", icon: Briefcase, count: loanCount > 0 ? `${loanCount} Active` : "No Loans", color: "text-rose-400", bg: "bg-rose-500/10", border: "border-l-rose-500", onClick: () => setActiveTab(TABS.LOANS) },
            { label: "Set Budget", icon: Target, count: settings?.monthlyBudget > 0 ? `₹${(settings.monthlyBudget/1000).toFixed(0)}K / month` : "Goals & Limits", color: "text-amber-400", bg: "bg-amber-500/10", border: "border-l-amber-500", onClick: () => setActiveTab(TABS.BUDGET) }
          ].map((item, idx) => (
            <motion.div 
              key={idx}
              variants={itemVariants}
              whileHover={{ x: 8, backgroundColor: "rgba(255,255,255,0.08)" }}
              onClick={item.onClick}
              className={`bg-white/5 backdrop-blur-xl p-5 rounded-3xl border border-white/10 flex items-center justify-between group cursor-pointer transition-all border-l-4 ${item.border}`}
            >
              <div className="flex items-center gap-5">
                <div className={`${item.bg} ${item.color} p-3.5 rounded-2xl shadow-inner group-hover:scale-110 transition-transform`}>
                  <item.icon className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-base font-black text-white leading-tight">{item.label}</p>
                  <p className="text-[11px] font-bold text-slate-500 tracking-wide mt-0.5">{item.count}</p>
                </div>
              </div>
              <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-white group-hover:translate-x-1 transition-all" />
            </motion.div>
          ))}
        </section>
      </div>

      {/* Feature Comparison */}
      {user?.tier && (
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-gradient-to-br from-slate-900/50 to-slate-900/30 backdrop-blur-xl p-5 sm:p-8 rounded-[2rem] sm:rounded-[3rem] border border-slate-700/50"
        >
          <div className="mb-6">
            <h3 className="text-2xl font-bold text-slate-100 mb-2">Available Features by Tier</h3>
            <p className="text-slate-400">Compare what you get with each subscription tier</p>
          </div>
          <FeatureComparison />
          {user?.tier === "free" && (
            <motion.div
              className="mt-6 text-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <button className="px-6 py-3 bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 text-white rounded-lg font-bold transition-all">
                Upgrade to Pro
              </button>
            </motion.div>
          )}
        </motion.section>
      )}

      {/* Dynamic Sign Out */}
      <motion.button
        whileHover={{ x: 5 }}
        type="button"
        onClick={() => triggerConfirm("Are you sure you want to sign out?", onSignOut)}
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
