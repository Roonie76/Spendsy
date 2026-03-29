import React, { useState } from 'react';
import { X, TrendingUp, Brain, Save, AlertCircle, Trash2 } from 'lucide-react';

export default function PlanDetailsDrawer({ plan, onClose, onAdjust, onDelete }) {
  const [adjustValue, setAdjustValue] = useState(plan?.monthly_saving || 0);

  if (!plan) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-[60] w-full max-w-md border-l border-white/10 bg-[#0b1220]/95 shadow-2xl backdrop-blur-xl transition-transform animate-in slide-in-from-right duration-300">
      <div className="flex items-center justify-between border-b border-white/10 px-6 py-4">
        <h2 className="text-xl font-bold text-white uppercase tracking-widest text-xs opacity-50">Plan Intelligence</h2>
        <button onClick={onClose} className="rounded-full p-2 text-slate-400 hover:bg-white/10 transition-colors">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="h-[calc(100vh-64px)] overflow-y-auto p-6 no-scrollbar">
        <div className="mb-8 rounded-3xl bg-gradient-to-br from-blue-600/10 to-purple-600/10 p-6 border border-white/5 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <Brain className="w-24 h-24" />
          </div>
          <div className="relative z-10">
            <h3 className="text-3xl font-black text-white mb-2">{plan.title}</h3>
            <div className="flex items-center gap-2 mb-6">
              <span className="px-2 py-0.5 rounded-lg bg-blue-500/20 text-blue-400 text-[10px] font-bold uppercase border border-blue-500/20">
                {plan.status.replace('_', ' ')}
              </span>
              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">
                Source: {plan.source}
              </span>
            </div>
            
            <div className="space-y-4">
              <div className="flex justify-between items-end">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Progress</span>
                <span className="text-lg font-black text-white">
                  {((plan.current_saved / plan.target_amount) * 100).toFixed(1)}%
                </span>
              </div>
              <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-blue-600 to-cyan-400"
                  style={{ width: `${(plan.current_saved / plan.target_amount) * 100}%` }}
                />
              </div>
              <div className="flex justify-between text-xs font-medium text-slate-400">
                <span>₹{plan.current_saved.toLocaleString()}</span>
                <span>₹{plan.target_amount.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 mb-8">
            <div className="p-4 rounded-2xl bg-white/5 border border-white/5">
                <p className="text-[10px] font-bold text-slate-500 uppercase mb-1">Target Date</p>
                <p className="text-lg font-bold text-white">{new Date(plan.deadline).toLocaleDateString()}</p>
            </div>
            <div className="p-4 rounded-2xl bg-white/5 border border-white/5">
                <p className="text-[10px] font-bold text-slate-500 uppercase mb-1">Daily Save</p>
                <p className="text-lg font-bold text-white">₹{plan.daily_saving.toFixed(0)}</p>
            </div>
        </div>

        <div className="mb-10">
          <h4 className="mb-4 text-[10px] font-bold uppercase tracking-widest text-slate-500 px-1">TORA AI Analysis</h4>
          <div className="rounded-2xl border border-blue-500/20 bg-blue-500/5 p-5">
            <p className="text-sm leading-relaxed text-slate-300 italic">
              "{plan.reasoning || "TORA has analyzed your spending habits and confirms this plan remains sustainable based on your average monthly surplus."}"
            </p>
          </div>
        </div>

        <div className="space-y-6">
          <div>
            <h4 className="mb-4 text-[10px] font-bold uppercase tracking-widest text-slate-500 px-1">Refine Strategy</h4>
            <div className="flex gap-3">
              <input 
                type="number"
                value={adjustValue}
                onChange={(e) => setAdjustValue(e.target.value)}
                className="flex-1 rounded-2xl border border-white/10 bg-white/5 px-4 py-4 text-white outline-none focus:border-blue-500 transition-all shadow-inner"
              />
              <button 
                onClick={() => onAdjust(plan.uid, { monthly_saving: adjustValue })}
                className="rounded-2xl bg-blue-600 px-6 py-4 font-bold text-white hover:bg-blue-700 transition-all active:scale-95 shadow-lg shadow-blue-600/20"
              >
                Apply
              </button>
            </div>
          </div>
          
          <button 
            onClick={() => {
              if (window.confirm("Permanently delete this financial plan?")) {
                onDelete(plan.uid);
              }
            }}
            className="w-full flex items-center justify-center gap-2 rounded-2xl bg-rose-500/10 border border-rose-500/20 py-4 font-bold text-rose-500 hover:bg-rose-500/20 transition-all"
          >
            <Trash2 className="h-4 w-4" />
            Delete Plan
          </button>
        </div>
      </div>
    </div>
  );
}
