import React, { useState, useMemo, useCallback } from "react";
import { downloadCSV } from "@shared/utils/exportUtils";
import { motion, AnimatePresence } from "framer-motion";
import {
  User, Mail, Lock, Phone, Home as HomeIcon, Briefcase,
  Coins, Moon, Sun, Bell, Shield, ChevronLeft, ChevronRight,
  LogOut, Database, Edit2, Save, X, Search,
  CreditCard, Tag, Target, Camera, Smartphone, Eye,
  Download, Upload, Trash2, AlertTriangle, Crown,
  HelpCircle, FileText, Info, MessageSquare, Ticket,
  Palette, Bot, TrendingUp, RefreshCw, Globe,
  ShieldCheck, Activity, CheckCircle, QrCode, Key,
  Sliders, Repeat, Star, Package, LifeBuoy, ZapOff,
  BarChart2, SlidersHorizontal, Layers
} from "lucide-react";

// ─── Preferences Persistence ─────────────────────────────────────────────────
const PREFS_KEY = "spendsy_preferences";
const loadPrefs = () => {
  try { return JSON.parse(localStorage.getItem(PREFS_KEY)) || {}; }
  catch { return {}; }
};
const savePref = (key, value) => {
  const prefs = { ...loadPrefs(), [key]: value };
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  } catch (err) {
    console.warn("Could not save preference to localStorage:", err);
  }
};

// ─── Reusable Components ──────────────────────────────────────────────────────

const pageVariants = {
  initial: { opacity: 0, x: 30 },
  animate: { opacity: 1, x: 0, transition: { duration: 0.25, ease: [0.22, 1, 0.36, 1] } },
  exit:    { opacity: 0, x: -20, transition: { duration: 0.18 } },
};

const SettingRow = ({ icon: Icon, iconColor = "text-blue-400", iconBg = "bg-blue-500/10", label, description, value, onClick, danger = false, badge, trailing }) => (
  <motion.button
    onClick={onClick}
    whileHover={{ x: 4, backgroundColor: "rgba(255,255,255,0.06)" }}
    whileTap={{ scale: 0.99 }}
    className={`w-full flex items-center gap-4 px-5 py-4 rounded-2xl border border-white/5 transition-colors group ${danger ? "hover:border-rose-500/20" : ""}`}
    style={{ background: "rgba(255,255,255,0.03)" }}
  >
    <div className={`p-2.5 ${iconBg} ${iconColor} rounded-xl shrink-0 group-hover:scale-110 transition-transform`}>
      <Icon className="w-5 h-5" />
    </div>
    <div className="flex-1 text-left min-w-0">
      <p className={`text-sm font-bold ${danger ? "text-rose-400" : "text-white"} leading-tight`}>{label}</p>
      {description && <p className="text-[11px] text-slate-500 mt-0.5 truncate">{description}</p>}
    </div>
    {badge && (
      <span className="px-2 py-0.5 rounded-full bg-indigo-500/20 border border-indigo-500/30 text-[10px] font-bold text-indigo-400 uppercase tracking-wider shrink-0">
        {badge}
      </span>
    )}
    {value && <span className="text-xs text-slate-500 font-medium shrink-0 max-w-[120px] truncate">{value}</span>}
    {trailing || <ChevronRight className={`w-4 h-4 ${danger ? "text-rose-500/50 group-hover:text-rose-400" : "text-slate-700 group-hover:text-slate-400"} transition-colors shrink-0`} />}
  </motion.button>
);

const SettingSection = ({ title, children }) => (
  <div className="space-y-2">
    <p className="text-[10px] font-black text-slate-600 uppercase tracking-[0.3em] px-2 mb-3">{title}</p>
    <div className="space-y-2">{children}</div>
  </div>
);

const PageHeader = ({ title, subtitle, onBack }) => (
  <div className="flex items-center gap-4 pb-5 border-b border-white/5 mb-6">
    <motion.button
      whileHover={{ scale: 1.05, x: -2 }}
      whileTap={{ scale: 0.95 }}
      onClick={onBack}
      className="p-3 bg-white/5 rounded-2xl hover:bg-white/10 transition-colors shadow-lg shrink-0"
    >
      <ChevronLeft className="w-5 h-5 text-white" />
    </motion.button>
    <div>
      <h2 className="text-xl font-black text-white tracking-tight">{title}</h2>
      {subtitle && <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest mt-0.5">{subtitle}</p>}
    </div>
  </div>
);

const Toggle = ({ enabled, onChange }) => (
  <button
    type="button"
    onClick={(e) => { e.stopPropagation(); onChange(!enabled); }}
    className={`relative w-10 h-5 rounded-full transition-all duration-300 shrink-0 ${enabled ? "bg-indigo-500" : "bg-white/10"}`}
  >
    <div className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-all duration-300 ${enabled ? "translate-x-5" : "translate-x-0"}`} />
  </button>
);

const ComingSoonBadge = () => (
  <span className="px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-[10px] font-bold text-amber-400 tracking-wider">Soon</span>
);

// ─── Sub-Pages ────────────────────────────────────────────────────────────────

const PersonalInfoPage = ({ user, onBack }) => {
  const [editing, setEditing] = useState(false);
  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <PageHeader title="Personal Information" subtitle="Manage your identity" onBack={onBack} />
      <div className="space-y-6">
        <SettingSection title="Profile">
          <SettingRow icon={Camera} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="Profile Picture" description="Upload a photo or avatar" />
          <SettingRow icon={User} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Display Name" description="Your public name" value={user?.username || "Admin"} />
          <SettingRow icon={Mail} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Email Address" description="Login & notifications" value={user?.email || "—"} />
          <SettingRow icon={Phone} iconColor="text-sky-400" iconBg="bg-sky-500/10" label="Verify Phone" description="Add for 2FA & alerts" badge="Add" />
        </SettingSection>
        <SettingSection title="Personal Details">
          <SettingRow icon={HomeIcon} iconColor="text-indigo-400" iconBg="bg-indigo-500/10" label="Primary Address" description="State & Country" />
          <SettingRow icon={Briefcase} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Occupation" description="Your profession" />
        </SettingSection>
      </div>
    </motion.div>
  );
};

const SecurityPage = ({ onBack }) => {
  const [twoFA, setTwoFA] = useState(false);
  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <PageHeader title="Privacy & Security" subtitle="Protect your account" onBack={onBack} />
      <div className="space-y-6">
        <SettingSection title="Authentication">
          <SettingRow icon={Lock} iconColor="text-purple-400" iconBg="bg-purple-500/10" label="Change Password" description="Update your login password" />
          <SettingRow
            icon={ShieldCheck}
            iconColor="text-emerald-400"
            iconBg="bg-emerald-500/10"
            label="Two-Factor Authentication"
            description={twoFA ? "Enabled — your account is secure" : "Disabled — enable for extra security"}
            badge={twoFA ? "On" : "Off"}
            trailing={<Toggle enabled={twoFA} onChange={setTwoFA} />}
          />
        </SettingSection>

        {twoFA && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="space-y-2">
            <SettingSection title="2FA Methods">
              <SettingRow icon={Smartphone} iconColor="text-sky-400" iconBg="bg-sky-500/10" label="SMS Verification" description="Send OTP to your phone" />
              <SettingRow icon={QrCode} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="Authenticator App" description="Scan QR with Google / Authy" badge="Recommended" />
            </SettingSection>
          </motion.div>
        )}

        <SettingSection title="Sessions">
          <SettingRow icon={Activity} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Active Sessions" description="View & revoke logins" />
        </SettingSection>

        <SettingSection title="Privacy Controls">
          <SettingRow icon={Eye} iconColor="text-slate-400" iconBg="bg-slate-500/10" label="Profile Visibility" description="Who can see your profile" value="Private" />
          <SettingRow icon={Database} iconColor="text-rose-400" iconBg="bg-rose-500/10" label="Data Sharing" description="Manage app data permissions" />
        </SettingSection>
      </div>
    </motion.div>
  );
};

const FinancialSettingsPage = ({ onBack }) => {
  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <PageHeader title="Financial Settings" subtitle="Configure money preferences" onBack={onBack} />
      <div className="space-y-6">
        <SettingSection title="Region">
          <SettingRow icon={Globe} iconColor="text-sky-400" iconBg="bg-sky-500/10" label="Currency & Region" description="Base currency for all transactions" value="INR (₹)" />
        </SettingSection>

        <SettingSection title="Bank Accounts">
          <SettingRow icon={CreditCard} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Add Account" description="Link a new bank or card" />
          <SettingRow icon={Trash2} iconColor="text-rose-400" iconBg="bg-rose-500/10" label="Remove Account" description="Unlink an existing account" danger />
          <SettingRow icon={RefreshCw} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Sync Status" description="Last synced: Just now" />
        </SettingSection>

        <SettingSection title="Budget & Categories">
          <SettingRow icon={Tag} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="Expense Categories" description="Customize spending categories" />
          <SettingRow icon={Target} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Monthly Limit" description="Set your monthly spending cap" />
          <SettingRow icon={Bell} iconColor="text-rose-400" iconBg="bg-rose-500/10" label="Budget Alerts" description="Get notified before you overspend" />
        </SettingSection>
      </div>
    </motion.div>
  );
};

const NotificationsPage = ({ onBack }) => {
  const prefs = loadPrefs();
  const [emailN, setEmailN] = useState(prefs.notif_email !== false);
  const [pushN, setPushN] = useState(prefs.notif_push !== false);
  const [smsN, setSmsN] = useState(prefs.notif_sms === true);
  const toggle = (key, setter) => (val) => { setter(val); savePref(key, val); };
  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <PageHeader title="Notifications" subtitle="Stay informed, not overwhelmed" onBack={onBack} />
      <div className="space-y-6">
        <SettingSection title="Channels">
          <SettingRow icon={Mail} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Email Preferences" description={emailN ? "Receiving email updates" : "Email notifications silenced"} trailing={<Toggle enabled={emailN} onChange={toggle("notif_email", setEmailN)} />} />
          <SettingRow icon={Smartphone} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Push Notifications" description={pushN ? "Enabled on this device" : "Silent mode active"} trailing={<Toggle enabled={pushN} onChange={toggle("notif_push", setPushN)} />} />
          <SettingRow icon={MessageSquare} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="SMS Alerts" description={smsN ? "Receiving SMS for critical events" : "No SMS alerts"} trailing={<Toggle enabled={smsN} onChange={toggle("notif_sms", setSmsN)} />} />
        </SettingSection>
      </div>
    </motion.div>
  );
};

const AppearancePage = ({ onBack, currentTheme, onThemeChange }) => {
  const themeLabel = currentTheme === "dark" ? "Dark" : "Light";
  const [accent, setAccent] = useState(() => loadPrefs().accent || "indigo");
  const accents = [
    { name: "indigo", color: "#6366f1" },
    { name: "violet", color: "#8b5cf6" },
    { name: "emerald", color: "#10b981" },
    { name: "rose", color: "#f43f5e" },
    { name: "amber", color: "#f59e0b" },
    { name: "sky", color: "#38bdf8" },
  ];
  const handleTheme = (t) => {
    const newTheme = t === "Dark" ? "dark" : "light";
    if (newTheme !== currentTheme && onThemeChange) onThemeChange(newTheme);
  };
  const handleAccent = (name) => {
    setAccent(name);
    savePref("accent", name);
  };
  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <PageHeader title="Appearance" subtitle="Make it yours" onBack={onBack} />
      <div className="space-y-6">
        <SettingSection title="Theme">
          <div className="flex bg-black/30 p-1.5 rounded-2xl border border-white/5">
            {["Dark", "Light"].map((t) => (
              <button key={t} onClick={() => handleTheme(t)} className={`flex-1 py-2.5 rounded-xl text-xs font-bold transition-all ${themeLabel === t ? "bg-white/10 text-white shadow" : "text-slate-500 hover:text-slate-300"}`}>
                {t === "Dark" ? "🌑" : "☀️"} {t}
              </button>
            ))}
          </div>
        </SettingSection>

        <SettingSection title="Accent Color">
          <div className="flex gap-3 px-2 py-3">
            {accents.map((a) => (
              <button key={a.name} onClick={() => handleAccent(a.name)} className="relative w-10 h-10 rounded-2xl transition-transform hover:scale-110">
                <div className="w-full h-full rounded-2xl" style={{ backgroundColor: a.color }} />
                {accent === a.name && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <CheckCircle className="w-5 h-5 text-white drop-shadow-lg" />
                  </div>
                )}
              </button>
            ))}
          </div>
        </SettingSection>

        <SettingSection title="Layout">
          <SettingRow icon={Layers} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Layout Preferences" description="Compact or Comfortable" value="Default" />
        </SettingSection>
      </div>
    </motion.div>
  );
};

const AIFeaturesPage = ({ onBack }) => {
  const prefs = loadPrefs();
  const [autoCat, setAutoCat] = useState(prefs.ai_autocat !== false);
  const [insights, setInsights] = useState(prefs.ai_insights !== false);
  const [predictive, setPredictive] = useState(prefs.ai_predictive === true);
  const toggle = (key, setter) => (val) => { setter(val); savePref(key, val); };
  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <PageHeader title="Smart Features (AI)" subtitle="Let Tora work for you" onBack={onBack} />
      <div className="space-y-2">
        <div className="p-5 mb-6 rounded-3xl bg-gradient-to-br from-violet-500/10 to-blue-500/5 border border-violet-500/20">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-violet-500/20 rounded-xl"><Bot className="w-5 h-5 text-violet-400" /></div>
            <p className="text-sm font-black text-white">Tora AI Engine</p>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed">Tora learns from your spending patterns to provide personalized insights and automation.</p>
        </div>
        <SettingSection title="Features">
          <SettingRow icon={Tag} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Auto Categorization" description="Let AI sort your transactions" trailing={<Toggle enabled={autoCat} onChange={toggle("ai_autocat", setAutoCat)} />} />
          <SettingRow icon={TrendingUp} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Smart Insights" description="Weekly AI-powered spending reports" trailing={<Toggle enabled={insights} onChange={toggle("ai_insights", setInsights)} />} />
          <SettingRow icon={Bell} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Predictive Alerts" description="Know before you overspend" trailing={<Toggle enabled={predictive} onChange={toggle("ai_predictive", setPredictive)} />} badge={!predictive ? "Beta" : undefined} />
        </SettingSection>
      </div>
    </motion.div>
  );
};

const DataManagementPage = ({ onBack, triggerConfirm, transactions, onDeleteAll, showToast, onNavigateImport }) => (
  <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
    <PageHeader title="Data Management" subtitle="Your data, your control" onBack={onBack} />
    <div className="space-y-6">
      <SettingSection title="Import & Export">
        <SettingRow
          icon={Download} iconColor="text-emerald-400" iconBg="bg-emerald-500/10"
          label="Export Data" description={`Download ${transactions?.length || 0} transactions as CSV`}
          onClick={() => {
            if (!transactions?.length) { showToast?.("No transactions to export", "error"); return; }
            downloadCSV(transactions);
            showToast?.("CSV downloaded!", "success");
          }}
        />
        <SettingRow icon={Upload} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Import Statements" description="Upload bank or card statements" onClick={onNavigateImport} />
      </SettingSection>

      <SettingSection title="Danger Zone">
        <div className="p-4 rounded-2xl bg-rose-500/5 border border-rose-500/20 space-y-2">
          <p className="text-[10px] text-rose-400 font-black uppercase tracking-widest mb-3">Irreversible Actions</p>
          <SettingRow
            icon={Trash2} iconColor="text-rose-400" iconBg="bg-rose-500/10"
            label="Delete All Transactions" description="Permanently erase transaction history" danger
            onClick={() => triggerConfirm?.(`Delete ALL ${transactions?.length || 0} transactions? This cannot be undone.`, onDeleteAll)}
          />
        </div>
      </SettingSection>
    </div>
  </motion.div>
);

const TIER_CONFIG = {
  free:       { label: "Free Plan",       color: "from-slate-800/80 to-slate-900/60",   border: "border-slate-500/20",   glow: "bg-slate-500/10",    icon: "text-slate-400",  badge: "text-slate-400",   features: ["20 Transactions/mo", "Basic Insights", "Community Support"] },
  pro:        { label: "Pro Member",      color: "from-indigo-900/50 to-violet-900/30", border: "border-indigo-500/20", glow: "bg-indigo-500/10", icon: "text-indigo-400", badge: "text-indigo-400", features: ["Unlimited Transactions", "AI Insights", "Priority Support"] },
  enterprise: { label: "Enterprise",      color: "from-amber-900/50 to-orange-900/30",  border: "border-amber-500/20",  glow: "bg-amber-500/10",   icon: "text-amber-400",  badge: "text-amber-400",  features: ["Unlimited Everything", "Custom Integrations", "Dedicated Support"] },
};

const SubscriptionPage = ({ onBack, tier = "free" }) => {
  const cfg = TIER_CONFIG[tier] || TIER_CONFIG.free;
  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <PageHeader title="Subscription & Billing" subtitle="Manage your plan" onBack={onBack} />
      <div className="space-y-6">
        <div className={`p-6 rounded-3xl bg-gradient-to-br ${cfg.color} border ${cfg.border} relative overflow-hidden`}>
          <div className={`absolute top-0 right-0 w-48 h-48 ${cfg.glow} blur-[60px] rounded-full pointer-events-none`} />
          <div className="relative z-10">
            <div className="flex items-center gap-3 mb-3">
              <div className={`p-2 bg-white/10 rounded-xl`}><Crown className={`w-5 h-5 ${cfg.icon}`} /></div>
              <div>
                <p className="text-xs font-black text-white uppercase tracking-wider">{cfg.label}</p>
                <p className={`text-[10px] ${cfg.badge} font-bold`}>
                  {tier === "free" ? "Upgrade for full access" : "Active · Thank you for subscribing!"}
                </p>
              </div>
            </div>
            <div className="flex gap-2 mt-4 flex-wrap">
              {cfg.features.map(f => (
                <span key={f} className="px-2 py-1 rounded-full bg-white/5 border border-white/10 text-[9px] font-bold text-slate-400 uppercase tracking-wider">{f}</span>
              ))}
            </div>
          </div>
        </div>

        <SettingSection title="Plan">
          {tier === "free" && (
            <SettingRow icon={Star} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Upgrade to Pro" description="Unlock AI, unlimited transactions & more" badge="Upgrade" />
          )}
          {tier !== "free" && (
            <SettingRow icon={Star} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Upgrade Plan" description="Unlock advanced features" badge="New" />
          )}
          <SettingRow icon={FileText} iconColor="text-slate-400" iconBg="bg-slate-500/10" label="Billing History" description="View past invoices & receipts" />
          <SettingRow icon={Package} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Redeem Coupon" description="Apply a promo or referral code" />
        </SettingSection>
      </div>
    </motion.div>
  );
};

const HelpSupportPage = ({ onBack }) => (
  <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
    <PageHeader title="Help & Support" subtitle="We're here for you" onBack={onBack} />
    <div className="space-y-6">
      <SettingSection title="Resources">
        <SettingRow icon={LifeBuoy} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Help Center" description="Browse guides and documentation" />
        <SettingRow icon={HelpCircle} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="FAQs" description="Frequently asked questions" />
      </SettingSection>
      <SettingSection title="Contact">
        <SettingRow icon={MessageSquare} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Contact Support" description="Chat with our team" />
        <SettingRow icon={Ticket} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Raise a Ticket" description="Report a bug or issue" />
      </SettingSection>
    </div>
  </motion.div>
);

const AboutPage = ({ onBack }) => (
  <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
    <PageHeader title="About" subtitle="Spendsy — Know your money" onBack={onBack} />
    <div className="space-y-6">
      <div className="text-center py-8">
        <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center mx-auto mb-4 shadow-2xl shadow-indigo-900/40">
          <span className="text-3xl">⚡</span>
        </div>
        <p className="text-xl font-black text-white">Spendsy</p>
        <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mt-1">Personal Finance OS</p>
      </div>
      <SettingSection title="App Info">
        <SettingRow icon={Info} iconColor="text-slate-400" iconBg="bg-slate-500/10" label="App Version" description="Current build" value="v2.4.0-stable" trailing={<span />} />
        <SettingRow icon={FileText} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Terms & Conditions" description="User agreement" />
        <SettingRow icon={Shield} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Privacy Policy" description="How we use your data" value="v1.4 Jan 2026" />
      </SettingSection>
    </div>
  </motion.div>
);

// ─── Main Settings Page ───────────────────────────────────────────────────────

const SECTIONS = [
  {
    key: "personal",
    icon: User, label: "Personal Information",
    description: "Name, email, phone, photo",
    iconColor: "text-blue-400", iconBg: "bg-blue-500/10",
  },
  {
    key: "security",
    icon: Shield, label: "Privacy & Security",
    description: "Password, 2FA, sessions",
    iconColor: "text-emerald-400", iconBg: "bg-emerald-500/10",
  },
  {
    key: "financial",
    icon: Coins, label: "Financial Settings",
    description: "Currency, accounts, budget",
    iconColor: "text-amber-400", iconBg: "bg-amber-500/10",
  },
  {
    key: "notifications",
    icon: Bell, label: "Notifications",
    description: "Email, push, SMS",
    iconColor: "text-violet-400", iconBg: "bg-violet-500/10",
  },
  {
    key: "appearance",
    icon: Palette, label: "Appearance",
    description: "Theme, colors, layout",
    iconColor: "text-pink-400", iconBg: "bg-pink-500/10",
  },
  {
    key: "ai",
    icon: Bot, label: "Smart Features",
    description: "Auto-categorize, AI insights",
    iconColor: "text-indigo-400", iconBg: "bg-indigo-500/10",
    badge: "AI",
  },
  {
    key: "data",
    icon: Database, label: "Data Management",
    description: "Export, import, backup, danger zone",
    iconColor: "text-slate-400", iconBg: "bg-slate-500/10",
  },
  {
    key: "subscription",
    icon: Crown, label: "Subscription & Billing",
    description: "Plan, invoices, coupons",
    iconColor: "text-amber-400", iconBg: "bg-amber-500/10",
  },
  {
    key: "help",
    icon: LifeBuoy, label: "Help & Support",
    description: "FAQs, contact, raise ticket",
    iconColor: "text-sky-400", iconBg: "bg-sky-500/10",
  },
  {
    key: "about",
    icon: Info, label: "About",
    description: "Version, terms, privacy policy",
    iconColor: "text-slate-400", iconBg: "bg-slate-500/10",
  },
];

const SettingsPage = ({ user, settings = {}, onUpdateSettings, onBack, onSignOut, triggerConfirm, theme: currentTheme, onThemeChange, transactions, onDeleteAll, showToast, onNavigateImport }) => {
  const [currentSection, setCurrentSection] = useState(null);
  const [search, setSearch] = useState("");

  const filteredSections = useMemo(() =>
    SECTIONS.filter(s =>
      s.label.toLowerCase().includes(search.toLowerCase()) ||
      s.description.toLowerCase().includes(search.toLowerCase())
    ), [search]);

  const goBack = () => setCurrentSection(null);

  const renderSection = () => {
    switch (currentSection) {
      case "personal":     return <PersonalInfoPage user={user} onBack={goBack} />;
      case "security":     return <SecurityPage onBack={goBack} />;
      case "financial":    return <FinancialSettingsPage onBack={goBack} />;
      case "notifications":return <NotificationsPage onBack={goBack} />;
      case "appearance":   return <AppearancePage onBack={goBack} currentTheme={currentTheme} onThemeChange={onThemeChange} />;
      case "ai":           return <AIFeaturesPage onBack={goBack} />;
      case "data":         return <DataManagementPage onBack={goBack} triggerConfirm={triggerConfirm} transactions={transactions} onDeleteAll={onDeleteAll} showToast={showToast} onNavigateImport={onNavigateImport} />;
      case "subscription": return <SubscriptionPage onBack={goBack} tier={user?.tier || "free"} />;
      case "help":         return <HelpSupportPage onBack={goBack} />;
      case "about":        return <AboutPage onBack={goBack} />;
      default: return null;
    }
  };

  return (
    <div className="space-y-0 pb-32">
      <AnimatePresence mode="wait">
        {currentSection ? (
          <motion.div key={currentSection} variants={pageVariants} initial="initial" animate="animate" exit="exit">
            {renderSection()}
          </motion.div>
        ) : (
          <motion.div key="main" variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between pb-5 border-b border-white/5">
              <div className="flex items-center gap-4">
                <motion.button
                  whileHover={{ scale: 1.05, x: -2 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={onBack}
                  className="p-3 bg-white/5 rounded-2xl hover:bg-white/10 transition-colors shadow-lg"
                >
                  <ChevronLeft className="w-5 h-5 text-white" />
                </motion.button>
                <div>
                  <h1 className="text-2xl font-black text-white tracking-tight">Settings</h1>
                  <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest mt-0.5">Configure your experience</p>
                </div>
              </div>
            </div>

            {/* Search */}
            <div className="relative group">
              <div className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-600 group-focus-within:text-indigo-400 transition-colors">
                <Search className="w-5 h-5" />
              </div>
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search settings..."
                className="w-full pl-14 pr-5 py-4 bg-white/5 border border-white/10 rounded-2xl text-white text-sm font-medium outline-none focus:border-indigo-500/50 focus:bg-white/8 transition-all placeholder:text-slate-600"
              />
              {search && (
                <button onClick={() => setSearch("")} className="absolute right-5 top-1/2 -translate-y-1/2 text-slate-600 hover:text-white transition-colors">
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Sections */}
            <div className="space-y-2">
              {filteredSections.length === 0 ? (
                <div className="py-16 text-center">
                  <Search className="w-8 h-8 text-slate-700 mx-auto mb-3" />
                  <p className="text-slate-500 text-sm font-bold">No settings found for "{search}"</p>
                </div>
              ) : (
                filteredSections.map((s) => (
                  <motion.button
                    key={s.key}
                    onClick={() => setCurrentSection(s.key)}
                    whileHover={{ x: 6, backgroundColor: "rgba(255,255,255,0.07)" }}
                    whileTap={{ scale: 0.99 }}
                    className="w-full flex items-center gap-4 px-5 py-4 rounded-2xl border border-white/5 transition-all group text-left"
                    style={{ background: "rgba(255,255,255,0.03)" }}
                  >
                    <div className={`p-3 ${s.iconBg} ${s.iconColor} rounded-2xl shrink-0 group-hover:scale-110 transition-transform shadow-inner`}>
                      <s.icon className="w-6 h-6" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-black text-white leading-tight">{s.label}</p>
                      <p className="text-[11px] text-slate-500 mt-0.5 truncate">{s.description}</p>
                    </div>
                    {s.badge && (
                      <span className="px-2 py-0.5 rounded-full bg-indigo-500/20 border border-indigo-500/30 text-[9px] font-bold text-indigo-400 uppercase tracking-wider shrink-0">{s.badge}</span>
                    )}
                    <ChevronRight className="w-5 h-5 text-slate-700 group-hover:text-slate-400 transition-colors shrink-0" />
                  </motion.button>
                ))
              )}
            </div>

            {/* Logout */}
            <motion.button
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.99 }}
              onClick={() => triggerConfirm?.("Are you sure you want to sign out?", onSignOut)}
              className="w-full flex items-center gap-4 px-5 py-5 rounded-2xl bg-rose-500/5 hover:bg-rose-500/10 border border-rose-500/10 hover:border-rose-500/25 transition-all group mt-4"
            >
              <div className="p-3 bg-rose-500/10 rounded-2xl text-rose-500 shrink-0 group-hover:scale-110 transition-transform">
                <LogOut className="w-6 h-6" />
              </div>
              <div className="flex-1 text-left">
                <p className="text-sm font-black text-rose-400">Sign Out of Spendsy</p>
                <p className="text-[11px] text-rose-500/50 mt-0.5">End your current session</p>
              </div>
              <ChevronRight className="w-5 h-5 text-rose-500/40 group-hover:text-rose-400 transition-colors shrink-0" />
            </motion.button>

            {/* Footer */}
            <p className="text-center text-[10px] font-black text-slate-800 uppercase tracking-widest pt-4">Spendsy v2.4.0-stable</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default SettingsPage;
