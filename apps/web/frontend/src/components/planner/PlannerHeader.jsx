import React from 'react';
import { Plus, Target, TrendingUp, ShieldCheck, Zap } from 'lucide-react';

export default function PlannerHeader({ totalPlans = 0, monthlyCommitment = 0, successRate = 0, aiInfluenceScore = 0, onCreateClick }) {
  const StatCard = ({ icon: Icon, label, value, color }) => (
    <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-md">
      <div className={`absolute -right-2 -top-2 h-12 w-12 rounded-full ${color} opacity-20 blur-2xl`} />
      <div className="flex items-center gap-3">
        <div className={`rounded-xl bg-white/10 p-2 ${color.replace('bg-', 'text-')}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs text-slate-400">{label}</p>
          <p className="text-lg font-bold text-white">{value}</p>
        </div>
      </div>
    </div>
  );

  return (
    <div className="mb-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Financial Planner</h1>
          <p className="text-slate-400">Strategic goals powered by TORA AI</p>
        </div>
        <button
          onClick={onCreateClick}
          className="flex items-center gap-2 rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 px-6 py-3 text-sm font-bold text-white shadow-lg transition-all hover:scale-105 hover:shadow-cyan-500/25 active:scale-95"
        >
          <Plus className="h-4 w-4" />
          Create New Plan
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Target} label="Active Plans" value={totalPlans} color="bg-cyan-500" />
        <StatCard icon={TrendingUp} label="Monthly Target" value={`₹${monthlyCommitment.toLocaleString()}`} color="bg-indigo-500" />
        <StatCard icon={ShieldCheck} label="Success Rate" value={`${successRate}%`} color="bg-emerald-500" />
        <StatCard icon={Zap} label="AI Influence" value={`${aiInfluenceScore}%`} color="bg-purple-500" />
      </div>
    </div>
  );
}
