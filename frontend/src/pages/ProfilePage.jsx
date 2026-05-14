import React, { useState, useMemo, useEffect } from "react";
import {
  User, Settings as SettingsIcon, ChevronRight, ShieldCheck,
  Plus, Link2, Unlink, CheckCircle, AlertCircle, Clock,
  Building2, CreditCard, Wallet, ArrowUpRight, ArrowDownRight,
  Target, Landmark, Briefcase, TrendingUp, TrendingDown,
  BarChart2, Zap, Bot, Brain, Sparkles, Crown,
  IndianRupee, PiggyBank, Activity, FileBarChart,
  Calendar, Receipt, Shield, Star, ExternalLink,
  RefreshCw, BadgeCheck, CircleDashed, Info,
  ListFilter, PieChart as PieChartIcon, SlidersHorizontal, Check, X,
  LogOut, Trash2, Key, Bell, ShieldAlert,
  Smartphone, Monitor, Globe, MapPin, UserCircle
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { TABS } from "@shared/config/constants";
import { TierBadge } from "../components/ui/TierBadge";
import { formatIndianCompact } from "@shared/utils/helpers";
import { ProfileSkeleton } from "../components/ui/Skeletons";
import { alertsApi, authApi } from "../api";

// ─── Helpers ─────────────────────────────────────────────────────────────────

const fmt = (v) => {
  const n = parseFloat(v) || 0;
  if (formatIndianCompact) return formatIndianCompact(n);
  return n >= 1e7 ? `${(n/1e7).toFixed(2)}Cr` : n >= 1e5 ? `${(n/1e5).toFixed(2)}L` : n >= 1e3 ? `${(n/1e3).toFixed(1)}K` : n.toLocaleString("en-IN");
};

// ─── Primitives ───────────────────────────────────────────────────────────────

const Card = ({ children, className = "", glow }) => (
  <div className={`rounded-3xl border border-white/8 relative overflow-hidden ${className}`} style={{ background: "rgba(255,255,255,0.03)" }}>
    {glow && <div className={`absolute top-0 right-0 w-56 h-56 ${glow} blur-[80px] rounded-full -translate-y-1/3 translate-x-1/3 pointer-events-none`} />}
    {children}
  </div>
);

const Pill = ({ label, color = "indigo" }) => {
  const c = { 
    indigo: "bg-indigo-500/15 border-indigo-500/30 text-indigo-400", 
    emerald: "bg-emerald-500/15 border-emerald-500/30 text-emerald-400", 
    amber: "bg-amber-500/15 border-amber-500/30 text-amber-400", 
    rose: "bg-rose-500/15 border-rose-500/30 text-rose-400", 
    slate: "bg-slate-500/15 border-slate-500/30 text-slate-400", 
    violet: "bg-violet-500/15 border-violet-500/30 text-violet-400",
    blue: "bg-blue-500/15 border-blue-500/30 text-blue-400"
  };
  return <span className={`px-2 py-0.5 rounded-full border text-[9px] font-black uppercase tracking-wider ${c[color] || c.indigo}`}>{label}</span>;
};

const Modal = ({ isOpen, onClose, title, subtitle, children, icon: Icon }) => (
  <AnimatePresence>
    {isOpen && (
      <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
        <motion.div 
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/60 backdrop-blur-sm" 
        />
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-lg bg-[#0f172a] border border-white/10 rounded-[2.5rem] shadow-2xl overflow-hidden"
        >
          <div className="p-6 border-b border-white/5 flex items-center justify-between">
            <div className="flex items-center gap-4">
              {Icon && (
                <div className="p-3 bg-white/5 rounded-2xl text-indigo-400">
                  <Icon className="w-6 h-6" />
                </div>
              )}
              <div>
                <h3 className="text-xl font-black text-white">{title}</h3>
                {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
              </div>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full transition-colors">
              <X className="w-5 h-5 text-slate-400" />
            </button>
          </div>
          <div className="p-6 max-h-[70vh] overflow-y-auto custom-scrollbar">
            {children}
          </div>
        </motion.div>
      </div>
    )}
  </AnimatePresence>
);

const FormField = ({ label, children, error }) => (
  <div className="space-y-1.5">
    <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest pl-1">{label}</label>
    {children}
    {error && <p className="text-[10px] text-rose-500 font-bold pl-1 mt-1">{error}</p>}
  </div>
);

const Input = ({ ...props }) => (
  <input 
    {...props}
    className="w-full h-12 bg-white/5 border border-white/10 rounded-2xl px-4 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all placeholder:text-slate-700"
  />
);

const Select = ({ options, ...props }) => (
  <select 
    {...props}
    className="w-full h-12 bg-white/5 border border-white/10 rounded-2xl px-4 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all appearance-none"
  >
    {options.map(opt => (
      <option key={opt.value} value={opt.value} className="bg-[#1e293b] text-white">
        {opt.label}
      </option>
    ))}
  </select>
);

// ─── 1. HERO ─────────────────────────────────────────────────────────────────

const HeroSection = ({ user, setActiveTab, onLogout, onEdit }) => {
  const initials = [user?.first_name, user?.last_name].filter(Boolean).map(n => n[0]).join("").toUpperCase() || (user?.username || "U")[0].toUpperCase();
  const displayName = [user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.username || "User";
  const occupation = user?.preferences?.occupation || user?.lifeStage || "Member";

  return (
    <Card className="p-6" glow="bg-indigo-500/20">
      <div className="relative z-10 flex flex-col sm:flex-row items-start justify-between gap-6">
        <div className="flex items-center gap-5 min-w-0">
          <div className="relative shrink-0">
            <motion.div
              whileHover={{ scale: 1.04, rotate: 1 }}
              className="w-20 h-20 rounded-3xl bg-gradient-to-br from-indigo-500 via-indigo-600 to-violet-700 flex items-center justify-center shadow-xl shadow-indigo-900/40 text-2xl font-black text-white"
            >
              {initials}
            </motion.div>
            <div className="absolute -bottom-1.5 -right-1.5 w-7 h-7 bg-emerald-500 rounded-2xl border-2 border-[#0f172a] flex items-center justify-center shadow-lg">
              <ShieldCheck className="w-3.5 h-3.5 text-white" />
            </div>
          </div>
          <div className="min-w-0">
            <h2 className="text-2xl font-black text-white tracking-tight truncate">{displayName}</h2>
            <p className="text-xs text-slate-500 truncate mt-0.5">{user?.email || "—"}</p>
            <div className="flex gap-2 flex-wrap mt-3">
              <TierBadge tier={user?.tier || "free"} showLabel size="sm" />
              <Pill label="Verified" color="emerald" />
              <Pill label={occupation} color="slate" />
            </div>
          </div>
        </div>
        <div className="flex gap-2 shrink-0 self-end sm:self-start">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onEdit}
            className="px-4 py-2 bg-white/5 rounded-2xl border border-white/10 text-xs font-black text-white hover:bg-white/10 transition-all flex items-center gap-2"
          >
            <UserCircle className="w-4 h-4 text-indigo-400" />
            Edit Profile
          </motion.button>
          <motion.button
            whileHover={{ rotate: 90, scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={() => setActiveTab(TABS.SETTINGS)}
            className="p-2.5 bg-white/5 rounded-2xl border border-white/10 text-slate-400 hover:text-white transition-all"
          >
            <SettingsIcon className="w-5 h-5" />
          </motion.button>
        </div>
      </div>
      <div className="relative z-10 mt-6 pt-4 border-t border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-[11px] text-slate-600">
            <Calendar className="w-3.5 h-3.5" />
            <span>Joined {user?.created_at ? new Date(user.created_at).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' }) : "Recently"}</span>
          </div>
          {user?.preferences?.location && (
            <div className="flex items-center gap-1.5 text-[11px] text-slate-600">
              <MapPin className="w-3.5 h-3.5" />
              <span>{user.preferences.location}</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[10px] font-black text-emerald-400 uppercase tracking-wider">Live Active</span>
        </div>
      </div>
    </Card>
  );
};

// ─── 2. QUICK STATS BAR ───────────────────────────────────────────────────────

const QuickStatsBar = ({ wealthItems, transactions, settings, onEditFinance }) => {
  const totalAssets = wealthItems.filter(i => i.type === "asset").reduce((s, i) => s + parseFloat(i.amount || 0), 0);
  const totalLiab   = wealthItems.filter(i => i.type === "liability").reduce((s, i) => s + parseFloat(i.amount || 0), 0);
  const netWorth    = totalAssets - totalLiab;
  const income      = parseFloat(settings?.monthlyIncome || 0);
  const budget      = parseFloat(settings?.monthlyBudget || 0);
  const savingsRate = income > 0 ? Math.max(0, ((income - budget) / income) * 100) : 0;
  
  const thisMonth = useMemo(() => {
    const now = new Date();
    return transactions.filter(t => {
      const d = new Date(t.date || t.created_at);
      return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear() && t.type === "expense";
    }).reduce((s, t) => s + parseFloat(t.amount || 0), 0);
  }, [transactions]);

  const budgetPct = budget > 0 ? Math.min(100, (thisMonth / budget) * 100) : 0;
  const budgetStatus = thisMonth > budget ? "Limit Reached" : thisMonth > budget * 0.8 ? "Warning" : "On Track";

  const stats = [
    { label: "Net Worth",    value: `${fmt(netWorth)}`,   color: netWorth >= 0 ? "text-emerald-400" : "text-rose-400" },
    { label: "Monthly Spend", value: `${fmt(thisMonth)}`, color: "text-white" },
    { label: "Savings Rate", value: `${savingsRate.toFixed(0)}%`, color: savingsRate >= 20 ? "text-emerald-400" : savingsRate >= 10 ? "text-amber-400" : "text-rose-400" },
    { label: "Total Debt",   value: totalLiab > 0 ? `${fmt(totalLiab)}` : "Debt Free", color: totalLiab > 0 ? "text-rose-400" : "text-emerald-400" },
  ];

  return (
    <div className="space-y-3">
      <Card className="p-4">
        <div className="grid grid-cols-4 divide-x divide-white/5">
          {stats.map((s, i) => (
            <div key={i} className="px-3 first:pl-0 last:pr-0 flex flex-col gap-0.5">
              <span className="text-[9px] text-slate-600 font-black uppercase tracking-widest leading-tight">{s.label}</span>
              <span className={`text-sm font-black leading-tight ${s.color}`}>{s.value}</span>
            </div>
          ))}
        </div>
      </Card>
      
      <Card className="p-3 bg-white/[0.02]">
        <div className="flex items-center justify-between mb-2 px-1">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Monthly Budget Progress</span>
            {budget > 0 && (
              <Pill label={budgetStatus} color={budgetStatus === "Limit Reached" ? "rose" : budgetStatus === "Warning" ? "amber" : "emerald"} />
            )}
          </div>
          <button onClick={onEditFinance} className="text-[10px] font-black text-indigo-400 hover:text-indigo-300 transition-colors uppercase tracking-widest">
            Adjust Goals
          </button>
        </div>
        {budget > 0 ? (
          <div className="relative h-2 rounded-full bg-white/5 overflow-hidden">
            <motion.div 
              initial={{ width: 0 }} 
              animate={{ width: `${budgetPct}%` }} 
              className={`h-full rounded-full transition-colors ${budgetPct > 100 ? "bg-rose-500" : budgetPct > 80 ? "bg-amber-500" : "bg-indigo-500"}`} 
            />
          </div>
        ) : (
          <div className="text-center py-1">
            <button onClick={onEditFinance} className="text-[10px] text-slate-600 hover:text-slate-500 font-bold">
              + Set monthly budget to track spending
            </button>
          </div>
        )}
      </Card>
    </div>
  );
};

// ─── 3. FINANCIAL HEALTH SCORE ────────────────────────────────────────────────

const HealthScoreSection = ({ wealthItems, settings }) => {
  const income  = parseFloat(settings?.monthlyIncome || 0);
  const budget  = parseFloat(settings?.monthlyBudget || 0);
  const totalAssets = wealthItems.filter(i => i.type === "asset").reduce((s, i) => s + parseFloat(i.amount || 0), 0);
  const totalLiab   = wealthItems.filter(i => i.type === "liability").reduce((s, i) => s + parseFloat(i.amount || 0), 0);

  const savingsRate = income > 0 ? Math.max(0, 100 - (budget / income * 100)) : 0;
  const dtiRatio    = income > 0 ? (totalLiab / (income * 12)) * 100 : 0;
  const cashAssets  = wealthItems.filter(i => i.type === "asset" && (i.title?.toLowerCase().includes("bank") || i.title?.toLowerCase().includes("cash"))).reduce((s, i) => s + parseFloat(i.amount || 0), 0);
  const efRatio     = budget > 0 ? cashAssets / budget : 0;

  const savingsScore = savingsRate >= 30 ? 100 : savingsRate >= 20 ? 80 : savingsRate >= 10 ? 60 : 30;
  const dtiScore     = dtiRatio < 20 ? 100 : dtiRatio < 40 ? 70 : dtiRatio < 60 ? 40 : 10;
  const efScore      = efRatio >= 6 ? 100 : efRatio >= 3 ? 70 : efRatio >= 1 ? 40 : 10;
  const score = income > 0 ? Math.round(savingsScore * 0.4 + dtiScore * 0.3 + efScore * 0.3) : 0;

  const riskLevel = dtiRatio > 50 || savingsRate < 5 || efRatio < 1 ? "High" : dtiRatio > 30 || savingsRate < 15 || efRatio < 3 ? "Medium" : "Low";
  const scoreLabel = score >= 90 ? "Excellent" : score >= 70 ? "Stable" : score >= 50 ? "Average" : "At Risk";
  const scoreColor = score >= 80 ? "#10b981" : score >= 50 ? "#f59e0b" : "#f43f5e";

  const factors = [
    { label: "Savings Rate",    value: `${savingsRate.toFixed(0)}%`,       score: savingsScore },
    { label: "Debt-to-Income",  value: `${dtiRatio.toFixed(0)}%`,          score: dtiScore },
    { label: "Emergency Fund",  value: `${efRatio.toFixed(1)}× months`,    score: efScore },
  ];

  const pieData = [
    { value: score,       color: scoreColor },
    { value: 100 - score, color: "rgba(255,255,255,0.04)" },
  ];

  return (
    <Card className="p-6">
      <div className="flex items-start justify-between mb-5">
        <div>
          <p className="text-[10px] font-black text-slate-600 uppercase tracking-[0.3em]">Financial Health</p>
          <p className="text-xs text-slate-500 mt-0.5">Savings · Debt · Liquidity</p>
        </div>
        <Pill label={riskLevel + " Risk"} color={riskLevel === "High" ? "rose" : riskLevel === "Medium" ? "amber" : "emerald"} />
      </div>
      <div className="flex items-center gap-6">
        <div className="relative w-32 h-32 shrink-0">
          <div className="absolute inset-3 rounded-full blur-xl opacity-25" style={{ backgroundColor: scoreColor }} />
          <ResponsiveContainer width="100%" height="100%" minWidth={0}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={44} outerRadius={56} startAngle={90} endAngle={450} paddingAngle={0} dataKey="value" stroke="none">
                {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <motion.span initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="text-3xl font-black text-white leading-none">{score}</motion.span>
            <span className="text-[9px] font-black uppercase tracking-widest text-slate-500 mt-0.5">{scoreLabel}</span>
          </div>
        </div>
        <div className="flex-1 space-y-3">
          {factors.map(f => (
            <div key={f.label}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-slate-500 font-bold">{f.label}</span>
                <span className="text-[10px] text-slate-400 font-black">{f.value}</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-white/5 overflow-hidden">
                <motion.div
                  initial={{ width: 0 }} animate={{ width: `${f.score}%` }} transition={{ duration: 0.8, delay: 0.2 }}
                  className="h-full rounded-full"
                  style={{ backgroundColor: f.score >= 80 ? "#10b981" : f.score >= 50 ? "#f59e0b" : "#f43f5e" }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
      {income === 0 && (
        <div className="mt-4 p-3 rounded-2xl bg-amber-500/8 border border-amber-500/15 flex items-start gap-2">
          <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <p className="text-[11px] text-amber-400/80">Set your monthly income in Budget to unlock your full health score.</p>
        </div>
      )}
    </Card>
  );
};


// ─── 5. PORTFOLIO SNAPSHOT ────────────────────────────────────────────────────

const PortfolioSnapshot = ({ wealthItems, setActiveTab }) => {
  const assets   = wealthItems.filter(i => i.type === "asset");
  const liabs    = wealthItems.filter(i => i.type === "liability");
  const totalA   = assets.reduce((s, i) => s + parseFloat(i.amount || 0), 0);
  const totalL   = liabs.reduce((s, i) => s + parseFloat(i.amount || 0), 0);
  const netWorth = totalA - totalL;

  const categoryTotals = assets.reduce((acc, item) => {
    const cat = item.category || item.asset_type || "Other";
    acc[cat] = (acc[cat] || 0) + parseFloat(item.amount || 0);
    return acc;
  }, {});
  const COLORS = ["#6366f1","#10b981","#f59e0b","#f43f5e","#8b5cf6","#38bdf8"];
  const slices  = Object.entries(categoryTotals).slice(0,6).map(([name,value],i) => ({ name, value, color: COLORS[i] }));

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-[10px] font-black text-slate-600 uppercase tracking-[0.3em]">Portfolio</p>
          <p className="text-lg font-black text-white mt-0.5">{fmt(netWorth)}</p>
        </div>
        <button onClick={() => setActiveTab(TABS.WEALTH)} className="text-[11px] text-indigo-400 font-bold hover:text-indigo-300 flex items-center gap-0.5 transition-colors">
          Full View <ExternalLink className="w-3 h-3" />
        </button>
      </div>
      <div className="flex items-center gap-5">
        <div className="w-24 h-24 shrink-0">
          {slices.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%" minWidth={0}>
              <PieChart>
                <Pie data={slices} cx="50%" cy="50%" innerRadius={26} outerRadius={44} dataKey="value" stroke="none" paddingAngle={2}>
                  {slices.map((e,i) => <Cell key={i} fill={e.color} />)}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="w-full h-full rounded-full border-4 border-dashed border-white/10 flex items-center justify-center">
              <CircleDashed className="w-6 h-6 text-slate-700" />
            </div>
          )}
        </div>
        <div className="flex-1 space-y-3">
          {[["Assets", totalA, "#10b981"], ["Liabilities", totalL, "#f43f5e"]].map(([lbl,val,col]) => (
            <div key={lbl}>
              <div className="flex justify-between text-[10px] mb-1">
                <span className="text-slate-500 font-bold">{lbl}</span>
                <span className="font-black" style={{color:col}}>{fmt(val)}</span>
              </div>
              <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                <div className="h-full rounded-full" style={{ width: totalA+totalL>0?`${(val/(totalA+totalL))*100}%`:"0%", backgroundColor:col }} />
              </div>
            </div>
          ))}
          {slices.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {slices.slice(0,3).map(s => (
                <div key={s.name} className="flex items-center gap-1">
                  <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{backgroundColor:s.color}} />
                  <span className="text-[9px] text-slate-600">{s.name}</span>
                </div>
              ))}
              {slices.length > 3 && <span className="text-[9px] text-slate-700">+{slices.length-3} more</span>}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
};

// ─── 6. NAV SHORTCUTS ─────────────────────────────────────────────────────────

const ALL_SHORTCUTS = [
  { id: TABS.BUDGET, label: "Budget", icon: Target, color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20", sub: "Monthly targets" },
  { id: TABS.GOALS, label: "Goals", icon: Star, color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20", sub: "Track milestones" },
  { id: TABS.LOANS, label: "Loans", icon: Briefcase, color: "text-rose-400", bg: "bg-rose-500/10", border: "border-rose-500/20", sub: "Liabilities" },
  { id: TABS.PLANNER, label: "Planner", icon: TrendingUp, color: "text-indigo-400", bg: "bg-indigo-500/10", border: "border-indigo-500/20", sub: "AI-driven plans" },

  { id: TABS.AUDIT, label: "Tax Audit", icon: Receipt, color: "text-sky-400", bg: "bg-sky-500/10", border: "border-sky-500/20", sub: "Deductions score" },
  { id: TABS.HISTORY, label: "History", icon: ListFilter, color: "text-slate-400", bg: "bg-slate-500/10", border: "border-slate-500/20", sub: "All transactions" },
  { id: TABS.WEALTH, label: "Wealth", icon: Landmark, color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20", sub: "Net valuation" },
  { id: TABS.ADD, label: "Add New", icon: Plus, color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20", sub: "Manual entry" },
  { id: TABS.STATS, label: "Stats", icon: PieChartIcon, color: "text-orange-400", bg: "bg-orange-500/10", border: "border-orange-500/20", sub: "Spending analysis" },
  { id: TABS.DEBIT_CARDS, label: "Debit Cards", icon: CreditCard, color: "text-sky-400", bg: "bg-sky-500/10", border: "border-sky-500/20", sub: "Manage cards" },
  { id: TABS.CREDIT_CARDS, label: "Credit Cards", icon: CreditCard, color: "text-violet-400", bg: "bg-violet-500/10", border: "border-violet-500/20", sub: "Manage cards" },
];

const QuickActionsModal = ({ isOpen, onClose, currentActions, onSave }) => {
  const [selected, setSelected] = useState(currentActions || []);
  
  const toggle = (id) => {
    if (selected.includes(id)) {
      setSelected(selected.filter(i => i !== id));
    } else {
      if (selected.length < 6) setSelected([...selected, id]);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm" 
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative w-full max-w-lg bg-[#0f172a] border border-white/10 rounded-[2.5rem] shadow-2xl overflow-hidden"
          >
            <div className="p-6 border-b border-white/5 flex items-center justify-between">
              <div>
                <h3 className="text-xl font-black text-white">Configure Actions</h3>
                <p className="text-xs text-slate-500 mt-1">Select up to 6 shortcuts for your profile</p>
              </div>
              <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full transition-colors">
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>
            
            <div className="p-6 grid grid-cols-2 gap-3 max-h-[60vh] overflow-y-auto">
              {ALL_SHORTCUTS.map(s => {
                const isSelected = selected.includes(s.id);
                return (
                  <button
                    key={s.id}
                    onClick={() => toggle(s.id)}
                    className={`flex items-center gap-3 p-3 rounded-2xl border transition-all text-left ${isSelected ? "bg-indigo-500/10 border-indigo-500/40" : "bg-white/[0.02] border-white/5 hover:border-white/10"}`}
                  >
                    <div className={`p-2 rounded-xl bg-white/5 ${s.color}`}>
                      <s.icon className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-bold text-white truncate">{s.label}</p>
                      <p className="text-[10px] text-slate-600 truncate">{s.sub}</p>
                    </div>
                    <div className={`w-5 h-5 rounded-full border flex items-center justify-center transition-all ${isSelected ? "bg-indigo-500 border-indigo-500" : "border-white/10"}`}>
                      {isSelected && <Check className="w-3 h-3 text-white" />}
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="p-6 bg-white/[0.02] border-t border-white/5 flex gap-3">
              <button 
                onClick={onClose}
                className="flex-1 py-3.5 rounded-2xl text-xs font-black uppercase tracking-widest text-slate-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button 
                onClick={() => { onSave(selected); onClose(); }}
                className="flex-[2] py-3.5 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-black uppercase tracking-widest shadow-lg shadow-indigo-900/20 transition-all"
              >
                Save Changes
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

const NavShortcuts = ({ setActiveTab, settings, user, onUpdateActions }) => {
  const [modalOpen, setModalOpen] = useState(false);
  const preferences = user?.preferences || {};
  const selectedIds = preferences.quick_actions || [TABS.BUDGET, TABS.GOALS, TABS.LOANS, TABS.PLANNER, TABS.AUDIT];
  
  const shortcuts = ALL_SHORTCUTS.filter(s => selectedIds.includes(s.id));
  const hasBudget = parseFloat(settings?.monthlyBudget || 0) > 0;

  return (
    <div>
      <div className="flex items-center justify-between px-1 mb-3">
        <p className="text-[10px] font-black text-slate-600 uppercase tracking-[0.3em]">Quick Actions</p>
        <button 
          onClick={() => setModalOpen(true)}
          className="text-[10px] font-black text-indigo-400 uppercase tracking-widest hover:text-indigo-300 transition-colors flex items-center gap-1"
        >
          <SlidersHorizontal className="w-3 h-3" />
          Configure
        </button>
      </div>
      
      <div className="grid grid-cols-3 gap-2.5">
        {shortcuts.map(s => (
          <motion.button key={s.id} whileHover={{ scale: 1.03, y: -2 }} whileTap={{ scale: 0.97 }}
            onClick={() => setActiveTab(s.id)}
            className={`relative flex flex-col items-center gap-2.5 py-4 px-2 rounded-3xl border transition-all text-center ${s.border || "border-white/5"} bg-white/[0.02] hover:bg-white/5`}
          >
            {s.id === TABS.BUDGET && !hasBudget && <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-amber-500" />}
            <div className={`p-2.5 rounded-2xl bg-white/5 ${s.color}`}>
              <s.icon className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs font-black text-white leading-tight">{s.label}</p>
              <p className="text-[9px] text-slate-600 mt-0.5 leading-tight">
                {s.id === TABS.BUDGET && hasBudget ? `₹${fmt(settings.monthlyBudget)}/mo` : s.sub}
              </p>
            </div>
          </motion.button>
        ))}
      </div>

      <QuickActionsModal 
        isOpen={modalOpen} 
        onClose={() => setModalOpen(false)} 
        currentActions={selectedIds}
        onSave={onUpdateActions}
      />
    </div>
  );
};

// ─── 7. TORA ACTIVITY ────────────────────────────────────────────────────────

const ToraActivity = ({ user, setActiveTab }) => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const isPro = user?.tier === "pro" || user?.tier === "enterprise";

  useEffect(() => {
    let mounted = true;
    const fetchAlerts = async () => {
      try {
        const data = await alertsApi.list({ unreadOnly: false });
        if (mounted) {
          setAlerts((data?.data || data || []).slice(0, 3));
        }
      } catch (err) {
        console.error("Failed to fetch alerts for profile", err);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    fetchAlerts();
    return () => { mounted = false; };
  }, []);

  const memUsed  = isPro ? 37 : 14;
  const memLimit = isPro ? 100 : 20;
  const memPct   = (memUsed / memLimit) * 100;

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-violet-500/15 rounded-xl">
            <Bot className="w-4 h-4 text-violet-400" />
          </div>
          <div>
            <p className="text-xs font-black text-white">TORA Activity</p>
            <p className="text-[10px] text-slate-600 mt-0.5">AI Insights & Surveillance</p>
          </div>
        </div>
        <button onClick={() => setActiveTab(TABS.CHAT)} className="px-3 py-1.5 rounded-xl bg-violet-600/20 border border-violet-500/25 text-violet-400 text-[10px] font-black hover:bg-violet-600/30 transition-colors">
          Open Chat
        </button>
      </div>

      <div className="mb-6 p-4 rounded-2xl bg-white/[0.02] border border-white/5">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5">
            <Brain className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">Context Memory</span>
          </div>
          <span className="text-[10px] font-black text-white">{memUsed} / {memLimit} msgs</span>
        </div>
        <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
          <div className={`h-full rounded-full transition-all duration-1000 ${memPct > 80 ? "bg-rose-500" : memPct > 60 ? "bg-amber-500" : "bg-violet-500"}`} style={{ width: `${memPct}%` }} />
        </div>
        {!isPro && (
          <div className="mt-2.5 p-2 rounded-xl bg-amber-500/5 border border-amber-500/10 flex items-center justify-between">
            <p className="text-[9px] text-amber-500/70 font-bold italic">Memory is 70% full on Free Tier</p>
            <button onClick={() => setActiveTab(TABS.SETTINGS)} className="text-[9px] text-amber-400 font-black uppercase underline">Upgrade</button>
          </div>
        )}
      </div>

      <p className="text-[10px] font-black text-slate-700 uppercase tracking-widest mb-3 pl-1">Recent Intelligence</p>
      <div className="space-y-2">
        {loading ? (
          [1,2].map(i => <div key={i} className="h-16 w-full bg-white/5 rounded-2xl animate-pulse" />)
        ) : alerts.length > 0 ? (
          alerts.map((ins, i) => (
            <div key={i} className={`flex items-start gap-3 p-3.5 rounded-2xl border transition-all hover:translate-x-1 ${ins.severity === "danger" ? "bg-rose-500/5 border-rose-500/15" : ins.severity === "warning" ? "bg-amber-500/5 border-amber-500/15" : "bg-indigo-500/5 border-indigo-500/10"}`}>
              <div className={`mt-0.5 shrink-0 ${ins.severity === "danger" ? "text-rose-400" : ins.severity === "warning" ? "text-amber-400" : "text-indigo-400"}`}>
                {ins.alert_type === "spike" ? <TrendingUp className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[11px] font-bold text-white mb-0.5">{ins.title}</p>
                <p className="text-[10px] text-slate-400 leading-relaxed line-clamp-2">{ins.description}</p>
                <p className="text-[8px] text-slate-600 mt-1.5 uppercase font-black tracking-widest">{new Date(ins.created_at).toLocaleDateString()}</p>
              </div>
            </div>
          ))
        ) : (
          <div className="p-8 rounded-2xl border border-dashed border-white/5 text-center">
            <Bot className="w-8 h-8 text-slate-800 mx-auto mb-2" />
            <p className="text-[10px] text-slate-700 font-bold italic">Tora is still learning your patterns.</p>
          </div>
        )}
      </div>
    </Card>
  );
};

const SecurityCard = ({ onLogout, onPasswordChange }) => {
  return (
    <Card className="p-5">
      <div className="flex items-center gap-2.5 mb-5">
        <div className="p-2 bg-rose-500/15 rounded-xl text-rose-400">
          <ShieldAlert className="w-4 h-4" />
        </div>
        <div>
          <p className="text-xs font-black text-white">Security & Access</p>
          <p className="text-[10px] text-slate-600 mt-0.5">Control your account</p>
        </div>
      </div>
      
      <div className="space-y-2">
        <button 
          onClick={onPasswordChange}
          className="w-full flex items-center justify-between p-3.5 rounded-2xl bg-white/[0.02] border border-white/5 hover:bg-white/5 transition-all text-left"
        >
          <div className="flex items-center gap-3">
            <Key className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-bold text-white">Update Password</span>
          </div>
          <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
        </button>
        
        <button 
          onClick={onLogout}
          className="w-full flex items-center gap-3 p-3.5 rounded-2xl bg-rose-500/5 border border-rose-500/10 hover:bg-rose-500/10 transition-all text-left text-rose-400 mt-4"
        >
          <LogOut className="w-4 h-4" />
          <span className="text-xs font-black uppercase tracking-widest">Sign Out Everywhere</span>
        </button>
      </div>
    </Card>
  );
};

// ─── 8. ACCOUNT COMPLETENESS ─────────────────────────────────────────────────

const AccountCompleteness = ({ user, wealthItems, settings, setActiveTab }) => {
  const checks = [
    { label: "Profile photo",       done: false,                                        tab: TABS.SETTINGS },
    { label: "Phone number",        done: !!user?.phone,                                tab: TABS.SETTINGS },
    { label: "PAN linked",          done: !!user?.pan,                                  tab: TABS.SETTINGS },
    { label: "Monthly income set",  done: parseFloat(settings?.monthlyIncome||0) > 0,   tab: TABS.BUDGET },
    { label: "Monthly budget set",  done: parseFloat(settings?.monthlyBudget||0) > 0,   tab: TABS.BUDGET },
    { label: "Net worth tracked",   done: wealthItems.length > 0,                       tab: TABS.WEALTH },
    { label: "Bank account linked", done: false,                                        tab: TABS.BANK_ACCOUNTS },
    { label: "Financial goal set",  done: false,                                        tab: TABS.GOALS },
  ];

  const done  = checks.filter(c => c.done).length;
  const total = checks.length;
  const pctN  = Math.round((done / total) * 100);
  const barColor = pctN >= 80 ? "bg-emerald-500" : pctN >= 50 ? "bg-amber-500" : "bg-indigo-500";

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="text-[10px] font-black text-slate-600 uppercase tracking-[0.3em]">Profile Completeness</p>
          <p className="text-base font-black text-white mt-0.5">{pctN}% complete</p>
        </div>
        <div className="text-right">
          <span className="text-2xl font-black text-white">{done}</span>
          <span className="text-sm text-slate-600">/{total}</span>
        </div>
      </div>
      <div className="h-2 rounded-full bg-white/5 overflow-hidden mb-4">
        <motion.div initial={{ width: 0 }} animate={{ width: `${pctN}%` }} transition={{ duration: 1, delay: 0.3 }} className={`h-full rounded-full ${barColor}`} />
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {checks.map((c, i) => (
          <button key={i} onClick={() => !c.done && setActiveTab(c.tab)}
            className={`flex items-center gap-2 px-3 py-2 rounded-xl text-left transition-colors ${c.done ? "opacity-40 cursor-default" : "hover:bg-white/5 cursor-pointer"}`}
          >
            {c.done
              ? <CheckCircle className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
              : <CircleDashed className="w-3.5 h-3.5 text-slate-700 shrink-0" />
            }
            <span className={`text-[11px] font-bold truncate ${c.done ? "text-slate-600 line-through" : "text-slate-400"}`}>{c.label}</span>
          </button>
        ))}
      </div>
      {pctN < 100 && (
        <p className="text-[10px] text-slate-700 text-center mt-3">Complete your profile to unlock full TORA personalization</p>
      )}
    </Card>
  );
};

// ─── 9. TIER UPGRADE BANNER ───────────────────────────────────────────────────

const TierBanner = ({ user, setActiveTab }) => {
  if (user?.tier === "enterprise") return null;
  const isPro = user?.tier === "pro";
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      className={`p-5 rounded-3xl border relative overflow-hidden ${isPro ? "bg-gradient-to-br from-amber-900/30 to-orange-900/20 border-amber-500/20" : "bg-gradient-to-br from-indigo-900/40 to-violet-900/20 border-indigo-500/20"}`}
    >
      <div className={`absolute top-0 right-0 w-40 h-40 blur-[60px] rounded-full pointer-events-none ${isPro ? "bg-amber-500/15" : "bg-indigo-500/15"}`} />
      <div className="relative z-10 flex items-center gap-4">
        <div className={`p-3 rounded-2xl ${isPro ? "bg-amber-500/20" : "bg-indigo-500/20"}`}>
          <Crown className={`w-5 h-5 ${isPro ? "text-amber-400" : "text-indigo-400"}`} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-black text-white">{isPro ? "Upgrade to Enterprise" : "Upgrade to Pro"}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">
            {isPro ? "Unlimited memory, custom integrations, dedicated support" : "Unlock TORA tool calling, unlimited transactions & email reports"}
          </p>
        </div>
        <button onClick={() => setActiveTab(TABS.SETTINGS)}
          className={`px-3 py-2 rounded-2xl text-xs font-black uppercase tracking-wide shrink-0 transition-all ${isPro ? "bg-amber-500/20 border border-amber-500/30 text-amber-400 hover:bg-amber-500/30" : "bg-indigo-600 hover:bg-indigo-500 text-white"}`}
        >
          {isPro ? "Upgrade" : "Go Pro"}
        </button>
      </div>
    </motion.div>
  );
};

// ─── ROOT ─────────────────────────────────────────────────────────────────────

const ProfilePage = ({
  user,
  settings,
  wealthItems = [],
  transactions = [],
  onUpdateSettings,
  triggerConfirm,
  setActiveTab,
  showToast,
  onLogout,
  isLoading,
}) => {
  const [showEditProfile, setShowEditProfile] = useState(false);
  const [showEditFinance, setShowEditFinance] = useState(false);
  const [showChangePass, setShowChangePass] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Form States
  const [profileForm, setProfileForm] = useState({
    first_name: user?.first_name || "",
    last_name: user?.last_name || "",
    location: user?.preferences?.location || "",
    occupation: user?.preferences?.occupation || "",
  });

  const [financeForm, setFinanceForm] = useState({
    monthlyIncome: settings?.monthlyIncome || 0,
    monthlyBudget: settings?.monthlyBudget || 0,
    lifeStage: settings?.lifeStage || "early_career",
    riskTolerance: settings?.riskTolerance || "balanced",
    dependents: settings?.dependents || 0,
  });

  const [passForm, setPassForm] = useState({ current: "", new: "", confirm: "" });

  if (isLoading) return <ProfileSkeleton />;

  const handleUpdateProfile = async () => {
    setIsSaving(true);
    try {
      // 1. Update Auth Profile (Names)
      await authApi.updateProfile({ 
        first_name: profileForm.first_name, 
        last_name: profileForm.last_name 
      });

      // 2. Update Finance Profile (Prefs - Location/Occupation)
      const newPrefs = { 
        ...(user?.preferences || {}), 
        location: profileForm.location, 
        occupation: profileForm.occupation 
      };
      await onUpdateSettings({ preferences: newPrefs });

      showToast("Profile updated successfully", "success");
      setShowEditProfile(false);
    } catch (err) {
      showToast(err.message || "Failed to update profile", "error");
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateFinance = async () => {
    setIsSaving(true);
    try {
      await onUpdateSettings(financeForm);
      showToast("Financial goals updated", "success");
      setShowEditFinance(false);
    } catch (err) {
      showToast(err.message || "Failed to update goals", "error");
    } finally {
      setIsSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (passForm.new !== passForm.confirm) {
      showToast("New passwords do not match", "error");
      return;
    }
    setIsSaving(true);
    try {
      await authApi.changePassword({ 
        current_password: passForm.current, 
        new_password: passForm.new 
      });
      showToast("Password changed successfully", "success");
      setShowChangePass(false);
      setPassForm({ current: "", new: "", confirm: "" });
    } catch (err) {
      showToast(err.message || "Failed to change password", "error");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="space-y-4 pb-32"
    >
      <HeroSection user={user} setActiveTab={setActiveTab} onLogout={onLogout} onEdit={() => setShowEditProfile(true)} />
      
      <QuickStatsBar 
        wealthItems={wealthItems} 
        transactions={transactions} 
        settings={settings} 
        onEditFinance={() => setShowEditFinance(true)} 
      />

      <div>
        <HealthScoreSection wealthItems={wealthItems} settings={settings} />
      </div>

      <PortfolioSnapshot wealthItems={wealthItems} setActiveTab={setActiveTab} />
      
      <NavShortcuts 
        setActiveTab={setActiveTab} 
        settings={settings} 
        user={user} 
        onUpdateActions={(ids) => {
          const newPrefs = { ...(user?.preferences || {}), quick_actions: ids };
          onUpdateSettings({ preferences: newPrefs });
        }}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ToraActivity user={user} setActiveTab={setActiveTab} />
        <SecurityCard onLogout={onLogout} onPasswordChange={() => setShowChangePass(true)} />
      </div>

      <AccountCompleteness user={user} wealthItems={wealthItems} settings={settings} setActiveTab={setActiveTab} />
      
      <TierBanner user={user} setActiveTab={setActiveTab} />

      {/* ─── Modals ─────────────────────────────────────────────────────────── */}

      <Modal 
        isOpen={showEditProfile} 
        onClose={() => setShowEditProfile(false)}
        title="Edit Profile"
        subtitle="Update your personal identity details"
        icon={UserCircle}
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <FormField label="First Name">
              <Input value={profileForm.first_name} onChange={e => setProfileForm({...profileForm, first_name: e.target.value})} />
            </FormField>
            <FormField label="Last Name">
              <Input value={profileForm.last_name} onChange={e => setProfileForm({...profileForm, last_name: e.target.value})} />
            </FormField>
          </div>
          <FormField label="Occupation">
            <Input value={profileForm.occupation} onChange={e => setProfileForm({...profileForm, occupation: e.target.value})} placeholder="e.g. Software Engineer" />
          </FormField>
          <FormField label="Location">
            <Input value={profileForm.location} onChange={e => setProfileForm({...profileForm, location: e.target.value})} placeholder="e.g. Mumbai, India" />
          </FormField>
          <button 
            disabled={isSaving}
            onClick={handleUpdateProfile}
            className="w-full h-12 bg-indigo-600 rounded-2xl text-xs font-black uppercase tracking-widest text-white mt-4 disabled:opacity-50"
          >
            {isSaving ? "Saving..." : "Save Profile"}
          </button>
        </div>
      </Modal>

      <Modal 
        isOpen={showEditFinance} 
        onClose={() => setShowEditFinance(false)}
        title="Financial Goals"
        subtitle="Set your monthly targets and life stage"
        icon={Target}
      >
        <div className="space-y-4">
          <FormField label="Monthly Income (₹)">
            <Input type="number" value={financeForm.monthlyIncome} onChange={e => setFinanceForm({...financeForm, monthlyIncome: e.target.value})} />
          </FormField>
          <FormField label="Monthly Budget (₹)">
            <Input type="number" value={financeForm.monthlyBudget} onChange={e => setFinanceForm({...financeForm, monthlyBudget: e.target.value})} />
          </FormField>
          <div className="grid grid-cols-2 gap-3">
            <FormField label="Life Stage">
              <Select 
                value={financeForm.lifeStage} 
                onChange={e => setFinanceForm({...financeForm, lifeStage: e.target.value})}
                options={[
                  { label: "Early Career", value: "early_career" },
                  { label: "Married", value: "married" },
                  { label: "Parent", value: "parent" },
                  { label: "Pre-Retirement", value: "pre_retirement" },
                  { label: "Retired", value: "retired" },
                  { label: "Student", value: "student" },
                ]}
              />
            </FormField>
            <FormField label="Risk Tolerance">
              <Select 
                value={financeForm.riskTolerance} 
                onChange={e => setFinanceForm({...financeForm, riskTolerance: e.target.value})}
                options={[
                  { label: "Conservative", value: "conservative" },
                  { label: "Balanced", value: "balanced" },
                  { label: "Aggressive", value: "aggressive" },
                ]}
              />
            </FormField>
          </div>
          <FormField label="Number of Dependents">
            <Input type="number" value={financeForm.dependents} onChange={e => setFinanceForm({...financeForm, dependents: e.target.value})} />
          </FormField>
          <button 
            disabled={isSaving}
            onClick={handleUpdateFinance}
            className="w-full h-12 bg-indigo-600 rounded-2xl text-xs font-black uppercase tracking-widest text-white mt-4 disabled:opacity-50"
          >
            {isSaving ? "Updating Goals..." : "Sync Financial Profile"}
          </button>
        </div>
      </Modal>

      <Modal 
        isOpen={showChangePass} 
        onClose={() => setShowChangePass(false)}
        title="Change Password"
        subtitle="Keep your financial data secure"
        icon={Key}
      >
        <div className="space-y-4">
          <FormField label="Current Password">
            <Input type="password" value={passForm.current} onChange={e => setPassForm({...passForm, current: e.target.value})} />
          </FormField>
          <div className="h-px bg-white/5 my-2" />
          <FormField label="New Password">
            <Input type="password" value={passForm.new} onChange={e => setPassForm({...passForm, new: e.target.value})} />
          </FormField>
          <FormField label="Confirm New Password">
            <Input type="password" value={passForm.confirm} onChange={e => setPassForm({...passForm, confirm: e.target.value})} />
          </FormField>
          <button 
            disabled={isSaving}
            onClick={handleChangePassword}
            className="w-full h-12 bg-rose-600 rounded-2xl text-xs font-black uppercase tracking-widest text-white mt-4 disabled:opacity-50"
          >
            {isSaving ? "Processing..." : "Update Security Key"}
          </button>
        </div>
      </Modal>

    </motion.div>
  );
};

export default ProfilePage;