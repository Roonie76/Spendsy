import React from "react";
import { motion } from "framer-motion";
import { 
  Briefcase, 
  ChevronLeft, 
  TrendingUp,
  Landmark,
  ShieldCheck,
  Zap
} from "lucide-react";
import { formatIndianCompact } from "@shared/utils/helpers";

const ActiveLoansPage = ({ wealthItems, onBack }) => {
  const loans = wealthItems.filter(item => item.type === "liability" || item.is_loan);

  const totalDebt = loans.reduce((acc, curr) => acc + parseFloat(curr.amount || 0), 0);

  return (
    <div className="space-y-8 pb-32">
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
          <h1 className="text-2xl font-black text-white tracking-tight">Active Loans</h1>
          <p className="text-slate-400 text-[10px] font-black uppercase tracking-widest mt-1">Manage your repayment schedules</p>
        </div>
      </div>

      {/* Debt Summary */}
      <div className="bg-gradient-to-br from-rose-900/40 to-slate-900/40 p-8 rounded-[2.5rem] border border-white/10 relative overflow-hidden group">
        <div className="absolute top-0 right-0 w-64 h-64 bg-rose-500/10 blur-[80px] rounded-full pointer-events-none group-hover:bg-rose-500/20 transition-colors duration-700"></div>
        <div className="relative z-10">
          <p className="text-[10px] text-rose-300 font-black uppercase tracking-[0.3em] mb-2">Total Outstanding</p>
          <h2 className="text-5xl font-black text-white tracking-tighter mb-4">
            ₹{totalDebt.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
          </h2>
          <div className="flex gap-4">
            <span className="px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-[10px] font-bold text-rose-400 uppercase tracking-wider">
               {loans.length} Active Accounts
            </span>
            <span className="px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[10px] font-bold text-indigo-400 uppercase tracking-wider">
               Avg. 9.5% APR
            </span>
          </div>
        </div>
      </div>

      {/* Loan List */}
      <div className="space-y-4">
        {loans.length === 0 ? (
           <div className="bg-white/5 p-12 rounded-[2.5rem] border border-white/5 text-center">
              <div className="p-4 bg-white/5 rounded-full w-fit mx-auto mb-4">
                 <ShieldCheck className="w-8 h-8 text-slate-500" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">No Active Loans</h3>
              <p className="text-slate-500 text-sm max-w-xs mx-auto">Your credit profile looks clean. New loans will appear here once registered.</p>
           </div>
        ) : (
          loans.map((loan, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              className="bg-white/5 backdrop-blur-xl p-6 rounded-3xl border border-white/10 flex items-center justify-between group hover:bg-white/10 transition-all border-l-4 border-l-rose-500"
            >
              <div className="flex items-center gap-5">
                <div className="p-4 bg-rose-500/10 rounded-2xl group-hover:scale-110 transition-transform">
                   <Landmark className="w-7 h-7 text-rose-400" />
                </div>
                <div>
                  <h4 className="text-lg font-black text-white leading-none">{loan.title || loan.bank_name}</h4>
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">₹{formatIndianCompact(loan.amount)} Remaining</span>
                    <span className="w-1 h-1 bg-slate-700 rounded-full"></span>
                    <span className="text-[10px] text-emerald-500 font-bold uppercase tracking-wider">Next EMI: 15 Apr</span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <p className="text-xs font-black text-white">₹{(parseFloat(loan.amount) / 12).toFixed(0)}/mo</p>
                <p className="text-[9px] text-slate-500 font-bold uppercase tracking-widest mt-1">EMI Auto-Pay</p>
              </div>
            </motion.div>
          ))
        )}
      </div>

      <motion.button
         whileHover={{ scale: 1.02 }}
         whileTap={{ scale: 0.98 }}
         className="w-full py-5 bg-white/5 border border-white/10 hover:bg-white/10 rounded-[2rem] text-slate-400 hover:text-white font-black uppercase text-xs tracking-widest transition-all mt-4 flex items-center justify-center gap-3"
      >
         <Zap className="w-4 h-4 text-amber-400" />
         Explore Refinance Options
      </motion.button>
    </div>
  );
};

export default ActiveLoansPage;
