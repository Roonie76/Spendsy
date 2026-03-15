import React from "react";
import { motion } from "framer-motion";
import { 
  Landmark, 
  CreditCard as DebitCardIcon, 
  Zap,
  ChevronRight,
  ShieldCheck,
  TrendingUp
} from "lucide-react";
import { TABS } from "../../../../../packages/shared/config/constants";

const BankAccountsPage = ({ setActiveTab }) => {
  const options = [
    {
      id: TABS.DEBIT_CARDS,
      title: "Debit Cards",
      description: "Manage your checking accounts and daily spend cards.",
      icon: DebitCardIcon,
      color: "text-blue-400",
      bg: "bg-blue-500/10",
      border: "border-blue-500/20",
      shadow: "shadow-blue-500/5"
    },
    {
      id: TABS.CREDIT_CARDS,
      title: "Credit Cards",
      description: "Track limits, billing cycles, and rewards.",
      icon: Zap,
      color: "text-purple-400",
      bg: "bg-purple-500/10",
      border: "border-purple-500/20",
      shadow: "shadow-purple-500/5"
    }
  ];

  return (
    <div className="space-y-8 pb-28 animate-in slide-in-from-bottom-8">
      <div>
        <h1 className="text-2xl font-black text-white tracking-tight mb-2">Bank Accounts</h1>
        <p className="text-slate-400 text-sm font-medium">Manage your linked financial instruments</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {options.map((option, idx) => (
          <motion.button
            key={option.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            whileHover={{ scale: 1.02, translateY: -4 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setActiveTab(option.id)}
            className={`flex flex-col p-8 rounded-[2.5rem] bg-white/5 border ${option.border} border-white/5 text-left group transition-all ${option.shadow}`}
          >
            <div className={`p-4 ${option.bg} rounded-2xl w-fit mb-6 transition-transform group-hover:scale-110`}>
              <option.icon className={`w-8 h-8 ${option.color}`} />
            </div>
            
            <div className="flex-1">
              <h3 className="text-xl font-bold text-white mb-2">{option.title}</h3>
              <p className="text-slate-500 text-sm leading-relaxed mb-6 font-medium">
                {option.description}
              </p>
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-white/5">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-500" />
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Secure Link</span>
              </div>
              <ChevronRight className={`w-5 h-5 ${option.color} group-hover:translate-x-1 transition-transform`} />
            </div>
          </motion.button>
        ))}
      </div>

      {/* Security Banner */}
      <div className="p-6 bg-gradient-to-r from-emerald-500/10 to-teal-500/10 border border-emerald-500/20 rounded-[2rem] flex items-center gap-4">
        <div className="p-3 bg-emerald-500/20 rounded-xl text-emerald-400">
          <ShieldCheck className="w-6 h-6" />
        </div>
        <div>
          <p className="text-xs font-bold text-white uppercase tracking-wider mb-0.5">End-to-End Encryption</p>
          <p className="text-[10px] text-emerald-500/80 font-medium">Your card numbers are never stored in full. Only metadata for tracking.</p>
        </div>
      </div>
    </div>
  );
};

export default BankAccountsPage;
