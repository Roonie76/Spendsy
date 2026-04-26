import React, { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Briefcase,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  Landmark,
  ShieldCheck,
  Zap,
  Calendar,
  Percent,
  Clock
} from "lucide-react";
import { formatIndianCompact } from "@shared/utils/helpers";
import { TABS } from "@shared/config/constants";
import { financeApi } from "../api";

// --- Amortization Modal ---
const AmortizationModal = ({ loan, onClose }) => {
  const principal = parseFloat(loan.remaining_balance || loan.principal_amount || 0);
  const rate = parseFloat(loan.interest_rate || 0) / 100 / 12;
  const emi = parseFloat(loan.emi_amount || 0);
  
  const schedule = React.useMemo(() => {
    let balance = principal;
    const rows = [];
    // Calculate for next 12 months only for UI brevity, or full tenure if small
    for (let i = 1; i <= 24; i++) {
      if (balance <= 0) break;
      const interest = balance * rate;
      const principalRepayment = Math.min(balance, emi - interest);
      balance -= principalRepayment;
      rows.push({
        month: i,
        interest,
        principal: principalRepayment,
        balance: Math.max(0, balance)
      });
    }
    return rows;
  }, [principal, rate, emi]);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <motion.div 
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="bg-slate-900 border border-white/10 w-full max-w-lg rounded-[2.5rem] overflow-hidden shadow-2xl flex flex-col max-h-[80vh]"
      >
        <div className="p-6 border-b border-white/5 flex justify-between items-center">
          <div>
            <h3 className="text-xl font-black text-white">Amortization Schedule</h3>
            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1">Projected Repayment Flow</p>
          </div>
          <button onClick={onClose} className="p-2 bg-white/5 hover:bg-white/10 rounded-full text-slate-400">
            <Clock className="w-5 h-5 rotate-45" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
          <table className="w-full text-left">
            <thead>
              <tr className="text-[10px] font-black text-slate-500 uppercase tracking-widest border-b border-white/5">
                <th className="pb-4">Mo.</th>
                <th className="pb-4">Principal</th>
                <th className="pb-4">Interest</th>
                <th className="pb-4 text-right">Balance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {schedule.map((row) => (
                <tr key={row.month} className="group/row">
                  <td className="py-4 text-xs font-bold text-slate-500">{row.month}</td>
                  <td className="py-4 text-xs font-bold text-white">{formatIndianCompact(row.principal)}</td>
                  <td className="py-4 text-xs font-bold text-rose-400">{formatIndianCompact(row.interest)}</td>
                  <td className="py-4 text-xs font-black text-emerald-400 text-right">{formatIndianCompact(row.balance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-6 text-[10px] text-slate-600 italic text-center">Showing next 24 months of projected repayments</p>
        </div>
      </motion.div>
    </div>
  );
};

const ActiveLoansPage = ({ wealthItems, onBack, setActiveTab }) => {
  const [loans, setLoans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedLoan, setSelectedLoan] = useState(null);

  const fetchLoans = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await financeApi.loans();
      const data = resp?.data || resp;
      setLoans(Array.isArray(data) ? data : []);
    } catch {
      setLoans(wealthItems.filter(item => item.type === "liability" || item.is_loan));
    } finally {
      setLoading(false);
    }
  }, [wealthItems]);

  useEffect(() => { fetchLoans(); }, [fetchLoans]);

  const totalDebt = loans.reduce((acc, curr) => acc + parseFloat(curr.remaining_balance || curr.amount || 0), 0);
  const totalEmi = loans.reduce((acc, curr) => acc + parseFloat(curr.emi_amount || 0), 0);

  return (
    <div className="space-y-8 pb-32">
      {selectedLoan && <AmortizationModal loan={selectedLoan} onClose={() => setSelectedLoan(null)} />}
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
      <div className="bg-gradient-to-br from-rose-900/40 to-slate-900/40 p-5 sm:p-8 rounded-[2rem] sm:rounded-[2.5rem] border border-white/10 relative overflow-hidden group">
        <div className="absolute top-0 right-0 w-64 h-64 bg-rose-500/10 blur-[80px] rounded-full pointer-events-none group-hover:bg-rose-500/20 transition-colors duration-700"></div>
        <div className="relative z-10">
          <p className="text-[10px] text-rose-300 font-black uppercase tracking-[0.3em] mb-2">Total Outstanding</p>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-white tracking-tighter mb-4 break-all">
            ₹{totalDebt.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
          </h2>
          <div className="flex gap-4 flex-wrap">
            <span className="px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20 text-[10px] font-bold text-rose-400 uppercase tracking-wider">
               {loans.length} Active Loan{loans.length !== 1 ? "s" : ""}
            </span>
            {totalEmi > 0 && (
              <span className="px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[10px] font-bold text-indigo-400 uppercase tracking-wider">
                 {formatIndianCompact(totalEmi)}/mo Total EMI
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Loan List */}
      <div className="space-y-4">
        {loading ? (
          <div className="space-y-4">
            {[1, 2].map(n => (
              <div key={n} className="h-40 animate-pulse rounded-3xl bg-white/5 border border-white/10" />
            ))}
          </div>
        ) : loans.length === 0 ? (
           <div className="bg-white/5 p-12 rounded-[2.5rem] border border-white/5 text-center">
              <div className="p-4 bg-white/5 rounded-full w-fit mx-auto mb-4">
                 <ShieldCheck className="w-8 h-8 text-slate-500" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">No Active Loans</h3>
              <p className="text-slate-500 text-sm max-w-xs mx-auto">Your credit profile looks clean. New loans will appear here once registered.</p>
           </div>
        ) : (
          loans.map((loan, idx) => {
            const principal = parseFloat(loan.principal_amount || loan.amount || 0);
            const remaining = parseFloat(loan.remaining_balance || loan.amount || 0);
            const emi = parseFloat(loan.emi_amount || 0);
            const rate = parseFloat(loan.interest_rate || 0);
            const repaidPercent = principal > 0 ? Math.min(100, ((principal - remaining) / principal) * 100) : 0;
            const monthsLeft = emi > 0 ? Math.ceil(remaining / emi) : 0;

            return (
              <motion.div
                key={loan.uid || loan.id || idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="bg-white/5 backdrop-blur-xl p-6 rounded-3xl border border-white/10 group hover:bg-white/10 transition-all border-l-4 border-l-rose-500 space-y-4"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-5">
                    <div className="p-4 bg-rose-500/10 rounded-2xl group-hover:scale-110 transition-transform shrink-0">
                      <Landmark className="w-7 h-7 text-rose-400" />
                    </div>
                    <div>
                      <h4 className="text-lg font-black text-white leading-none">
                        {loan.loan_type ? `${loan.loan_type.charAt(0).toUpperCase() + loan.loan_type.slice(1)} Loan` : loan.title || loan.bank_name}
                      </h4>
                      {loan.bank_name && <p className="text-[11px] text-slate-500 font-medium mt-1">{loan.bank_name}</p>}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    {emi > 0 && <p className="text-sm font-black text-white">{formatIndianCompact(emi)}/mo</p>}
                    {rate > 0 && (
                      <div className="flex items-center gap-1 justify-end mt-1">
                        <Percent className="w-3 h-3 text-slate-500" />
                        <span className="text-[10px] text-slate-500 font-bold">{rate}% APR</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Repayment Progress */}
                <div>
                  <div className="flex justify-between text-[10px] font-bold uppercase tracking-wider mb-2">
                    <span className="text-emerald-400">{repaidPercent.toFixed(0)}% Repaid</span>
                    <span className="text-slate-500">{formatIndianCompact(remaining)} remaining</span>
                  </div>
                  <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${repaidPercent}%` }}
                      transition={{ duration: 1, ease: "circOut" }}
                      className="h-full bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-full"
                    />
                  </div>
                </div>

                <div className="flex justify-between items-center">
                  <div className="flex gap-4 flex-wrap">
                    {principal > 0 && (
                      <span className="px-2 py-1 rounded-lg bg-white/5 text-[10px] font-bold text-slate-400 flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" /> Principal: {formatIndianCompact(principal)}
                      </span>
                    )}
                    {monthsLeft > 0 && (
                      <span className="px-2 py-1 rounded-lg bg-white/5 text-[10px] font-bold text-slate-400 flex items-center gap-1">
                        <Clock className="w-3 h-3" /> ~{monthsLeft} months left
                      </span>
                    )}
                  </div>
                  <button 
                    onClick={() => setSelectedLoan(loan)}
                    className="px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-xl text-[10px] font-black text-white uppercase tracking-widest transition-colors flex items-center gap-2"
                  >
                    View Schedule <ChevronRight className="w-3 h-3" />
                  </button>
                </div>
              </motion.div>
            );
          })
        )}
      </div>

      <motion.button
         whileHover={{ scale: 1.02 }}
         whileTap={{ scale: 0.98 }}
         onClick={() => setActiveTab(TABS.CHAT)}
         className="w-full py-5 bg-white/5 border border-white/10 hover:bg-white/10 rounded-[2rem] text-slate-400 hover:text-white font-black uppercase text-xs tracking-widest transition-all mt-4 flex items-center justify-center gap-3"
      >
         <Zap className="w-4 h-4 text-amber-400" />
         Explore Refinance Options
      </motion.button>
    </div>
  );
};

export default ActiveLoansPage;
