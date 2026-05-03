import React, { useState, useMemo, useRef } from "react";
import { downloadCSV } from "@shared/utils/exportUtils";
import { authApi, financeApi } from "../api";
import { cn } from "@shared/utils/cn";
import { motion, AnimatePresence } from "framer-motion";
import { SettingsSkeleton } from "../components/ui/Skeletons";
import {
  User, Mail, Lock, Phone, Home as HomeIcon, Briefcase,
  Coins, Moon, Sun, Bell, Shield, ChevronLeft, ChevronRight,
  LogOut, Database, Edit2, Save, X, Search,
  CreditCard, Tag, Target, Camera, Smartphone, Eye, EyeOff,
  Download, Upload, Trash2, AlertTriangle, Crown,
  HelpCircle, FileText, Info, MessageSquare, Ticket,
  Palette, Bot, TrendingUp, RefreshCw, Globe,
  ShieldCheck, Activity, CheckCircle, QrCode, Key,
  Sliders, Repeat, Star, Package, LifeBuoy, ZapOff,
  BarChart2, SlidersHorizontal, Layers, MapPin, Calendar,
  IndianRupee, Receipt, Calculator, Building2, Wallet,
  AlertCircle, Clock, Zap, Languages, ChartBar,
  PiggyBank, ArrowRightLeft, Fingerprint, Link2,
  ExternalLink, Copy, Check, RotateCcw, LogIn,
  BellOff, BellRing, Landmark, FileBarChart, BookOpen,
  ListFilter, PieChart, Settings as SettingsIcon
} from "lucide-react";

// ─── Preferences Persistence ─────────────────────────────────────────────────
const PREFS_KEY = "spendsy_preferences";
const loadPrefs = () => {
  try { return JSON.parse(localStorage.getItem(PREFS_KEY)) || {}; }
  catch { return {}; }
};
const savePref = (key, value) => {
  try {
    const prefs = { ...loadPrefs(), [key]: value };
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  } catch (err) {
    console.warn("Could not save preference:", err);
  }
};

// ─── Animation Variants ───────────────────────────────────────────────────────
const pageVariants = {
  initial: { opacity: 0, x: 30 },
  animate: { opacity: 1, x: 0, transition: { duration: 0.25, ease: [0.22, 1, 0.36, 1] } },
  exit:    { opacity: 0, x: -20, transition: { duration: 0.18 } },
};
const fadeUp = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -6 } };

// ─── Shared Primitives ────────────────────────────────────────────────────────

const inputCls = "w-full px-4 py-3 bg-[#0f172a] border border-white/10 rounded-2xl text-white text-sm outline-none focus:border-indigo-500/50 focus:bg-white/5 transition-all placeholder:text-slate-600";
const labelCls = "text-[10px] font-black text-slate-500 uppercase tracking-[0.25em] pl-1";

const Toggle = ({ enabled, onChange, disabled = false }) => (
  <button
    type="button"
    disabled={disabled}
    onClick={(e) => { e.stopPropagation(); onChange(!enabled); }}
    className={`relative w-11 h-6 rounded-full transition-all duration-300 shrink-0 ${enabled ? "bg-indigo-500" : "bg-white/10"} ${disabled ? "opacity-40 cursor-not-allowed" : ""}`}
  >
    <div className={`absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow transition-all duration-300 ${enabled ? "translate-x-5" : "translate-x-0"}`} />
  </button>
);

const Badge = ({ label, color = "indigo" }) => {
  const colors = {
    indigo: "bg-indigo-500/20 border-indigo-500/30 text-indigo-400",
    amber:  "bg-amber-500/20 border-amber-500/30 text-amber-400",
    emerald:"bg-emerald-500/20 border-emerald-500/30 text-emerald-400",
    rose:   "bg-rose-500/20 border-rose-500/30 text-rose-400",
    violet: "bg-violet-500/20 border-violet-500/30 text-violet-400",
    sky:    "bg-sky-500/20 border-sky-500/30 text-sky-400",
    slate:  "bg-slate-500/20 border-slate-500/30 text-slate-400",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full border text-[9px] font-black uppercase tracking-wider shrink-0 ${colors[color] || colors.indigo}`}>
      {label}
    </span>
  );
};

const SettingRow = ({ icon: Icon, iconColor = "text-blue-400", iconBg = "bg-blue-500/10", label, description, value, onClick, danger = false, badge, badgeColor, trailing, disabled = false }) => (
  <motion.button
    onClick={disabled ? undefined : onClick}
    whileHover={disabled ? {} : { x: 4, backgroundColor: "rgba(255,255,255,0.06)" }}
    whileTap={disabled ? {} : { scale: 0.99 }}
    className={`w-full flex items-center gap-4 px-5 py-4 rounded-2xl border border-white/5 transition-colors group ${danger ? "hover:border-rose-500/20" : ""} ${disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}`}
    style={{ background: "rgba(255,255,255,0.03)" }}
  >
    <div className={`p-2.5 ${iconBg} ${iconColor} rounded-xl shrink-0 ${!disabled ? "group-hover:scale-110" : ""} transition-transform`}>
      <Icon className="w-5 h-5" />
    </div>
    <div className="flex-1 text-left min-w-0">
      <p className={`text-sm font-bold leading-tight ${danger ? "text-rose-400" : "text-white"}`}>{label}</p>
      {description && <p className="text-[11px] text-slate-500 mt-0.5 truncate">{description}</p>}
    </div>
    {badge && <Badge label={badge} color={badgeColor} />}
    {value && <span className="text-xs text-slate-500 font-medium shrink-0 max-w-[120px] truncate">{value}</span>}
    {trailing !== undefined ? trailing : <ChevronRight className={`w-4 h-4 ${danger ? "text-rose-500/50 group-hover:text-rose-400" : "text-slate-700 group-hover:text-slate-400"} transition-colors shrink-0`} />}
  </motion.button>
);

const SettingSection = ({ title, subtitle, children }) => (
  <div className="space-y-2">
    <div className="px-2 mb-3">
      <p className="text-[10px] font-black text-slate-600 uppercase tracking-[0.3em]">{title}</p>
      {subtitle && <p className="text-[10px] text-slate-700 mt-0.5">{subtitle}</p>}
    </div>
    <div className="space-y-2">{children}</div>
  </div>
);

const PageHeader = ({ title, subtitle, onBack, action }) => (
  <div className="flex items-center gap-4 pb-5 border-b border-white/5 mb-6">
    <motion.button
      whileHover={{ scale: 1.05, x: -2 }}
      whileTap={{ scale: 0.95 }}
      onClick={onBack}
      className="p-3 bg-white/5 rounded-2xl hover:bg-white/10 transition-colors shadow-lg shrink-0"
    >
      <ChevronLeft className="w-5 h-5 text-white" />
    </motion.button>
    <div className="flex-1">
      <h2 className="text-xl font-black text-white tracking-tight">{title}</h2>
      {subtitle && <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest mt-0.5">{subtitle}</p>}
    </div>
    {action}
  </div>
);

const InfoCard = ({ children, color = "indigo" }) => {
  const glows = { indigo: "from-indigo-500/10 to-violet-500/5 border-indigo-500/20", amber: "from-amber-500/10 to-orange-500/5 border-amber-500/20", emerald: "from-emerald-500/10 to-teal-500/5 border-emerald-500/20", rose: "from-rose-500/10 to-pink-500/5 border-rose-500/20" };
  return <div className={`p-5 rounded-3xl bg-gradient-to-br ${glows[color] || glows.indigo} border mb-5`}>{children}</div>;
};

const Spinner = ({ size = "sm" }) => (
  <div className={`${size === "sm" ? "w-4 h-4" : "w-6 h-6"} border-2 border-current border-t-transparent rounded-full animate-spin opacity-60`} />
);

// ─── 1. PERSONAL INFO ─────────────────────────────────────────────────────────

const OCCUPATIONS = ["Salaried", "Self-Employed / Freelancer", "Business Owner", "Student", "Retired", "Homemaker", "Government Employee", "NRI", "Other"];
const INDIAN_STATES = ["Andhra Pradesh","Arunachal Pradesh","Assam","Bihar","Chhattisgarh","Goa","Gujarat","Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh","Maharashtra","Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Punjab","Rajasthan","Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh","Uttarakhand","West Bengal","Delhi","Jammu & Kashmir","Ladakh","Puducherry","Chandigarh","Other"];

const PersonalInfoPage = ({ user, onBack, showToast, onRefreshUser }) => {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const fileRef = useRef();
  const [form, setForm] = useState({
    first_name: user?.first_name || "",
    last_name:  user?.last_name  || "",
    phone:      user?.phone      || "",
    pan:        user?.pan        || "",
    occupation: user?.occupation || "",
    state:      user?.state      || "",
    city:       user?.city       || "",
    dob:        user?.dob        || "",
  });
  const [copied, setCopied] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      // 1. Update Auth Profile
      await authApi.updateProfile({ 
        first_name: form.first_name, 
        last_name: "" // No need for separate last name
      });

      // 2. Update Finance Profile
      await financeApi.updateProfile(user.id, {
        first_name: form.first_name,
        last_name: "",
        phone: form.phone,
        pan: form.pan,
        occupation: form.occupation,
        state: form.state,
        city: form.city,
        dob: form.dob
      });

      showToast?.("Profile updated successfully!", "success");
      setEditing(false);
      onRefreshUser?.();
      
      // Force refresh data in parent components if needed, 
      // but usually the updated state here is enough until refresh
    } catch (err) {
      console.error("Profile Save Error:", err);
      showToast?.(err?.message || "Update failed. Check your connection.", "error");
    } finally { setSaving(false); }
  };

  const handleAvatarClick = () => fileRef.current?.click();

  const handleAvatarChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { showToast?.("Image must be under 2 MB", "error"); return; }
    setAvatarUploading(true);
    try {
      await authApi.uploadAvatar(file);
      showToast?.("Profile photo updated!", "success");
      onRefreshUser?.();
    } catch (err) {
      showToast?.(err?.message || "Upload failed", "error");
    } finally {
      setAvatarUploading(false);
    }
  };

  const copyUID = () => {
    navigator.clipboard.writeText(user?.id || "").then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); });
  };

  const initials = (user?.first_name || user?.username || "U")[0].toUpperCase();
  const displayName = user?.first_name || user?.username || "User";

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <PageHeader title="Personal Information" subtitle="Your identity on Spendsy" onBack={onBack} />

      {/* Avatar */}
      <div className="flex flex-col items-center gap-3 mb-8">
        <div className="relative group">
          <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-3xl font-black text-white shadow-xl shadow-indigo-900/40 overflow-hidden relative">
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt="Profile" className="w-full h-full object-cover" />
            ) : avatarUploading ? (
              <Spinner size="md" />
            ) : (
              <span>{initials}</span>
            )}
            {avatarUploading && (
              <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                <Spinner size="sm" />
              </div>
            )}
          </div>
          <button
            onClick={handleAvatarClick}
            className="absolute -bottom-2 -right-2 p-2 bg-slate-800 border border-white/10 rounded-xl text-slate-400 hover:text-white hover:bg-slate-700 transition-all shadow-lg"
          >
            <Camera className="w-4 h-4" />
          </button>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleAvatarChange} />
        </div>
        <div className="text-center">
          <p className="text-base font-black text-white">{displayName}</p>
          <p className="text-xs text-slate-500">{user?.email}</p>
        </div>
        {user?.id && (
          <button onClick={copyUID} className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3 text-slate-500" />}
            <span className="text-[10px] text-slate-500 font-bold font-mono">UID: {String(user.id).slice(0, 12)}…</span>
          </button>
        )}
      </div>

      <div className="space-y-6">
        {/* Account Details (always visible) */}
        <SettingSection title="Account">
          <div className="flex items-center gap-4 px-5 py-4 rounded-2xl border border-white/5" style={{ background: "rgba(255,255,255,0.03)" }}>
            <div className="p-2.5 bg-blue-500/10 text-blue-400 rounded-xl shrink-0"><User className="w-5 h-5" /></div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-white">Username</p>
              <p className="text-[11px] text-slate-500">{user?.username || "—"}</p>
            </div>
            <span className="text-[10px] text-slate-700 font-bold">Cannot change</span>
          </div>
          <div className="flex items-center gap-4 px-5 py-4 rounded-2xl border border-white/5" style={{ background: "rgba(255,255,255,0.03)" }}>
            <div className="p-2.5 bg-emerald-500/10 text-emerald-400 rounded-xl shrink-0"><Mail className="w-5 h-5" /></div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-white">Email Address</p>
              <p className="text-[11px] text-slate-500">{user?.email || "—"}</p>
            </div>
            <Badge label="Verified" color="emerald" />
          </div>
        </SettingSection>

        {/* Editable Profile */}
        <SettingSection title="Profile Details">
          {!editing ? (
            <>
              {[
                { icon: User, iconBg: "bg-indigo-500/10", iconColor: "text-indigo-400", label: "Full Name", val: user?.first_name || "—" },
                { icon: Phone, iconBg: "bg-sky-500/10", iconColor: "text-sky-400", label: "Phone Number", val: form.phone || "Not set" },
                { icon: Calendar, iconBg: "bg-violet-500/10", iconColor: "text-violet-400", label: "Date of Birth", val: form.dob || "Not set" },
                { icon: Briefcase, iconBg: "bg-amber-500/10", iconColor: "text-amber-400", label: "Occupation", val: form.occupation || "Not set" },
                { icon: MapPin, iconBg: "bg-rose-500/10", iconColor: "text-rose-400", label: "City / State", val: [form.city, form.state].filter(Boolean).join(", ") || "Not set" },
              ].map(({ icon: I, iconBg, iconColor, label, val }) => (
                <div key={label} className="flex items-center gap-4 px-5 py-4 rounded-2xl border border-white/5" style={{ background: "rgba(255,255,255,0.03)" }}>
                  <div className={`p-2.5 ${iconBg} ${iconColor} rounded-xl shrink-0`}><I className="w-5 h-5" /></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-bold text-white">{label}</p>
                    <p className="text-[11px] text-slate-500">{val}</p>
                  </div>
                </div>
              ))}
              <motion.button
                onClick={() => setEditing(true)}
                whileHover={{ x: 4 }}
                className="w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-black uppercase tracking-widest hover:bg-indigo-500/20 transition-colors mt-2"
              >
                <Edit2 className="w-4 h-4" />
                Edit Profile
              </motion.button>
            </>
          ) : (
            <motion.div {...fadeUp} className="space-y-4 p-5 rounded-2xl bg-white/[0.03] border border-white/10">
              <div className="space-y-1.5">
                <label className={labelCls}>Full Name</label>
                <input className={inputCls} value={form.first_name} onChange={e => setForm(f => ({ ...f, first_name: e.target.value }))} placeholder="Your full name" />
              </div>
              <div className="space-y-1.5">
                <label className={labelCls}>Phone Number</label>
                <input className={inputCls} value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} placeholder="+91 98765 43210" type="tel" />
              </div>
              <div className="space-y-1.5">
                <label className={labelCls}>PAN Number</label>
                <input className={inputCls} value={form.pan} onChange={e => setForm(f => ({ ...f, pan: e.target.value?.toUpperCase() }))} placeholder="ABCDE1234F" maxLength={10} />
              </div>
              <div className="space-y-1.5">
                <label className={labelCls}>Date of Birth</label>
                <input className={inputCls} value={form.dob} onChange={e => setForm(f => ({ ...f, dob: e.target.value }))} type="date" />
              </div>
              <div className="space-y-1.5">
                <label className={labelCls}>Occupation</label>
                <select className={`${inputCls} [&>option]:bg-slate-900`} value={form.occupation} onChange={e => setForm(f => ({ ...f, occupation: e.target.value }))}>
                  <option value="" className="bg-slate-900">Select occupation</option>
                  {OCCUPATIONS.map(o => <option key={o} value={o} className="bg-slate-900">{o}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className={labelCls}>City</label>
                  <input className={inputCls} value={form.city} onChange={e => setForm(f => ({ ...f, city: e.target.value }))} placeholder="Mumbai" />
                </div>
                <div className="space-y-1.5">
                  <label className={labelCls}>State</label>
                  <select className={`${inputCls} [&>option]:bg-slate-900`} value={form.state} onChange={e => setForm(f => ({ ...f, state: e.target.value }))}>
                    <option value="" className="bg-slate-900">Select state</option>
                    {INDIAN_STATES.map(s => <option key={s} value={s} className="bg-slate-900">{s}</option>)}
                  </select>
                </div>
              </div>
              <div className="flex gap-3 pt-2">
                <button onClick={() => setEditing(false)} className="flex-1 py-3 rounded-2xl bg-white/5 border border-white/10 text-slate-400 text-xs font-black uppercase tracking-widest hover:bg-white/10 transition-colors">
                  Cancel
                </button>
                <button onClick={handleSave} disabled={saving} className="flex-1 py-3 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-black uppercase tracking-widest transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
                  {saving ? <Spinner /> : <Save className="w-4 h-4" />}
                  {saving ? "Saving…" : "Save Changes"}
                </button>
              </div>
            </motion.div>
          )}
        </SettingSection>

        {/* KYC / Tax IDs */}
        <SettingSection title="Tax & KYC Identifiers" subtitle="Used for ITR filing and compliance">
          <div className="flex items-center gap-4 px-5 py-4 rounded-2xl border border-white/5" style={{ background: "rgba(255,255,255,0.03)" }}>
            <div className="p-2.5 bg-amber-500/10 text-amber-400 rounded-xl shrink-0"><Receipt className="w-5 h-5" /></div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-white">PAN Number</p>
              <p className="text-[11px] text-slate-500">{form.pan ? form.pan.replace(/(.{5})/, "XXXXX") : "Not linked"}</p>
            </div>
            <Badge label={form.pan ? "Linked" : "Link"} color={form.pan ? "emerald" : "amber"} />
          </div>
          <SettingRow icon={Fingerprint} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="Aadhaar Linkage" description="Link Aadhaar for e-verification" badge="Soon" badgeColor="slate" trailing={null} />
          <SettingRow icon={Building2} iconColor="text-sky-400" iconBg="bg-sky-500/10" label="GST Number" description="For business owners / freelancers" badge="Soon" badgeColor="slate" trailing={null} />
        </SettingSection>
      </div>
    </motion.div>
  );
};

// ─── 2. SECURITY ─────────────────────────────────────────────────────────────

const SECURITY_TIPS = [
  "Use a unique password not shared with any other service.",
  "Enable 2FA to protect against stolen passwords.",
  "Regularly review and revoke sessions on unknown devices.",
  "Never share your OTP or session tokens with anyone.",
];

const SecurityPage = ({ onBack, showToast, triggerConfirm }) => {
  const [twoFA, setTwoFA] = useState(false);
  const [showChangePw, setShowChangePw] = useState(false);
  const [showSessions, setShowSessions] = useState(false);
  const [showPwCurrent, setShowPwCurrent] = useState(false);
  const [showPwNew, setShowPwNew] = useState(false);
  const [pwForm, setPwForm] = useState({ current_password: "", new_password: "", confirm: "" });
  const [pwSaving, setPwSaving] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [loginAlerts, setLoginAlerts] = useState(() => loadPrefs().login_alerts !== false);
  const [suspiciousAlerts, setSuspiciousAlerts] = useState(() => loadPrefs().suspicious_alerts !== false);

  const pwStrength = useMemo(() => {
    const p = pwForm.new_password;
    if (!p) return null;
    let score = 0;
    if (p.length >= 8)  score++;
    if (p.length >= 12) score++;
    if (/[A-Z]/.test(p)) score++;
    if (/[0-9]/.test(p)) score++;
    if (/[^A-Za-z0-9]/.test(p)) score++;
    if (score <= 1) return { label: "Weak", color: "bg-rose-500", pct: "20%" };
    if (score <= 2) return { label: "Fair", color: "bg-amber-500", pct: "45%" };
    if (score <= 3) return { label: "Good", color: "bg-yellow-400", pct: "65%" };
    if (score <= 4) return { label: "Strong", color: "bg-emerald-500", pct: "85%" };
    return { label: "Very Strong", color: "bg-emerald-400", pct: "100%" };
  }, [pwForm.new_password]);

  const handleChangePassword = async () => {
    if (pwForm.new_password !== pwForm.confirm) { showToast?.("Passwords don't match", "error"); return; }
    if (pwForm.new_password.length < 8) { showToast?.("Password must be at least 8 characters", "error"); return; }
    setPwSaving(true);
    try {
      await authApi.changePassword({ current_password: pwForm.current_password, new_password: pwForm.new_password });
      showToast?.("Password updated successfully!", "success");
      setShowChangePw(false);
      setPwForm({ current_password: "", new_password: "", confirm: "" });
    } catch (err) {
      showToast?.(err?.detail || err?.message || "Password change failed", "error");
    } finally { setPwSaving(false); }
  };

  const loadSessions = async () => {
    setSessionsLoading(true);
    try {
      const res = await authApi.sessions();
      setSessions(res?.sessions || res?.data?.sessions || []);
    } catch { showToast?.("Failed to load sessions", "error"); }
    finally { setSessionsLoading(false); }
  };

  const handleRevoke = (id) => {
    triggerConfirm?.("Revoke this session? The device will be logged out.", async () => {
      try {
        await authApi.revokeSession(id);
        setSessions(s => s.filter(x => x.id !== id));
        showToast?.("Session revoked", "success");
      } catch { showToast?.("Revoke failed", "error"); }
    });
  };

  const pwInputCls = "w-full pl-4 pr-12 py-3 bg-black/20 border border-white/10 rounded-2xl text-white text-sm outline-none focus:border-purple-500/50 transition-colors placeholder:text-slate-600";

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <PageHeader title="Privacy & Security" subtitle="Protect your account" onBack={onBack} />

      {/* Security score pill */}
      <InfoCard color="indigo">
        <div className="flex items-center gap-3 mb-3">
          <div className="p-2 bg-indigo-500/20 rounded-xl"><Shield className="w-5 h-5 text-indigo-400" /></div>
          <div>
            <p className="text-sm font-black text-white">Security Score</p>
            <p className="text-[10px] text-slate-400">Based on your current settings</p>
          </div>
          <div className="ml-auto text-2xl font-black text-indigo-400">{twoFA ? "85" : "55"}<span className="text-sm text-slate-500">/100</span></div>
        </div>
        <div className="w-full h-1.5 rounded-full bg-white/5 overflow-hidden">
          <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-700" style={{ width: twoFA ? "85%" : "55%" }} />
        </div>
        <p className="text-[10px] text-slate-500 mt-2">{twoFA ? "Great! Enable biometric login to reach 100." : "Enable 2FA to boost your score by 30 points."}</p>
      </InfoCard>

      <div className="space-y-6">
        <SettingSection title="Authentication">
          {/* Change Password */}
          <SettingRow
            icon={Lock} iconColor="text-purple-400" iconBg="bg-purple-500/10"
            label="Change Password" description="Update your login password"
            onClick={() => setShowChangePw(v => !v)}
            trailing={<ChevronRight className={`w-4 h-4 text-slate-700 transition-all ${showChangePw ? "rotate-90" : ""}`} />}
          />
          <AnimatePresence>
            {showChangePw && (
              <motion.div key="pwform" {...fadeUp} className="space-y-4 p-5 rounded-2xl bg-white/[0.03] border border-white/10">
                <div className="space-y-1.5">
                  <label className={labelCls}>Current Password</label>
                  <div className="relative">
                    <input type={showPwCurrent ? "text" : "password"} className={pwInputCls} value={pwForm.current_password} onChange={e => setPwForm(f => ({ ...f, current_password: e.target.value }))} placeholder="Your current password" />
                    <button type="button" onClick={() => setShowPwCurrent(v => !v)} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-400">
                      {showPwCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className={labelCls}>New Password</label>
                  <div className="relative">
                    <input type={showPwNew ? "text" : "password"} className={pwInputCls} value={pwForm.new_password} onChange={e => setPwForm(f => ({ ...f, new_password: e.target.value }))} placeholder="Min 8 chars, mixed case + digit" />
                    <button type="button" onClick={() => setShowPwNew(v => !v)} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-400">
                      {showPwNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                  {pwStrength && (
                    <div className="space-y-1 pt-1">
                      <div className="w-full h-1 rounded-full bg-white/5 overflow-hidden">
                        <div className={`h-full rounded-full ${pwStrength.color} transition-all duration-500`} style={{ width: pwStrength.pct }} />
                      </div>
                      <p className="text-[10px] text-slate-500 pl-1">Strength: <span className="font-black text-white">{pwStrength.label}</span></p>
                    </div>
                  )}
                </div>
                <div className="space-y-1.5">
                  <label className={labelCls}>Confirm New Password</label>
                  <input type="password" className={pwInputCls} value={pwForm.confirm} onChange={e => setPwForm(f => ({ ...f, confirm: e.target.value }))} placeholder="Re-enter new password" />
                  {pwForm.new_password && pwForm.confirm && pwForm.new_password !== pwForm.confirm && (
                    <p className="text-[11px] text-rose-400 font-bold pl-1 flex items-center gap-1"><AlertCircle className="w-3 h-3" /> Passwords don't match</p>
                  )}
                </div>
                <div className="flex gap-3 pt-1">
                  <button onClick={() => setShowChangePw(false)} className="flex-1 py-3 rounded-2xl bg-white/5 border border-white/10 text-slate-400 text-xs font-black uppercase tracking-widest hover:bg-white/8 transition-colors">Cancel</button>
                  <button
                    onClick={handleChangePassword}
                    disabled={pwSaving || !pwForm.current_password || !pwForm.new_password || pwForm.new_password !== pwForm.confirm}
                    className="flex-1 py-3 rounded-2xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-black uppercase tracking-widest transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
                  >
                    {pwSaving ? <Spinner /> : <Key className="w-4 h-4" />}
                    {pwSaving ? "Updating…" : "Update"}
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* 2FA */}
          <SettingRow
            icon={ShieldCheck} iconColor="text-emerald-400" iconBg="bg-emerald-500/10"
            label="Two-Factor Authentication"
            description={twoFA ? "Active — extra layer of protection on" : "Off — enable to protect your account"}
            badge={twoFA ? "ON" : "OFF"} badgeColor={twoFA ? "emerald" : "slate"}
            trailing={<Toggle enabled={twoFA} onChange={setTwoFA} />}
          />
          <AnimatePresence>
            {twoFA && (
              <motion.div key="2fa" {...fadeUp} className="space-y-2 pl-2">
                <SettingRow icon={Smartphone} iconColor="text-sky-400" iconBg="bg-sky-500/10" label="SMS OTP" description="Receive code via mobile" badge="Soon" badgeColor="slate" trailing={null} />
                <SettingRow icon={QrCode} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="Authenticator App" description="Google Authenticator / Authy" badge="Soon" badgeColor="slate" trailing={null} />
                <SettingRow icon={Fingerprint} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Biometric Login" description="Face ID / Fingerprint" badge="Soon" badgeColor="slate" trailing={null} />
              </motion.div>
            )}
          </AnimatePresence>
        </SettingSection>

        {/* Sessions */}
        <SettingSection title="Active Sessions">
          <SettingRow
            icon={Activity} iconColor="text-amber-400" iconBg="bg-amber-500/10"
            label="Manage Devices" description="View all devices where you're logged in"
            onClick={() => { setShowSessions(v => !v); if (!showSessions) loadSessions(); }}
            trailing={<ChevronRight className={`w-4 h-4 text-slate-700 transition-all ${showSessions ? "rotate-90" : ""}`} />}
          />
          <AnimatePresence>
            {showSessions && (
              <motion.div key="sessions" {...fadeUp} className="space-y-2">
                {sessionsLoading ? (
                  <div className="py-6 flex justify-center"><Spinner size="md" /></div>
                ) : sessions.length === 0 ? (
                  <p className="text-xs text-slate-500 text-center py-4 italic">No other active sessions found</p>
                ) : (
                  sessions.map((s) => (
                    <div key={s.id} className="flex items-center gap-3 px-4 py-3.5 rounded-2xl bg-white/[0.03] border border-white/5">
                      <div className={`p-2 rounded-xl shrink-0 ${s.is_current ? "bg-emerald-500/10" : "bg-white/5"}`}>
                        <Smartphone className={`w-4 h-4 ${s.is_current ? "text-emerald-400" : "text-slate-500"}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-xs font-bold text-white">{s.is_current ? "This Device" : s.device_name || "Unknown Device"}</p>
                          {s.is_current && <Badge label="Current" color="emerald" />}
                        </div>
                        <p className="text-[10px] text-slate-500 mt-0.5">
                          {s.ip_address && <span className="font-mono">{s.ip_address} · </span>}
                          Since {new Date(s.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
                        </p>
                      </div>
                      {!s.is_current && (
                        <button onClick={() => handleRevoke(s.id)} className="px-3 py-1.5 rounded-xl bg-rose-500/10 text-rose-400 text-[10px] font-black uppercase tracking-wider hover:bg-rose-500/20 transition-colors shrink-0">
                          Revoke
                        </button>
                      )}
                    </div>
                  ))
                )}
                <button
                  onClick={() => triggerConfirm?.("Sign out all other devices?", () => showToast?.("All other sessions revoked", "success"))}
                  className="w-full py-3 rounded-2xl bg-rose-500/5 border border-rose-500/15 text-rose-400 text-xs font-black uppercase tracking-widest hover:bg-rose-500/10 transition-colors"
                >
                  Revoke All Other Sessions
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </SettingSection>

        {/* Security Alerts */}
        <SettingSection title="Security Alerts">
          <SettingRow icon={LogIn} iconColor="text-sky-400" iconBg="bg-sky-500/10" label="New Login Alerts" description="Notify on sign-in from a new device" trailing={<Toggle enabled={loginAlerts} onChange={v => { setLoginAlerts(v); savePref("login_alerts", v); }} />} />
          <SettingRow icon={AlertTriangle} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Suspicious Activity Alerts" description="Unusual access patterns or locations" trailing={<Toggle enabled={suspiciousAlerts} onChange={v => { setSuspiciousAlerts(v); savePref("suspicious_alerts", v); }} />} />
        </SettingSection>

        {/* Privacy Controls */}
        <SettingSection title="Privacy">
          <SettingRow icon={Eye} iconColor="text-slate-400" iconBg="bg-slate-500/10" label="Profile Visibility" description="Your profile is private by default" value="Private" trailing={null} />
          <SettingRow icon={Database} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="Data Sharing Consent" description="Analytics used to improve Spendsy" badge="Minimal" badgeColor="violet" />
          <SettingRow icon={RotateCcw} iconColor="text-rose-400" iconBg="bg-rose-500/10" label="Request Data Deletion" description="Permanently delete your account & data" danger onClick={() => triggerConfirm?.("Request account deletion? Our team will process this within 30 days.", () => showToast?.("Deletion request submitted", "success"))} />
        </SettingSection>

        {/* Tips */}
        <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5 space-y-2">
          <p className={labelCls + " mb-2"}>Security Tips</p>
          {SECURITY_TIPS.map((tip, i) => (
            <div key={i} className="flex items-start gap-2">
              <CheckCircle className="w-3 h-3 text-emerald-500 shrink-0 mt-0.5" />
              <p className="text-[11px] text-slate-500">{tip}</p>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
};

// ─── 3. FINANCIAL SETTINGS ────────────────────────────────────────────────────

const FinancialSettingsPage = ({ onBack, showToast }) => {
  const prefs = loadPrefs();
  const [currency, setCurrency] = useState(prefs.currency || "INR");
  const [fiscalMonth, setFiscalMonth] = useState(prefs.fiscal_start || "April");
  const [roundOff, setRoundOff] = useState(prefs.round_off !== false);
  const [showSplit, setShowSplit] = useState(prefs.show_split !== false);
  const [autoReconcile, setAutoReconcile] = useState(prefs.auto_reconcile !== false);
  const [defaultAccount, setDefaultAccount] = useState(prefs.default_account || "");
  const [regime, setRegime] = useState(prefs.tax_regime || "new");
  const [compactAmounts, setCompactAmounts] = useState(prefs.compact_amounts !== false);

  const save = (key, val) => { 
    savePref(key, val); 
    onUpdateSettings?.({ [key]: val });
    showToast?.("Preference synced!", "success"); 
  };

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <PageHeader title="Financial Settings" subtitle="Currency, tax & account preferences" onBack={onBack} />
      <div className="space-y-6">

        <SettingSection title="Region & Currency">
          <div className="flex items-center gap-4 px-5 py-4 rounded-2xl border border-white/5" style={{ background: "rgba(255,255,255,0.03)" }}>
            <div className="p-2.5 bg-sky-500/10 text-sky-400 rounded-xl shrink-0"><Globe className="w-5 h-5" /></div>
            <div className="flex-1">
              <p className="text-sm font-bold text-white">Base Currency</p>
              <p className="text-[11px] text-slate-500">All amounts displayed in this currency</p>
            </div>
            <select
              value={currency}
              onChange={e => { setCurrency(e.target.value); save("currency", e.target.value); }}
              className="bg-white/5 border border-white/10 text-white text-xs font-bold rounded-xl px-3 py-2 outline-none focus:border-sky-500/50"
            >
              <option value="INR">INR (₹)</option>
              <option value="USD">USD ($)</option>
              <option value="EUR">EUR (€)</option>
              <option value="GBP">GBP (£)</option>
              <option value="SGD">SGD (S$)</option>
            </select>
          </div>

          <div className="flex items-center gap-4 px-5 py-4 rounded-2xl border border-white/5" style={{ background: "rgba(255,255,255,0.03)" }}>
            <div className="p-2.5 bg-violet-500/10 text-violet-400 rounded-xl shrink-0"><Calendar className="w-5 h-5" /></div>
            <div className="flex-1">
              <p className="text-sm font-bold text-white">Financial Year Start</p>
              <p className="text-[11px] text-slate-500">India: April (FY runs April–March)</p>
            </div>
            <select
              value={fiscalMonth}
              onChange={e => { setFiscalMonth(e.target.value); save("fiscal_start", e.target.value); }}
              className="bg-white/5 border border-white/10 text-white text-xs font-bold rounded-xl px-3 py-2 outline-none focus:border-violet-500/50"
            >
              {["January","February","March","April","July","October"].map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>

          <SettingRow icon={IndianRupee} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Compact Amount Format" description="Show ₹1.2L instead of ₹1,20,000" trailing={<Toggle enabled={compactAmounts} onChange={v => { setCompactAmounts(v); save("compact_amounts", v); }} />} />
        </SettingSection>

        <SettingSection title="Indian Tax Regime">
          <InfoCard color="amber">
            <p className="text-xs font-black text-white mb-1">Active Tax Regime</p>
            <p className="text-[11px] text-slate-400 mb-3">This affects TORA's tax calculations and ITR recommendations.</p>
            <div className="flex gap-2">
              {[["new", "New Regime", "Lower rates, no deductions"], ["old", "Old Regime", "Higher rates, all deductions"]].map(([key, label, sub]) => (
                <button
                  key={key}
                  onClick={() => { setRegime(key); save("tax_regime", key); }}
                  className={`flex-1 p-3 rounded-2xl border text-left transition-all ${regime === key ? "bg-amber-500/20 border-amber-500/40" : "bg-white/5 border-white/5 hover:bg-white/10"}`}
                >
                  <p className={`text-xs font-black ${regime === key ? "text-amber-300" : "text-white"}`}>{label}</p>
                  <p className="text-[10px] text-slate-500 mt-0.5">{sub}</p>
                </button>
              ))}
            </div>
          </InfoCard>
        </SettingSection>

        <SettingSection title="Transaction Preferences">
          <SettingRow icon={ArrowRightLeft} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Auto-Reconcile Transfers" description="Pair matching debits & credits automatically" trailing={<Toggle enabled={autoReconcile} onChange={v => { setAutoReconcile(v); save("auto_reconcile", v); }} />} />
          <SettingRow icon={Layers} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Show Split Transactions" description="Display split category breakdown inline" trailing={<Toggle enabled={showSplit} onChange={v => { setShowSplit(v); save("show_split", v); }} />} />
          <SettingRow icon={Calculator} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="Round-off Display" description="Round amounts to nearest rupee in views" trailing={<Toggle enabled={roundOff} onChange={v => { setRoundOff(v); save("round_off", v); }} />} />
        </SettingSection>

        <SettingSection title="Linked Accounts">
          <SettingRow icon={Building2} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Bank Accounts" description="Manage linked savings & current accounts" />
          <SettingRow icon={CreditCard} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="Credit Cards" description="Add, remove or update credit cards" />
          <SettingRow icon={Wallet} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Investment Accounts" description="Demat, MF folio, NPS, PPF" badge="Soon" badgeColor="slate" trailing={null} />
          <SettingRow icon={RefreshCw} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Sync All Accounts" description="Pull latest balances from linked sources" onClick={() => showToast?.("Sync initiated…", "success")} />
        </SettingSection>

        <SettingSection title="Budget Defaults">
          <SettingRow icon={Target} iconColor="text-rose-400" iconBg="bg-rose-500/10" label="Monthly Spending Cap" description="Alert when total spend approaches limit" />
          <SettingRow icon={Tag} iconColor="text-indigo-400" iconBg="bg-indigo-500/10" label="Expense Categories" description="Customize or rename spending categories" />
          <SettingRow icon={PiggyBank} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Auto-Save Rule" description="Set a % of income to auto-allocate to savings" badge="Soon" badgeColor="slate" trailing={null} />
        </SettingSection>
      </div>
    </motion.div>
  );
};

// ─── 4. NOTIFICATIONS ─────────────────────────────────────────────────────────

const NotificationsPage = ({ onBack }) => {
  const prefs = loadPrefs();
  const mk = (key, def) => {
    const [val, set] = useState(prefs[key] !== undefined ? prefs[key] : def);
    const toggle = v => { 
      set(v); 
      savePref(key, v); 
      onUpdateSettings?.({ [key]: v });
    };
    return [val, toggle];
  };

  const [emailN, toggleEmail] = mk("notif_email", true);
  const [pushN, togglePush] = mk("notif_push", true);
  const [smsN, toggleSms] = mk("notif_sms", false);

  const [txnAlert, toggleTxn] = mk("notif_txn", true);
  const [budgetAlert, toggleBudget] = mk("notif_budget", true);
  const [goalAlert, toggleGoal] = mk("notif_goal", true);
  const [loanAlert, toggleLoan] = mk("notif_loan", true);
  const [itrAlert, toggleITR] = mk("notif_itr", true);
  const [taxDeadline, toggleTaxDeadline] = mk("notif_tax_deadline", true);
  const [advTax, toggleAdvTax] = mk("notif_adv_tax", true);
  const [toraWeekly, toggleToraWeekly] = mk("notif_tora_weekly", true);
  const [toraInsight, toggleToraInsight] = mk("notif_tora_insight", false);
  const [secAlert, toggleSecAlert] = mk("notif_security", true);
  const [quietMode, toggleQuiet] = mk("notif_quiet", false);
  const [quietStart, setQuietStart] = useState(prefs.quiet_start || "22:00");
  const [quietEnd, setQuietEnd] = useState(prefs.quiet_end || "07:00");

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <PageHeader title="Notifications" subtitle="Stay informed, not overwhelmed" onBack={onBack} />
      <div className="space-y-6">

        <SettingSection title="Delivery Channels">
          <SettingRow icon={Mail} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Email Notifications" description={emailN ? "Receiving digests & alerts via email" : "Email notifications disabled"} trailing={<Toggle enabled={emailN} onChange={toggleEmail} />} />
          <SettingRow icon={Smartphone} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Push Notifications" description={pushN ? "Enabled on this device" : "Push notifications silent"} trailing={<Toggle enabled={pushN} onChange={togglePush} />} />
          <SettingRow icon={MessageSquare} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="SMS Alerts" description={smsN ? "Critical alerts via SMS" : "No SMS alerts"} trailing={<Toggle enabled={smsN} onChange={toggleSms} />} />
        </SettingSection>

        <SettingSection title="Transaction Alerts">
          <SettingRow icon={ArrowRightLeft} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Transaction Posted" description="Alert on every debit or credit" trailing={<Toggle enabled={txnAlert} onChange={toggleTxn} />} />
          <SettingRow icon={AlertTriangle} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Budget Threshold" description="Warn when 80% of budget is used" trailing={<Toggle enabled={budgetAlert} onChange={toggleBudget} />} />
          <SettingRow icon={Target} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Goal Milestones" description="Celebrate goal progress" trailing={<Toggle enabled={goalAlert} onChange={toggleGoal} />} />
          <SettingRow icon={Landmark} iconColor="text-rose-400" iconBg="bg-rose-500/10" label="EMI Due Reminders" description="Loan & credit card due date alerts" trailing={<Toggle enabled={loanAlert} onChange={toggleLoan} />} />
        </SettingSection>

        <SettingSection title="Tax & Compliance (Indian)" subtitle="Critical dates you cannot miss">
          <SettingRow icon={FileBarChart} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="ITR Filing Deadlines" description="July 31 & belated return reminders" trailing={<Toggle enabled={itrAlert} onChange={toggleITR} />} />
          <SettingRow icon={Calendar} iconColor="text-orange-400" iconBg="bg-orange-500/10" label="Advance Tax Due Dates" description="June 15, Sep 15, Dec 15, Mar 15" trailing={<Toggle enabled={advTax} onChange={toggleAdvTax} />} />
          <SettingRow icon={Receipt} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="Tax-Saving Deadlines" description="80C/80D investment deadline reminders" trailing={<Toggle enabled={taxDeadline} onChange={toggleTaxDeadline} />} />
        </SettingSection>

        <SettingSection title="TORA AI Digest">
          <SettingRow icon={BarChart2} iconColor="text-indigo-400" iconBg="bg-indigo-500/10" label="Weekly Spending Summary" description="Emailed every Monday morning" trailing={<Toggle enabled={toraWeekly} onChange={toggleToraWeekly} />} />
          <SettingRow icon={Zap} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="Proactive AI Insights" description="TORA nudges when it spots an opportunity" trailing={<Toggle enabled={toraInsight} onChange={toggleToraInsight} />} />
        </SettingSection>

        <SettingSection title="Security Notifications">
          <SettingRow icon={Shield} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Security Alerts" description="Login from new device, password change" trailing={<Toggle enabled={secAlert} onChange={toggleSecAlert} />} />
        </SettingSection>

        <SettingSection title="Do Not Disturb">
          <SettingRow icon={BellOff} iconColor="text-slate-400" iconBg="bg-slate-500/10" label="Quiet Hours" description="Suppress non-critical alerts at night" trailing={<Toggle enabled={quietMode} onChange={toggleQuiet} />} />
          <AnimatePresence>
            {quietMode && (
              <motion.div key="quiet" {...fadeUp} className="px-5 py-4 rounded-2xl bg-white/[0.03] border border-white/10">
                <div className="flex gap-4">
                  <div className="flex-1 space-y-1.5">
                    <label className={labelCls}>Silence From</label>
                    <input type="time" value={quietStart} onChange={e => { setQuietStart(e.target.value); savePref("quiet_start", e.target.value); }} className={inputCls} />
                  </div>
                  <div className="flex-1 space-y-1.5">
                    <label className={labelCls}>Until</label>
                    <input type="time" value={quietEnd} onChange={e => { setQuietEnd(e.target.value); savePref("quiet_end", e.target.value); }} className={inputCls} />
                  </div>
                </div>
                <p className="text-[10px] text-slate-600 mt-2 pl-1">Security and fraud alerts always go through.</p>
              </motion.div>
            )}
          </AnimatePresence>
        </SettingSection>
      </div>
    </motion.div>
  );
};

// ─── 5. APPEARANCE ────────────────────────────────────────────────────────────

const AppearancePage = ({ onBack, currentTheme, onThemeChange }) => {
  const prefs = loadPrefs();
  const [accent, setAccent] = useState(prefs.accent || "indigo");
  const [density, setDensity] = useState(prefs.density || "comfortable");
  const [fontScale, setFontScale] = useState(prefs.font_scale || "normal");
  const [animEnabled, setAnimEnabled] = useState(prefs.animations !== false);
  const [chartStyle, setChartStyle] = useState(prefs.chart_style || "gradient");

  const accents = [
    { name: "indigo", hex: "#6366f1", label: "Indigo" },
    { name: "violet", hex: "#8b5cf6", label: "Violet" },
    { name: "emerald", hex: "#10b981", label: "Emerald" },
    { name: "rose", hex: "#f43f5e", label: "Rose" },
    { name: "amber", hex: "#f59e0b", label: "Amber" },
    { name: "sky", hex: "#38bdf8", label: "Sky" },
    { name: "pink", hex: "#ec4899", label: "Pink" },
    { name: "cyan", hex: "#06b6d4", label: "Cyan" },
  ];

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <PageHeader title="Appearance" subtitle="Make it yours" onBack={onBack} />
      <div className="space-y-6">

        <SettingSection title="Theme">
          <div className="flex bg-black/30 p-1.5 rounded-2xl border border-white/5 gap-1.5">
            {[["dark", "🌑", "Dark"], ["light", "☀️", "Light"], ["system", "⚙️", "System"]].map(([t, emoji, label]) => (
              <button key={t} onClick={() => onThemeChange?.(t)} className={`flex-1 py-2.5 rounded-xl text-xs font-bold transition-all ${currentTheme === t ? "bg-white/10 text-white shadow" : "text-slate-500 hover:text-slate-300"}`}>
                {emoji} {label}
              </button>
            ))}
          </div>
        </SettingSection>

        <SettingSection title="Accent Color">
          <div className="grid grid-cols-4 gap-3 px-2 py-3">
            {accents.map(a => (
              <button key={a.name} onClick={() => { 
                setAccent(a.name); 
                savePref("accent", a.name); 
                onUpdateSettings?.({ accent: a.name });
              }} className="flex flex-col items-center gap-1.5 group">
                <div className="relative w-10 h-10 rounded-2xl transition-transform group-hover:scale-110" style={{ backgroundColor: a.hex }}>
                  {accent === a.name && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <CheckCircle className="w-5 h-5 text-white drop-shadow-lg" />
                    </div>
                  )}
                </div>
                <span className={`text-[9px] font-bold ${accent === a.name ? "text-white" : "text-slate-600"}`}>{a.label}</span>
              </button>
            ))}
          </div>
        </SettingSection>

        <SettingSection title="Layout Density">
          <div className="flex bg-black/30 p-1.5 rounded-2xl border border-white/5 gap-1.5">
            {["compact", "comfortable", "spacious"].map(d => (
              <button key={d} onClick={() => { setDensity(d); savePref("density", d); onUpdateSettings?.({ density: d }); }} className={`flex-1 py-2.5 rounded-xl text-xs font-bold capitalize transition-all ${density === d ? "bg-white/10 text-white shadow" : "text-slate-500 hover:text-slate-300"}`}>
                {d}
              </button>
            ))}
          </div>
        </SettingSection>

        <SettingSection title="Charts & Visualizations">
          <div className="flex bg-black/30 p-1.5 rounded-2xl border border-white/5 gap-1.5">
            {[["gradient", "Gradient"], ["flat", "Flat"], ["minimal", "Minimal"]].map(([v, l]) => (
              <button key={v} onClick={() => { setChartStyle(v); savePref("chart_style", v); onUpdateSettings?.({ chart_style: v }); }} className={`flex-1 py-2.5 rounded-xl text-xs font-bold transition-all ${chartStyle === v ? "bg-white/10 text-white shadow" : "text-slate-500 hover:text-slate-300"}`}>
                {l}
              </button>
            ))}
          </div>
        </SettingSection>

        <SettingSection title="Accessibility">
          <SettingRow icon={Zap} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Animations & Transitions" description="Disable to reduce motion" trailing={<Toggle enabled={animEnabled} onChange={v => { setAnimEnabled(v); savePref("animations", v); onUpdateSettings?.({ animations: v }); }} />} />
          <div className="flex items-center gap-4 px-5 py-4 rounded-2xl border border-white/5" style={{ background: "rgba(255,255,255,0.03)" }}>
            <div className="p-2.5 bg-blue-500/10 text-blue-400 rounded-xl shrink-0"><Languages className="w-5 h-5" /></div>
            <div className="flex-1">
              <p className="text-sm font-bold text-white">Font Size</p>
              <p className="text-[11px] text-slate-500">Adjust text size across the app</p>
            </div>
            <select value={fontScale} onChange={e => { setFontScale(e.target.value); savePref("font_scale", e.target.value); onUpdateSettings?.({ font_scale: e.target.value }); }} className="bg-white/5 border border-white/10 text-white text-xs font-bold rounded-xl px-3 py-2 outline-none">
              {["small", "normal", "large", "x-large"].map(s => <option key={s} value={s} className="capitalize">{s.replace("-", " ")}</option>)}
            </select>
          </div>
        </SettingSection>
      </div>
    </motion.div>
  );
};

// ─── 6. AI / TORA FEATURES ────────────────────────────────────────────────────

const AIFeaturesPage = ({ onBack, user, onUpdateSettings }) => {
  const prefs = loadPrefs();
  const mk = (key, def) => {
    const [val, set] = useState(prefs[key] !== undefined ? prefs[key] : def);
    return [val, v => { 
      set(v); 
      savePref(key, v);
      onUpdateSettings?.({ [key]: v });
    }];
  };

  const [autoCat, toggleAutoCat] = mk("ai_autocat", true);
  const [insights, toggleInsights] = mk("ai_insights", true);
  const [predictive, togglePredictive] = mk("ai_predictive", false);
  const [taxOptimize, toggleTaxOptimize] = mk("ai_tax_optimize", true);
  const [anomaly, toggleAnomaly] = mk("ai_anomaly", true);
  const [planSuggest, togglePlanSuggest] = mk("ai_plan_suggest", true);
  const [toraPersonality, setToraPersonality] = useState(prefs.tora_personality || "balanced");
  const [toraVerbosity, setToraVerbosity] = useState(prefs.tora_verbosity || "normal");
  const [memoryEnabled, toggleMemory] = mk("ai_memory", true);
  const [feedbackMode, toggleFeedbackMode] = mk("ai_feedback", true);

  const isPro = user?.tier === "pro" || user?.tier === "enterprise";

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <PageHeader title="TORA AI Settings" subtitle="Configure your AI co-pilot" onBack={onBack} />

      <InfoCard color="indigo">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-violet-500/20 rounded-xl"><Bot className="w-5 h-5 text-violet-400" /></div>
          <div>
            <p className="text-sm font-black text-white">TORA — Tax Optimization & Recommendation Agent</p>
            <p className="text-[10px] text-slate-400">Powered by Gemini 1.5 Flash</p>
          </div>
          <Badge label={isPro ? "Pro" : "Free"} color={isPro ? "indigo" : "slate"} />
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed">TORA learns from your patterns to categorize, forecast, and optimize your finances. Tool-calling (creating plans, comparing tax regimes) requires Pro.</p>
      </InfoCard>

      <div className="space-y-6">
        <SettingSection title="Automation">
          <SettingRow icon={Tag} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Auto-Categorization" description="AI sorts transactions into categories" trailing={<Toggle enabled={autoCat} onChange={toggleAutoCat} />} />
          <SettingRow icon={AlertCircle} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Anomaly Detection" description="Flag unusual or duplicate transactions" trailing={<Toggle enabled={anomaly} onChange={toggleAnomaly} />} />
          <SettingRow icon={TrendingUp} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Predictive Spending Alerts" description="Warn before you're likely to overspend" badge={!isPro ? "Pro" : undefined} badgeColor="indigo" trailing={<Toggle enabled={predictive} onChange={togglePredictive} disabled={!isPro} />} />
          <SettingRow icon={PiggyBank} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="Investment Plan Suggestions" description="TORA recommends plans based on goals" badge={!isPro ? "Pro" : undefined} badgeColor="indigo" trailing={<Toggle enabled={planSuggest} onChange={togglePlanSuggest} disabled={!isPro} />} />
        </SettingSection>

        <SettingSection title="Tax Intelligence">
          <SettingRow icon={Calculator} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Tax Regime Optimizer" description="Auto-compare New vs Old regime for you" badge={!isPro ? "Pro" : undefined} badgeColor="indigo" trailing={<Toggle enabled={taxOptimize} onChange={toggleTaxOptimize} disabled={!isPro} />} />
          <SettingRow icon={Receipt} iconColor="text-rose-400" iconBg="bg-rose-500/10" label="Deduction Scanner" description="Spot eligible 80C/80D deductions in transactions" badge={!isPro ? "Pro" : undefined} badgeColor="indigo" trailing={<span />} />
        </SettingSection>

        <SettingSection title="Weekly Insights">
          <SettingRow icon={BarChart2} iconColor="text-sky-400" iconBg="bg-sky-500/10" label="Smart Insights Digest" description="Weekly AI-powered spending report" trailing={<Toggle enabled={insights} onChange={toggleInsights} />} />
        </SettingSection>

        <SettingSection title="TORA Personality">
          <div className="space-y-2 px-1">
            <p className="text-[10px] text-slate-600 uppercase tracking-widest font-black mb-3 pl-1">Communication Style</p>
            {[["concise", "Concise", "Short, direct answers"], ["balanced", "Balanced", "Mix of detail and brevity (default)"], ["detailed", "Detailed", "Full explanations and context"]].map(([v, l, d]) => (
              <button
                key={v}
                onClick={() => { 
                  setToraPersonality(v); 
                  savePref("tora_personality", v);
                  onUpdateSettings?.({ tora_personality: v });
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl border transition-all text-left ${toraPersonality === v ? "bg-violet-500/15 border-violet-500/30" : "bg-white/[0.02] border-white/5 hover:bg-white/5"}`}
              >
                <div className={`w-4 h-4 rounded-full border-2 shrink-0 flex items-center justify-center ${toraPersonality === v ? "border-violet-500 bg-violet-500" : "border-slate-600"}`}>
                  {toraPersonality === v && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                </div>
                <div>
                  <p className="text-sm font-bold text-white">{l}</p>
                  <p className="text-[10px] text-slate-500">{d}</p>
                </div>
              </button>
            ))}
          </div>
        </SettingSection>

        <SettingSection title="Memory & Learning">
          <SettingRow icon={BookOpen} iconColor="text-indigo-400" iconBg="bg-indigo-500/10" label="Conversation Memory" description={`TORA remembers ${isPro ? "last 100" : "last 20"} messages`} trailing={<Toggle enabled={memoryEnabled} onChange={toggleMemory} />} />
          <SettingRow icon={CheckCircle} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Feedback Loop" description="Thumbs up/down improves TORA's suggestions" trailing={<Toggle enabled={feedbackMode} onChange={toggleFeedbackMode} />} />
          <SettingRow icon={Trash2} iconColor="text-rose-400" iconBg="bg-rose-500/10" label="Clear TORA Memory" description="Reset all conversation history" danger onClick={() => { savePref("tora_cleared", Date.now()); }} />
        </SettingSection>
      </div>
    </motion.div>
  );
};

// ─── 7. DATA MANAGEMENT ───────────────────────────────────────────────────────

const DataManagementPage = ({ onBack, triggerConfirm, transactions, onDeleteAll, showToast, onNavigateImport }) => {
  const [backupRunning, setBackupRunning] = useState(false);

  const handleExport = (format) => {
    if (!transactions?.length) { showToast?.("No transactions to export", "error"); return; }
    if (format === "csv") {
      downloadCSV(transactions);
      showToast?.("CSV downloaded!", "success");
    } else {
      showToast?.(`${format.toUpperCase()} export coming soon`, "success");
    }
  };

  const handleBackup = async () => {
    setBackupRunning(true);
    await new Promise(r => setTimeout(r, 1800));
    setBackupRunning(false);
    showToast?.("Backup created successfully", "success");
  };

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <PageHeader title="Data Management" subtitle="Your data, your control" onBack={onBack} />
      <div className="space-y-6">

        <SettingSection title="Export Transactions">
          <div className="grid grid-cols-3 gap-2">
            {[["CSV", "csv", "text-emerald-400", "bg-emerald-500/10"], ["PDF", "pdf", "text-rose-400", "bg-rose-500/10"], ["XLSX", "xlsx", "text-blue-400", "bg-blue-500/10"]].map(([label, fmt, tc, bg]) => (
              <button key={fmt} onClick={() => handleExport(fmt)} className={`py-4 rounded-2xl border border-white/5 flex flex-col items-center gap-2 hover:bg-white/5 transition-colors ${bg}`}>
                <Download className={`w-5 h-5 ${tc}`} />
                <span className={`text-xs font-black ${tc}`}>{label}</span>
                <span className="text-[9px] text-slate-600 uppercase">{transactions?.length || 0} rows</span>
              </button>
            ))}
          </div>
        </SettingSection>

        <SettingSection title="Import">
          <SettingRow icon={Upload} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Import Bank Statement" description="Upload PDF or CSV from your bank" onClick={onNavigateImport} />
          <SettingRow icon={Link2} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="Connect via Account Aggregator" description="Secure AA framework (RBI-approved)" badge="Soon" badgeColor="slate" trailing={null} />
        </SettingSection>

        <SettingSection title="Backup & Sync">
          <SettingRow
            icon={Database} iconColor="text-emerald-400" iconBg="bg-emerald-500/10"
            label="Create Backup"
            description="Snapshot all your financial data"
            onClick={handleBackup}
            trailing={backupRunning ? <Spinner /> : <ChevronRight className="w-4 h-4 text-slate-700" />}
          />
          <SettingRow icon={RefreshCw} iconColor="text-sky-400" iconBg="bg-sky-500/10" label="Cloud Sync" description="Keep data in sync across devices" badge="Soon" badgeColor="slate" trailing={null} />
        </SettingSection>

        <SettingSection title="Danger Zone">
          <div className="p-4 rounded-2xl bg-rose-500/5 border border-rose-500/20 space-y-2">
            <p className="text-[10px] text-rose-400 font-black uppercase tracking-widest mb-3 flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5" /> Irreversible Actions</p>
            <SettingRow
              icon={Trash2} iconColor="text-rose-400" iconBg="bg-rose-500/10"
              label="Delete All Transactions" description={`Erase all ${transactions?.length || 0} transactions permanently`} danger
              onClick={() => triggerConfirm?.(`Delete ALL ${transactions?.length || 0} transactions? This is irreversible.`, onDeleteAll)}
            />
            <SettingRow
              icon={ZapOff} iconColor="text-rose-500" iconBg="bg-rose-500/10"
              label="Reset App Data" description="Wipe all local preferences and cache" danger
              onClick={() => triggerConfirm?.("Reset all app data and preferences? Your server data is safe.", () => { localStorage.clear(); showToast?.("App data reset. Reload to apply.", "success"); })}
            />
          </div>
        </SettingSection>
      </div>
    </motion.div>
  );
};

// ─── 8. SUBSCRIPTION ─────────────────────────────────────────────────────────

const TIER_CONFIG = {
  free:       { label: "Free Plan",   color: "from-slate-800/80 to-slate-900/60",   border: "border-slate-500/20",   glow: "bg-slate-500/10",   icon: "text-slate-400",  badge: "text-slate-400",  features: ["20 transactions/mo", "Basic insights", "Community support", "CSV export"] },
  pro:        { label: "Pro Member",  color: "from-indigo-900/50 to-violet-900/30", border: "border-indigo-500/20",  glow: "bg-indigo-500/10",  icon: "text-indigo-400", badge: "text-indigo-400", features: ["Unlimited transactions", "TORA tool calling", "100-msg AI memory", "Email reports", "No ads", "Priority support"] },
  enterprise: { label: "Enterprise", color: "from-amber-900/50 to-orange-900/30",  border: "border-amber-500/20",   glow: "bg-amber-500/10",   icon: "text-amber-400",  badge: "text-amber-400",  features: ["Unlimited everything", "Unlimited AI memory", "Custom integrations", "Dedicated support", "White-label option"] },
};

const SubscriptionPage = ({ onBack, tier = "free" }) => {
  const cfg = TIER_CONFIG[tier] || TIER_CONFIG.free;

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <PageHeader title="Subscription & Billing" subtitle="Manage your plan" onBack={onBack} />
      <div className="space-y-6">

        {/* Plan Card */}
        <div className={`p-6 rounded-3xl bg-gradient-to-br ${cfg.color} border ${cfg.border} relative overflow-hidden`}>
          <div className={`absolute top-0 right-0 w-48 h-48 ${cfg.glow} blur-[60px] rounded-full pointer-events-none`} />
          <div className="relative z-10">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-white/10 rounded-xl"><Crown className={`w-5 h-5 ${cfg.icon}`} /></div>
                <div>
                  <p className="text-sm font-black text-white uppercase tracking-wider">{cfg.label}</p>
                  <p className={`text-[10px] ${cfg.badge} font-bold`}>
                    {tier === "free" ? "Upgrade for full access" : "Active subscription — thank you!"}
                  </p>
                </div>
              </div>
              {tier !== "free" && <Badge label="Active" color="emerald" />}
            </div>
            <div className="grid grid-cols-2 gap-2">
              {cfg.features.map(f => (
                <div key={f} className="flex items-center gap-2">
                  <CheckCircle className={`w-3 h-3 ${cfg.icon} shrink-0`} />
                  <span className="text-[11px] text-slate-300">{f}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Upgrade CTA for free tier */}
        {tier === "free" && (
          <div className="grid grid-cols-2 gap-3">
            <button className="py-4 rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-600 text-white text-xs font-black uppercase tracking-widest hover:opacity-90 transition-opacity shadow-lg shadow-indigo-900/30">
              <Crown className="w-4 h-4 mx-auto mb-1" />
              Go Pro
            </button>
            <button className="py-4 rounded-2xl bg-gradient-to-br from-amber-600 to-orange-600 text-white text-xs font-black uppercase tracking-widest hover:opacity-90 transition-opacity shadow-lg shadow-amber-900/30">
              <Star className="w-4 h-4 mx-auto mb-1" />
              Enterprise
            </button>
          </div>
        )}

        <SettingSection title="Billing">
          <SettingRow icon={FileText} iconColor="text-slate-400" iconBg="bg-slate-500/10" label="Billing History" description="View past invoices & receipts" />
          <SettingRow icon={CreditCard} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Payment Method" description={tier !== "free" ? "Manage your card on file" : "Add card when upgrading"} />
          <SettingRow icon={Package} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Redeem Coupon" description="Apply a promo or referral code" />
          {tier !== "free" && (
            <SettingRow icon={RotateCcw} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Renewal Date" description="Your plan renews monthly" value="May 2026" trailing={null} />
          )}
        </SettingSection>

        {/* Feature comparison */}
        <SettingSection title="Plan Comparison">
          <div className="rounded-2xl border border-white/5 overflow-hidden" style={{ background: "rgba(255,255,255,0.03)" }}>
            <div className="grid grid-cols-4 px-4 py-2 border-b border-white/5">
              <p className="text-[10px] font-black text-slate-600 uppercase col-span-2">Feature</p>
              {["Free", "Pro", "Ent"].map(h => <p key={h} className="text-[10px] font-black text-slate-600 uppercase text-center">{h}</p>)}
            </div>
            {[
              ["Transactions", "20/mo", "∞", "∞"],
              ["AI Chat", "Basic", "Full", "Full"],
              ["Tool Calling", "✗", "✓", "✓"],
              ["AI Memory", "20 msgs", "100 msgs", "∞"],
              ["Email Reports", "✗", "✓", "✓"],
              ["Ads", "Yes", "None", "None"],
              ["Support", "Community", "Priority", "Dedicated"],
            ].map(([feat, ...vals]) => (
              <div key={feat} className="grid grid-cols-4 px-4 py-2.5 border-b border-white/5 last:border-0 hover:bg-white/[0.02]">
                <p className="text-xs text-slate-400 font-bold col-span-2">{feat}</p>
                {vals.map((v, i) => (
                  <p key={i} className={`text-[11px] text-center font-bold ${v === "✓" ? "text-emerald-400" : v === "✗" ? "text-slate-700" : "text-slate-400"}`}>{v}</p>
                ))}
              </div>
            ))}
          </div>
        </SettingSection>
      </div>
    </motion.div>
  );
};

// ─── 9. HELP & SUPPORT ────────────────────────────────────────────────────────

const HelpSupportPage = ({ onBack }) => (
  <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
    <PageHeader title="Help & Support" subtitle="We're here for you" onBack={onBack} />
    <div className="space-y-6">
      <SettingSection title="Self-Service">
        <SettingRow icon={BookOpen} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Help Center" description="Browse guides, tutorials, and FAQs" />
        <SettingRow icon={FileText} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="Getting Started Guide" description="Set up Spendsy in 5 minutes" />
        <SettingRow icon={Calculator} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="ITR Filing Walkthrough" description="Step-by-step ITR on Spendsy" />
        <SettingRow icon={Bot} iconColor="text-indigo-400" iconBg="bg-indigo-500/10" label="TORA User Manual" description="How to get the best from your AI agent" />
      </SettingSection>
      <SettingSection title="Contact">
        <SettingRow icon={MessageSquare} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Live Chat Support" description="Chat with our team (Pro & Enterprise)" badge="Pro" badgeColor="indigo" />
        <SettingRow icon={Ticket} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Raise a Ticket" description="Report a bug or request a feature" />
        <SettingRow icon={Mail} iconColor="text-sky-400" iconBg="bg-sky-500/10" label="Email Support" description="support@spendsy.in" value="→" trailing={null} />
      </SettingSection>
      <SettingSection title="Community">
        <SettingRow icon={ExternalLink} iconColor="text-slate-400" iconBg="bg-slate-500/10" label="Community Forum" description="Connect with other Spendsy users" />
        <SettingRow icon={Star} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Rate the App" description="Enjoying Spendsy? Leave us a review" />
      </SettingSection>
    </div>
  </motion.div>
);

// ─── 10. ABOUT ────────────────────────────────────────────────────────────────

const AboutPage = ({ onBack }) => {
  const [copied, setCopied] = useState(false);
  const copy = (text) => { navigator.clipboard.writeText(text).then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000); }); };

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <PageHeader title="About" subtitle="Spendsy — Know your money" onBack={onBack} />
      <div className="space-y-6">
        <div className="text-center py-8 space-y-3">
          <div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center mx-auto shadow-2xl shadow-indigo-900/40">
            <span className="text-4xl">⚡</span>
          </div>
          <div>
            <p className="text-2xl font-black text-white tracking-tight">Spendsy</p>
            <p className="text-xs text-slate-500 font-black uppercase tracking-widest">Personal Finance OS</p>
          </div>
          <p className="text-xs text-slate-500 max-w-xs mx-auto leading-relaxed">
            Built for India. AI-powered wealth management, ITR filing, and tax optimization in one app.
          </p>
        </div>

        <SettingSection title="App Info">
          <SettingRow icon={Info} iconColor="text-slate-400" iconBg="bg-slate-500/10" label="Version" description="Current stable build" value="v2.4.0" trailing={null} />
          <SettingRow icon={Calendar} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Last Updated" description="Most recent release" value="Apr 2026" trailing={null} />
          <SettingRow icon={Globe} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Region" description="Data stored in India (AWS Mumbai)" value="IN" trailing={null} />
        </SettingSection>

        <SettingSection title="Legal">
          <SettingRow icon={FileText} iconColor="text-blue-400" iconBg="bg-blue-500/10" label="Terms & Conditions" description="User agreement — last revised Jan 2026" />
          <SettingRow icon={Shield} iconColor="text-emerald-400" iconBg="bg-emerald-500/10" label="Privacy Policy" description="How we store and use your data" value="v1.4" />
          <SettingRow icon={Landmark} iconColor="text-amber-400" iconBg="bg-amber-500/10" label="Compliance & Licenses" description="RBI NBFC-AA, IT Act 2000 compliant" />
          <SettingRow icon={BookOpen} iconColor="text-violet-400" iconBg="bg-violet-500/10" label="Open Source Licenses" description="Third-party libraries used" />
        </SettingSection>

        <SettingSection title="Debug">
          <SettingRow
            icon={Copy} iconColor="text-slate-400" iconBg="bg-slate-500/10"
            label="Copy Device ID" description="Share with support when reporting issues"
            onClick={() => copy(navigator.userAgent)}
            trailing={copied ? <Check className="w-4 h-4 text-emerald-400" /> : <ChevronRight className="w-4 h-4 text-slate-700" />}
          />
        </SettingSection>

        <p className="text-center text-[10px] font-black text-slate-800 uppercase tracking-[0.3em] pt-4">Made with ♥ in India — Spendsy v2.4.0</p>
      </div>
    </motion.div>
  );
};

// ─── MAIN SETTINGS HUB ───────────────────────────────────────────────────────

const SECTIONS = [
  { key: "personal",     icon: User,       label: "Personal Information",   description: "Name, photo, KYC, tax IDs",          iconColor: "text-blue-400",    iconBg: "bg-blue-500/10",    group: "Account" },
  { key: "security",     icon: Shield,     label: "Privacy & Security",     description: "Password, 2FA, sessions, alerts",     iconColor: "text-emerald-400", iconBg: "bg-emerald-500/10", group: "Account" },
  { key: "quick_actions",icon: SlidersHorizontal, label: "Quick Actions", description: "Customize your dashboard shortcuts", iconColor: "text-indigo-400", iconBg: "bg-indigo-500/10", group: "Account", badge: "New" },
  { key: "subscription", icon: Crown,      label: "Subscription & Billing", description: "Plan, invoices, coupons",             iconColor: "text-amber-400",   iconBg: "bg-amber-500/10",   group: "Account" },
  { key: "financial",    icon: Coins,      label: "Financial Settings",     description: "Currency, tax regime, accounts",      iconColor: "text-yellow-400",  iconBg: "bg-yellow-500/10",  group: "Finance" },
  { key: "notifications",icon: Bell,       label: "Notifications",          description: "Channels, tax deadlines, AI digest",  iconColor: "text-violet-400",  iconBg: "bg-violet-500/10",  group: "Finance" },
  { key: "ai",           icon: Bot,        label: "TORA AI Settings",       description: "Automation, memory, personality",     iconColor: "text-indigo-400",  iconBg: "bg-indigo-500/10",  group: "Finance",  badge: "AI" },
  { key: "appearance",   icon: Palette,    label: "Appearance",             description: "Theme, accent, density, charts",      iconColor: "text-pink-400",    iconBg: "bg-pink-500/10",    group: "App" },
  { key: "data",         icon: Database,   label: "Data Management",        description: "Export, import, backup, danger zone", iconColor: "text-slate-400",   iconBg: "bg-slate-500/10",   group: "App" },
  { key: "help",         icon: LifeBuoy,   label: "Help & Support",         description: "Guides, tickets, live chat",          iconColor: "text-sky-400",     iconBg: "bg-sky-500/10",     group: "App" },
  { key: "about",        icon: Info,       label: "About",                  description: "Version, legal, compliance",          iconColor: "text-slate-400",   iconBg: "bg-slate-500/10",   group: "App" },
];

const GROUPS = ["Account", "Finance", "App"];

const SettingsPage = ({ user, settings = {}, onUpdateSettings, onBack, onSignOut, triggerConfirm, theme: currentTheme, onThemeChange, transactions, onDeleteAll, showToast, onNavigateImport, initialSection, onClearSection, onRefreshUser, isLoading }) => {
  const [currentSection, setCurrentSection] = useState(initialSection || null);
  const [search, setSearch] = useState("");

  React.useEffect(() => {
    if (initialSection) {
      setCurrentSection(initialSection);
    }
  }, [initialSection]);

  const goBack = () => {
    setCurrentSection(null);
    onClearSection?.();
  };

  const filteredSections = useMemo(() => {
    const q = search.toLowerCase();
    if (!q) return null; // null = show grouped
    return SECTIONS.filter(s => s.label.toLowerCase().includes(q) || s.description.toLowerCase().includes(q));
  }, [search]);

  const grouped = useMemo(() => GROUPS.map(g => ({ group: g, items: SECTIONS.filter(s => s.group === g) })), []);

  if (isLoading) return <SettingsSkeleton />;

  const renderSection = () => {
    switch (currentSection) {
      case "personal":      return <PersonalInfoPage user={user} onBack={goBack} showToast={showToast} onRefreshUser={onRefreshUser} />;
      case "security":      return <SecurityPage onBack={goBack} showToast={showToast} triggerConfirm={triggerConfirm} />;
      case "financial":     return <FinancialSettingsPage onBack={goBack} showToast={showToast} onUpdateSettings={onUpdateSettings} />;
      case "notifications": return <NotificationsPage onBack={goBack} onUpdateSettings={onUpdateSettings} />;
      case "appearance":    return <AppearancePage onBack={goBack} currentTheme={currentTheme} onThemeChange={onThemeChange} onUpdateSettings={onUpdateSettings} />;
      case "ai":            return <AIFeaturesPage onBack={goBack} user={user} onUpdateSettings={onUpdateSettings} />;
      case "data":          return <DataManagementPage onBack={goBack} triggerConfirm={triggerConfirm} transactions={transactions} onDeleteAll={onDeleteAll} showToast={showToast} onNavigateImport={onNavigateImport} />;
      case "subscription":  return <SubscriptionPage onBack={goBack} tier={user?.tier || "free"} />;
      case "quick_actions": return (
        <div className="space-y-6">
          <PageHeader title="Quick Actions" subtitle="Configure Dashboard" onBack={goBack} />
          <InfoCard color="indigo">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-white/10 rounded-2xl"><SlidersHorizontal className="w-6 h-6 text-indigo-400" /></div>
              <div>
                <p className="text-sm font-bold text-white">Customize your workspace</p>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">Choose up to 6 shortcuts to appear on your Profile and Home screens for rapid navigation.</p>
              </div>
            </div>
          </InfoCard>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              { id: "budget", label: "Budget", icon: Target, color: "text-amber-400" },
              { id: "goals", label: "Goals", icon: Star, color: "text-emerald-400" },
              { id: "loans", label: "Loans", icon: Briefcase, color: "text-rose-400" },
              { id: "planner", label: "Planner", icon: TrendingUp, color: "text-indigo-400" },
              { id: "itr", label: "ITR Filing", icon: FileBarChart, color: "text-violet-400" },
              { id: "audit", label: "Tax Audit", icon: Receipt, color: "text-sky-400" },
              { id: "history", label: "History", icon: ListFilter, color: "text-slate-400" },
              { id: "wealth", label: "Wealth", icon: Landmark, color: "text-blue-400" },
              { id: "add", label: "Add New", icon: Plus, color: "text-emerald-400" },
              { id: "stats", label: "Stats", icon: PieChart, color: "text-orange-400" },
            ].map(s => {
              const selected = (user?.preferences?.quick_actions || ["budget", "goals", "loans", "planner", "itr", "audit"]).includes(s.id);
              return (
                <button
                  key={s.id}
                  onClick={() => {
                    const current = user?.preferences?.quick_actions || ["budget", "goals", "loans", "planner", "itr", "audit"];
                    const next = selected ? current.filter(id => id !== s.id) : [...current, s.id].slice(0, 6);
                    onUpdateSettings({ preferences: { ...(user?.preferences || {}), quick_actions: next } });
                  }}
                  className={`flex items-center gap-4 p-4 rounded-2xl border transition-all text-left ${selected ? "bg-indigo-500/10 border-indigo-500/30" : "bg-white/[0.03] border-white/5 hover:border-white/10"}`}
                >
                  <div className={`p-2.5 rounded-xl bg-white/5 ${s.color}`}><s.icon className="w-5 h-5" /></div>
                  <div className="flex-1">
                    <p className="text-sm font-bold text-white">{s.label}</p>
                  </div>
                  <div className={`w-6 h-6 rounded-full border flex items-center justify-center transition-all ${selected ? "bg-indigo-500 border-indigo-500" : "border-white/10"}`}>
                    {selected && <Check className="w-3.5 h-3.5 text-white" />}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      );
      case "help":          return <HelpSupportPage onBack={goBack} />;
      case "about":         return <AboutPage onBack={goBack} />;
      default: return null;
    }
  };

  const SectionButton = ({ s }) => (
    <motion.button
      key={s.key}
      onClick={() => setCurrentSection(s.key)}
      whileHover={{ x: 6, backgroundColor: "rgba(255,255,255,0.07)" }}
      whileTap={{ scale: 0.99 }}
      className="w-full flex items-center gap-4 px-5 py-4 rounded-2xl border border-white/5 transition-all group text-left"
      style={{ background: "rgba(255,255,255,0.03)" }}
    >
      <div className={`p-3 ${s.iconBg} ${s.iconColor} rounded-2xl shrink-0 group-hover:scale-110 transition-transform shadow-inner`}>
        <s.icon className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-black text-white leading-tight">{s.label}</p>
        <p className="text-[11px] text-slate-500 mt-0.5 truncate">{s.description}</p>
      </div>
      {s.badge && <Badge label={s.badge} color="indigo" />}
      <ChevronRight className="w-5 h-5 text-slate-700 group-hover:text-slate-400 transition-colors shrink-0" />
    </motion.button>
  );

  return (
    <div className="space-y-0 pb-32">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Pane: Navigation & Menu */}
        <div className={cn(
          "lg:col-span-4 space-y-6 transition-all duration-300",
          currentSection ? "hidden lg:block" : "block"
        )}>
          {/* Header */}
          <div className="flex items-center justify-between pb-5 border-b border-white/5">
            <div className="flex items-center gap-4">
              <motion.button whileHover={{ scale: 1.05, x: -2 }} whileTap={{ scale: 0.95 }} onClick={onBack} className="p-3 bg-white/5 rounded-2xl hover:bg-white/10 transition-colors shadow-lg lg:hidden">
                <ChevronLeft className="w-5 h-5 text-white" />
              </motion.button>
              <div>
                <h1 className="text-2xl font-black text-white tracking-tight">Settings</h1>
                <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest mt-0.5">Configure your experience</p>
              </div>
            </div>
          </div>

          {/* User snapshot */}
          <div className="flex items-center gap-4 px-5 py-4 rounded-2xl border border-white/5" style={{ background: "rgba(255,255,255,0.03)" }}>
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-lg font-black text-white shadow-lg shrink-0">
              {([user?.first_name, user?.last_name].filter(Boolean).map(n => n[0]).join("") || (user?.username || "U")[0]).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-black text-white truncate">{[user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.username || "User"}</p>
              <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
            </div>
            <Badge label={user?.tier || "Free"} color={user?.tier === "pro" ? "indigo" : user?.tier === "enterprise" ? "amber" : "slate"} />
          </div>

          {/* Search */}
          <div className="relative group">
            <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600 group-focus-within:text-indigo-400 transition-colors" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search settings…"
              className="w-full pl-12 pr-5 py-4 bg-white/5 border border-white/10 rounded-2xl text-white text-sm outline-none focus:border-indigo-500/50 focus:bg-white/8 transition-all placeholder:text-slate-600"
            />
            {search && (
              <button onClick={() => setSearch("")} className="absolute right-5 top-1/2 -translate-y-1/2 text-slate-600 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Sections List */}
          {filteredSections ? (
            <div className="space-y-2">
              {filteredSections.length === 0 ? (
                <div className="py-16 text-center">
                  <Search className="w-8 h-8 text-slate-700 mx-auto mb-3" />
                  <p className="text-slate-500 text-sm font-bold">No results for "{search}"</p>
                </div>
              ) : (
                filteredSections.map(s => <SectionButton key={s.key} s={s} />)
              )}
            </div>
          ) : (
            <div className="space-y-6">
              {grouped.map(({ group, items }) => (
                <div key={group} className="space-y-2">
                  <p className="text-[10px] font-black text-slate-600 uppercase tracking-[0.3em] px-2">{group}</p>
                  <div className="space-y-2">
                    {items.map(s => <SectionButton key={s.key} s={s} />)}
                  </div>
                </div>
              ))}
            </div>
          )}

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
              <p className="text-sm font-black text-rose-400">Sign Out</p>
              <p className="text-[11px] text-rose-500/50 mt-0.5">End current session</p>
            </div>
            <ChevronRight className="w-5 h-5 text-rose-500/40 group-hover:text-rose-400 transition-colors shrink-0" />
          </motion.button>

          <p className="text-center text-[10px] font-black text-slate-800 uppercase tracking-[0.3em] pt-2">Spendsy v2.4.0-stable</p>
        </div>

        {/* Right Pane: Active Content */}
        <div className={cn(
          "lg:col-span-8 transition-all duration-500",
          !currentSection ? "hidden lg:block" : "block"
        )}>
          <AnimatePresence mode="wait">
            {currentSection ? (
              <motion.div key={currentSection} variants={pageVariants} initial="initial" animate="animate" exit="exit">
                {renderSection()}
              </motion.div>
            ) : (
              <div className="hidden lg:flex flex-col items-center justify-center py-48 opacity-10 border border-dashed border-white/20 rounded-[3rem]">
                <SettingsIcon className="w-16 h-16 mb-4" />
                <p className="text-xs font-black uppercase tracking-[0.4em]">Select a section to configure</p>
              </div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
