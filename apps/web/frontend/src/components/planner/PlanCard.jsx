import React from 'react';
import { Calendar, Brain, User, ArrowRight, Receipt } from 'lucide-react';
import { motion } from 'framer-motion';

export default function PlanCard({ plan, onClick }) {
  const { title, target_amount, current_saved, deadline, daily_saving, status, source, loan_id } = plan;
  const progress = Math.min(100, (current_saved / target_amount) * 100);
  
  const statusColors = {
    on_track: "bg-emerald-500/20 text-emerald-400 border-emerald-500/20",
    risk: "bg-amber-500/20 text-amber-400 border-amber-500/20",
    delayed: "bg-rose-500/20 text-rose-400 border-rose-500/20",
    completed: "bg-blue-500/20 text-blue-400 border-blue-500/20"
  };

  return (
    <div 
      onClick={() => onClick(plan)}
      className="group relative cursor-pointer overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-5 transition-all hover:bg-white/10"
    >
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h3 className="text-lg font-bold text-white group-hover:text-cyan-400 transition-colors">{title}</h3>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${statusColors[status] || statusColors.on_track}`}>
              {status.replace('_', ' ')}
            </span>
            <span className="flex items-center gap-1 text-[10px] text-slate-500">
              {source === 'ai' ? <Brain className="h-3 w-3 text-purple-400" /> : <User className="h-3 w-3 text-cyan-400" />}
              {source.toUpperCase()}
            </span>
            {loan_id && (
              <span className="flex items-center gap-1 rounded-full bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 text-[10px] font-bold text-rose-400 uppercase tracking-wider">
                <Receipt className="h-2.5 w-2.5" /> DEBT
              </span>
            )}
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500 font-medium">{loan_id ? "Balance" : "Target"}</p>
          <p className="text-lg font-bold text-white">₹{(target_amount/1000).toFixed(1)}k</p>
        </div>
      </div>

      <div className="mb-4">
        <div className="mb-2 flex justify-between text-[10px] font-bold uppercase tracking-widest opacity-40">
          <span>{loan_id ? "Repayment Progress" : "Target Progress"}</span>
          <span>{progress.toFixed(0)}%</span>
        </div>
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/5">
          <motion.div 
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            className={`h-full bg-gradient-to-r ${loan_id ? 'from-rose-600 to-orange-500 shadow-[0_0_10px_rgba(225,29,72,0.3)]' : status === 'on_track' ? 'from-blue-600 to-cyan-400 shadow-[0_0_10px_rgba(59,130,246,0.3)]' : 'from-amber-500 to-rose-500 shadow-[0_0_10_rgba(245,158,11,0.3)]'}`} 
          />
        </div>
      </div>

      <div className="flex items-center justify-between rounded-2xl bg-black/20 p-3">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-slate-400" />
          <span className="text-xs text-slate-200">{new Date(deadline).toLocaleDateString()}</span>
        </div>
        <div className="text-right">
          <p className="text-[10px] text-slate-500">{loan_id ? "Extra Save" : "Daily Save"}</p>
          <p className="text-sm font-bold text-white">₹{daily_saving.toFixed(0)}</p>
        </div>
      </div>


      <div className="absolute right-3 top-1/2 -translate-y-1/2 opacity-0 transition-all group-hover:translate-x-1 group-hover:opacity-100">
        <ArrowRight className="h-5 w-5 text-cyan-400" />
      </div>
    </div>
  );
}
