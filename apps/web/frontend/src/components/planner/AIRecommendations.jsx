import React from 'react';
import { Sparkles, ArrowRight, TrendingUp, Zap } from 'lucide-react';

export default function AIRecommendations({ recommendations = [], onApply }) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-purple-400" />
          <h3 className="text-lg font-bold text-white">AI Recommendations</h3>
        </div>
        <span className="rounded-full bg-purple-500/20 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-purple-400 border border-purple-500/20">
          Live Analysis
        </span>
      </div>

      <div className="space-y-4">
        {recommendations.length > 0 ? recommendations.map((rec, idx) => (
          <div key={idx} className="group relative overflow-hidden rounded-2xl border border-white/5 bg-white/5 p-4 transition-all hover:bg-white/10">
            <div className={`absolute -right-4 -top-4 h-16 w-16 rounded-full ${idx === 0 ? 'bg-indigo-500' : 'bg-purple-500'} opacity-10 blur-2xl`} />
            <p className="mb-4 text-sm leading-relaxed text-slate-300">
              {rec.text}
            </p>
            <button 
              onClick={() => onApply(rec)}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-white/10 py-2.5 text-xs font-bold text-white transition-all hover:bg-white/20 active:scale-95"
            >
              Apply Strategy <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        )) : (
          <div className="py-8 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-white/5 text-slate-600">
              <Zap className="h-6 w-6" />
            </div>
            <p className="text-sm text-slate-500">No new recommendations</p>
          </div>
        )}
      </div>

      <div className="mt-6 rounded-2xl bg-gradient-to-br from-indigo-500/10 to-purple-500/10 p-4 border border-indigo-500/10">
        <div className="flex items-center gap-2 mb-2">
          <TrendingUp className="h-4 w-4 text-indigo-400" />
          <span className="text-xs font-bold text-indigo-300">Impact Predicted</span>
        </div>
        <p className="text-[11px] text-slate-400">
          Applying these strategies could improve your overall success rate by 12% across all active plans.
        </p>
      </div>
    </div>
  );
}
