import React from "react";
import { motion } from "framer-motion";
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
  LogOut,
  Database
} from "lucide-react";

const SettingsItem = ({ icon: Icon, label, value, onClick, color = "text-blue-400" }) => (
  <button 
    onClick={onClick}
    className="w-full flex items-center justify-between p-4 bg-white/5 hover:bg-white/10 rounded-2xl transition-colors group"
  >
    <div className="flex items-center gap-4">
      <div className={`p-2 bg-white/5 rounded-xl group-hover:scale-110 transition-transform ${color}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="text-left">
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{label}</p>
        <p className="text-sm font-bold text-white">{value}</p>
      </div>
    </div>
    <ChevronRight className="w-5 h-5 text-slate-700 group-hover:text-slate-400 transition-colors" />
  </button>
);

const SettingsSection = ({ title, children }) => (
  <div className="space-y-3">
    <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-4 mb-2">{title}</h3>
    <div className="space-y-2">{children}</div>
  </div>
);

const SettingsPage = ({ user, onBack, onSignOut, triggerConfirm }) => {
  return (
    <div className="space-y-8 pb-28 animate-in slide-in-from-bottom-8">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button 
          onClick={onBack}
          className="p-2 bg-white/5 rounded-xl hover:bg-white/10 transition-colors"
        >
          <ChevronLeft className="w-5 h-5 text-white" />
        </button>
        <h1 className="text-xl font-bold text-white">App Settings</h1>
      </div>

      {/* Account Settings */}
      <SettingsSection title="Account Settings">
        <SettingsItem icon={User} label="Display Name" value={user?.username || "Admin"} color="text-blue-400" />
        <SettingsItem icon={Mail} label="Email Address" value={user?.email || "user@example.com"} color="text-emerald-400" />
        <SettingsItem icon={Lock} label="Security" value="Update Password" color="text-purple-400" />
      </SettingsSection>

      {/* Personal Info */}
      <SettingsSection title="Personal Info">
        <SettingsItem icon={Phone} label="Phone Number" value="+91 98765 43210" color="text-sky-400" />
        <SettingsItem icon={HomeIcon} label="Primary Address" value="Chennai, India" color="text-indigo-400" />
        <SettingsItem icon={Briefcase} label="Occupation" value="Software Engineer" color="text-amber-400" />
      </SettingsSection>

      {/* App Preferences */}
      <SettingsSection title="App Preferences">
        <SettingsItem icon={Coins} label="Base Currency" value="INR (₹) - Indian Rupee" color="text-yellow-400" />
        <SettingsItem icon={Moon} label="App Theme" value="Dark Mode (OLED)" color="text-violet-400" />
        <SettingsItem icon={Bell} label="Notifications" value="Enabled (Push & Email)" color="text-rose-400" />
      </SettingsSection>

      {/* Security & Data */}
      <SettingsSection title="Security & Privacy">
        <SettingsItem icon={Database} label="Data Management" value="Export or Purge Records" color="text-slate-400" />
        <SettingsItem icon={Shield} label="Privacy Policy" value="v1.4 Updated Jan 2026" color="text-emerald-500" />
        <button 
          onClick={() => triggerConfirm("Are you sure you want to sign out?", onSignOut)}
          className="w-full flex items-center gap-4 p-4 bg-rose-500/5 hover:bg-rose-500/10 rounded-2xl transition-colors group mt-4 border border-rose-500/10"
        >
          <div className="p-2 bg-rose-500/10 rounded-xl text-rose-500">
            <LogOut className="w-5 h-5" />
          </div>
          <div className="text-left">
            <p className="text-[10px] font-bold text-rose-500/60 uppercase tracking-widest">Session</p>
            <p className="text-sm font-bold text-rose-500">Sign Out of Spendsy</p>
          </div>
        </button>
      </SettingsSection>

      {/* Footer Meta */}
      <div className="text-center px-4">
        <p className="text-[10px] font-bold text-slate-700 uppercase tracking-widest mb-1">Spendsy v2.4.0-stable</p>
        <p className="text-[8px] text-slate-800 font-medium tracking-tight">Financial Intelligence for Humans</p>
      </div>
    </div>
  );
};

export default SettingsPage;
