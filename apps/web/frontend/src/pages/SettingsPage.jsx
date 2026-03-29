import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  User, 
  Mail, 
  Lock, 
  Phone, 
  Home as HomeIcon, 
  Briefcase, 
  Coins, 
  Moon, 
  Bell, 
  Shield, 
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  LogOut,
  Database,
  Edit2,
  Save,
  X
} from "lucide-react";

const CURRENCY_OPTIONS = [
  "INR (₹) - Indian Rupee",
  "USD ($) - US Dollar",
  "EUR (€) - Euro",
  "GBP (£) - British Pound",
  "AUD (A$) - Australian Dollar",
  "CAD (C$) - Canadian Dollar",
  "SGD (S$) - Singapore Dollar",
  "JPY (¥) - Japanese Yen",
];

const OCCUPATION_OPTIONS = [
  "Software Engineer",
  "Business Owner",
  "Freelancer",
  "Student",
  "Healthcare Professional",
  "Educator",
  "Creative Professional",
];

const COUNTRY_OPTIONS = [
  "India",
  "United States",
  "United Kingdom",
  "Australia",
  "Canada",
  "Singapore",
];

const SettingsItem = ({ icon: Icon, label, value, type = "text", isEditing, onChange, color = "text-blue-400", focusGlow = "rgba(59,130,246,0.3)", options, customInput, allowOther = true }) => (
  <motion.div 
    layout
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, scale: 0.95 }}
    transition={{ type: "spring", stiffness: 400, damping: 30 }}
    className={isEditing && onChange 
      ? `w-full p-5 bg-black/20 backdrop-blur-xl rounded-[2rem] border border-white/10 relative group transition-all duration-300 focus-within:border-white/20 hover:border-white/20 focus-within:bg-white/5`
      : "w-full flex items-center justify-between p-4 bg-white/5 hover:bg-white/10 rounded-2xl transition-all group cursor-pointer"}
  >
    <div className={`flex ${isEditing && onChange ? 'flex-col gap-3' : 'items-center gap-4'} w-full`}>
      <div className={`flex items-center gap-3 ${isEditing && onChange ? 'opacity-80 ml-1' : ''}`}>
        <div className={`p-2 bg-white/5 rounded-xl group-hover:scale-110 transition-transform ${color} shrink-0`}>
          <Icon className="w-5 h-5" />
        </div>
        {(!isEditing || !onChange) && (
          <div className="text-left flex-1 mr-4">
            <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest leading-tight">{label}</p>
            <p className="text-sm font-bold text-white mt-0.5">{type === "password" ? "••••••••" : value}</p>
          </div>
        )}
        {(isEditing && onChange) && (
          <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 leading-tight">{label}</p>
        )}
      </div>

      {(isEditing && onChange) && (
        <div className="w-full flex flex-col gap-3">
          {customInput ? customInput : (
            <div 
              className="relative rounded-[1.5rem] transition-all duration-300"
              style={{ boxShadow: `0 0 0 0 ${focusGlow}` }}
              onFocus={(e) => e.currentTarget.style.boxShadow = `0 0 20px -5px ${focusGlow}`}
              onBlur={(e) => e.currentTarget.style.boxShadow = `0 0 0 0 ${focusGlow}`}
            >
              {options ? (
                <div className="relative">
                  <select
                    value={(options.includes(value) || !allowOther) ? value : "Other"}
                    onChange={(e) => onChange(e.target.value === "Other" ? "" : e.target.value)}
                    className="w-full bg-black/40 border-2 border-white/5 rounded-[1.5rem] px-5 py-3.5 text-base font-black text-white outline-none focus:border-white/20 focus:bg-white/5 transition-all shadow-inner appearance-none relative z-10"
                  >
                    <option value="" disabled className="bg-slate-900 text-slate-400">Select an option</option>
                    {options.map(opt => <option key={opt} value={opt} className="bg-slate-900 text-white">{opt}</option>)}
                    {allowOther && <option value="Other" className="bg-slate-900 text-white">Other (Specify)</option>}
                  </select>
                  <ChevronDown className="w-5 h-5 absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 z-0" />
                </div>
              ) : (
                <input
                  type={type}
                  value={value || ""}
                  onChange={(e) => onChange(e.target.value)}
                  className="w-full bg-black/40 border-2 border-white/5 rounded-[1.5rem] px-5 py-3.5 text-base font-black text-white outline-none focus:border-white/20 focus:bg-white/5 transition-all shadow-inner placeholder:text-slate-600"
                  placeholder={`Enter ${label}`}
                />
              )}
            </div>
          )}
          
          {/* Fallback to custom input if "Other" is chosen and it's not customInput handled */}
          {(options && allowOther && !options.includes(value) && value !== undefined && !customInput) && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="relative rounded-[1.5rem] transition-all duration-300"
              style={{ boxShadow: `0 0 0 0 ${focusGlow}` }}
              onFocus={(e) => e.currentTarget.style.boxShadow = `0 0 20px -5px ${focusGlow}`}
              onBlur={(e) => e.currentTarget.style.boxShadow = `0 0 0 0 ${focusGlow}`}
            >
              <input
                type="text"
                value={value || ""}
                onChange={(e) => onChange(e.target.value)}
                className="w-full bg-black/40 border-2 border-white/5 rounded-[1.5rem] px-5 py-3.5 text-base font-black text-white outline-none focus:border-emerald-500/50 focus:bg-emerald-500/5 transition-all shadow-inner placeholder:text-slate-500"
                placeholder="Type your custom value..."
                autoFocus
              />
            </motion.div>
          )}
        </div>
      )}
    </div>
    {!isEditing && <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-white group-hover:translate-x-1 transition-all shrink-0" />}
  </motion.div>
);

const SettingsSection = ({ title, children }) => (
  <div className="space-y-4">
    <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.3em] px-4 mb-3">{title}</h3>
    <div className="space-y-3">{children}</div>
  </div>
);

const SettingsPage = ({ user, settings = {}, onUpdateSettings, onBack, onSignOut, triggerConfirm }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [localSettings, setLocalSettings] = useState({
    username: user?.username || "Admin",
    email: user?.email || "user@example.com",
    security: "", // New password
    phoneNumber: settings.phoneNumber || "+91 98765 43210",
    addressState: settings.addressState || "Tamil Nadu",
    addressCountry: settings.addressCountry || "India",
    addressCustom: settings.addressCustom || "",
    occupation: settings.occupation || "Software Engineer",
    baseCurrency: settings.baseCurrency || "INR (₹) - Indian Rupee",
    theme: settings.theme || "Dark Mode (OLED)",
    notifications: settings.notifications || "Enabled (Push & Email)"
  });

  const handleSave = async () => {
    if (onUpdateSettings) {
      await onUpdateSettings(localSettings);
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setLocalSettings({
      username: user?.username || "Admin",
      email: user?.email || "user@example.com",
      security: "",
      phoneNumber: settings.phoneNumber || "+91 98765 43210",
      addressState: settings.addressState || "Tamil Nadu",
      addressCountry: settings.addressCountry || "India",
      addressCustom: settings.addressCustom || "",
      occupation: settings.occupation || "Software Engineer",
      baseCurrency: settings.baseCurrency || "INR (₹) - Indian Rupee",
      theme: settings.theme || "Dark Mode (OLED)",
      notifications: settings.notifications || "Enabled (Push & Email)"
    });
    setIsEditing(false);
  };

  const updateField = (field, value) => {
    setLocalSettings(prev => ({ ...prev, [field]: value }));
  };

  // Format Address for display
  const displayAddress = localSettings.addressCountry === "Other" 
    ? localSettings.addressCustom 
    : `${localSettings.addressState}, ${localSettings.addressCountry}`;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-8 pb-28"
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-white/5">
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
            <h1 className="text-2xl font-black text-white tracking-tight">App Settings</h1>
            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-1">Configure your experience</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <AnimatePresence mode="wait">
            {isEditing ? (
              <motion.div 
                key="edit-actions"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="flex gap-2"
              >
                <motion.button 
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleCancel}
                  className="flex items-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-white rounded-2xl transition-colors text-xs font-black uppercase tracking-wider"
                >
                  <X className="w-4 h-4" />
                  Cancel
                </motion.button>
                <motion.button 
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleSave}
                  className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white rounded-2xl shadow-lg shadow-indigo-500/20 transition-all text-xs font-black uppercase tracking-wider relative overflow-hidden group"
                >
                  <span className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300"></span>
                  <Save className="w-4 h-4 relative z-10" />
                  <span className="relative z-10">Save</span>
                </motion.button>
              </motion.div>
            ) : (
              <motion.button 
                key="edit-btn"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setIsEditing(true)}
                className="flex items-center gap-2 px-5 py-2.5 bg-white/10 hover:bg-white/20 text-white rounded-2xl transition-colors text-xs font-black uppercase tracking-wider shadow-lg"
              >
                <Edit2 className="w-4 h-4" />
                Edit Profile
              </motion.button>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Account Settings */}
      <SettingsSection title="Account Settings">
        <AnimatePresence>
          <SettingsItem 
            icon={User} 
            label="Display Name" 
            value={localSettings.username} 
            isEditing={isEditing}
            onChange={(val) => updateField('username', val)}
            color="text-blue-400" 
            focusGlow="rgba(96,165,250,0.3)"
          />
          <SettingsItem 
            icon={Mail} 
            label="Email Address" 
            value={localSettings.email} 
            type="email"
            isEditing={isEditing}
            onChange={(val) => updateField('email', val)}
            color="text-emerald-400" 
            focusGlow="rgba(52,211,153,0.3)"
          />
          <SettingsItem 
            icon={Lock} 
            label="Security (New Password)" 
            value={localSettings.security} 
            type="password"
            isEditing={isEditing}
            onChange={(val) => updateField('security', val)}
            color="text-purple-400" 
            focusGlow="rgba(192,132,252,0.3)"
          />
        </AnimatePresence>
      </SettingsSection>

      {/* Personal Info */}
      <SettingsSection title="Personal Info">
        <AnimatePresence>
          <SettingsItem 
            icon={Phone} 
            label="Phone Number" 
            value={localSettings.phoneNumber} 
            isEditing={isEditing}
            onChange={(val) => updateField('phoneNumber', val)}
            color="text-sky-400" 
            focusGlow="rgba(56,189,248,0.3)"
          />
          <SettingsItem 
            icon={HomeIcon} 
            label="Primary Address" 
            value={displayAddress} 
            isEditing={isEditing}
            onChange={(val) => {}} // handled by customInput
            color="text-indigo-400" 
            focusGlow="rgba(129,140,248,0.3)"
            customInput={
              <div className="flex flex-col gap-3 w-full">
                <div className="flex gap-3">
                  <div className="relative flex-1">
                    <select
                      value={COUNTRY_OPTIONS.includes(localSettings.addressCountry) ? localSettings.addressCountry : "Other"}
                      onChange={(e) => updateField('addressCountry', e.target.value)}
                      className="w-full bg-black/40 border-2 border-white/5 rounded-[1.5rem] px-5 py-3.5 text-base font-black text-white outline-none focus:border-white/20 focus:bg-white/5 transition-all shadow-inner appearance-none relative z-10"
                    >
                      {COUNTRY_OPTIONS.map(opt => <option key={opt} value={opt} className="bg-slate-900">{opt}</option>)}
                      <option value="Other" className="bg-slate-900">Other (Specify)</option>
                    </select>
                    <ChevronDown className="w-5 h-5 absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 z-0" />
                  </div>
                  {localSettings.addressCountry !== "Other" && (
                    <div className="flex-1">
                      <input
                        type="text"
                        value={localSettings.addressState}
                        onChange={(e) => updateField('addressState', e.target.value)}
                        className="w-full bg-black/40 border-2 border-white/5 rounded-[1.5rem] px-5 py-3.5 text-base font-black text-white outline-none focus:border-white/20 transition-all shadow-inner placeholder:text-slate-600"
                        placeholder="State / Region"
                      />
                    </div>
                  )}
                </div>
                {localSettings.addressCountry === "Other" && (
                  <input
                    type="text"
                    value={localSettings.addressCustom}
                    onChange={(e) => updateField('addressCustom', e.target.value)}
                    className="w-full bg-black/40 border-2 border-white/5 rounded-[1.5rem] px-5 py-3.5 text-base font-black text-white outline-none focus:border-emerald-500/50 transition-all shadow-inner placeholder:text-slate-500"
                    placeholder="Enter full custom address..."
                    autoFocus
                  />
                )}
              </div>
            }
          />
          <SettingsItem 
            icon={Briefcase} 
            label="Occupation" 
            value={localSettings.occupation} 
            isEditing={isEditing}
            onChange={(val) => updateField('occupation', val)}
            color="text-amber-400" 
            focusGlow="rgba(251,191,36,0.3)"
            options={OCCUPATION_OPTIONS}
          />
        </AnimatePresence>
      </SettingsSection>

      {/* App Preferences */}
      <SettingsSection title="App Preferences">
        <AnimatePresence>
          <SettingsItem 
            icon={Coins} 
            label="Base Currency" 
            value={localSettings.baseCurrency} 
            isEditing={isEditing}
            onChange={(val) => updateField('baseCurrency', val)}
            color="text-yellow-400" 
            focusGlow="rgba(250,204,21,0.3)"
            options={CURRENCY_OPTIONS}
            allowOther={false}
          />
          <SettingsItem 
            icon={Moon} 
            label="App Theme" 
            value={localSettings.theme} 
            isEditing={isEditing}
            onChange={(val) => updateField('theme', val)}
            color="text-violet-400" 
            focusGlow="rgba(167,139,250,0.3)"
          />
          <SettingsItem 
            icon={Bell} 
            label="Notifications" 
            value={localSettings.notifications} 
            isEditing={isEditing}
            onChange={(val) => updateField('notifications', val)}
            color="text-rose-400" 
            focusGlow="rgba(251,113,133,0.3)"
          />
        </AnimatePresence>
      </SettingsSection>

      {/* Security & Data */}
      <SettingsSection title="Security & Privacy">
        <SettingsItem icon={Database} label="Data Management" value="Export or Purge Records" color="text-slate-400" />
        <SettingsItem icon={Shield} label="Privacy Policy" value="v1.4 Updated Jan 2026" color="text-emerald-500" />
        
        <motion.button 
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          onClick={() => triggerConfirm("Are you sure you want to sign out?", onSignOut)}
          className="w-full flex items-center justify-between p-5 bg-rose-500/5 hover:bg-rose-500/10 rounded-[2rem] transition-colors group mt-6 border border-rose-500/10 shadow-lg"
        >
          <div className="flex items-center gap-4">
            <div className="p-3 bg-rose-500/10 rounded-2xl text-rose-500 group-hover:scale-110 transition-transform">
              <LogOut className="w-6 h-6" />
            </div>
            <div className="text-left">
              <p className="text-[10px] font-black text-rose-500/60 uppercase tracking-widest leading-tight">Session Actions</p>
              <p className="text-base font-black text-rose-500 mt-0.5">Sign Out of Spendsy</p>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-rose-500/50 group-hover:text-rose-400 group-hover:translate-x-1 transition-all" />
        </motion.button>
      </SettingsSection>

      {/* Footer Meta */}
      <div className="text-center px-4 pt-8">
        <p className="text-[10px] font-black text-slate-700 uppercase tracking-widest mb-2">Spendsy v2.4.0-stable</p>
        <div className="h-1 w-8 bg-slate-800 rounded-full mx-auto"></div>
      </div>
    </motion.div>
  );
};

export default SettingsPage;
