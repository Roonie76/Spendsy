import React, { useState, useEffect } from 'react';
import { X, Brain, User, Send, Loader2, Sparkles, Receipt, PiggyBank } from 'lucide-react';
import { financeApi } from '../../api';

export default function CreatePlanModal({ isOpen, onClose, onCreate }) {
  const [mode, setMode] = useState('manual');
  const [planType, setPlanType] = useState('saving'); // 'saving' or 'debt'
  const [loans, setLoans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    target_amount: '',
    deadline: '',
    monthly_saving: '',
    loan_id: null
  });
  const [aiInput, setAiInput] = useState('');

  useEffect(() => {
    if (isOpen) {
      const fetchLoans = async () => {
        try {
          const resp = await financeApi.loans();
          setLoans(resp?.data || []);
        } catch (err) {
          console.error("Failed to fetch loans:", err);
        }
      };
      fetchLoans();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleLoanSelect = (e) => {
    const loanId = e.target.value;
    if (!loanId) {
      setFormData({ ...formData, loan_id: null });
      return;
    }
    const loan = loans.find(l => String(l.id) === loanId);
    if (loan) {
      setFormData({
        ...formData,
        loan_id: loan.id,
        title: `Repay ${loan.loan_type} Loan`,
        target_amount: loan.remaining_balance
      });
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onCreate({ ...formData, source: mode });
    onClose();
  };

  const handleAiAssistance = async () => {
    setLoading(true);
    // In a real app, this would call aiApi.chat
    setTimeout(() => {
      setFormData({
        title: "TORA Optimized Plan",
        target_amount: 50000,
        deadline: "2025-12-31",
        monthly_saving: 2500,
        loan_id: null
      });
      setMode('manual');
      setLoading(false);
    }, 1500);
  };

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 text-slate-200">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      
      <div className="relative w-full max-w-lg overflow-hidden rounded-3xl border border-white/10 bg-[#0b1220] shadow-2xl">
        <div className="flex items-center justify-between border-b border-white/10 px-6 py-4">
          <h2 className="text-xl font-bold text-white">New Financial Plan</h2>
          <button onClick={onClose} className="rounded-full p-2 text-slate-400 hover:bg-white/10">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-1 flex gap-1 bg-white/5 m-4 rounded-2xl border border-white/5">
          <button 
            onClick={() => setMode('manual')}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-bold transition-all ${mode === 'manual' ? 'bg-white/10 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <User className="h-3.5 w-3.5" /> Manual Entry
          </button>
          <button 
            onClick={() => setMode('ai')}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-bold transition-all ${mode === 'ai' ? 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <Brain className="h-3.5 w-3.5" /> AI Assisted <Sparkles className="h-2.5 w-2.5" />
          </button>
        </div>

        <div className="p-6 pt-2">
          {mode === 'manual' ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="flex gap-4 mb-4">
                <button
                  type="button"
                  onClick={() => { setPlanType('saving'); setFormData({...formData, loan_id: null}); }}
                  className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-2xl border transition-all ${planType === 'saving' ? 'bg-cyan-500/10 border-cyan-500/50 text-cyan-400' : 'bg-white/5 border-white/5 text-slate-500'}`}
                >
                  <PiggyBank className="w-4 h-4" />
                  <span className="text-sm font-bold">Savings Goal</span>
                </button>
                <button
                  type="button"
                  onClick={() => setPlanType('debt')}
                  className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-2xl border transition-all ${planType === 'debt' ? 'bg-rose-500/10 border-rose-500/50 text-rose-400' : 'bg-white/5 border-white/5 text-slate-500'}`}
                >
                  <Receipt className="w-4 h-4" />
                  <span className="text-sm font-bold">Debt Repayment</span>
                </button>
              </div>

              {planType === 'debt' && (
                <div className="space-y-1.5 animate-in fade-in slide-in-from-top-2 duration-300">
                  <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">Select Loan to Repay</label>
                  <select
                    required
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none focus:border-cyan-500 appearance-none"
                    value={formData.loan_id || ''}
                    onChange={handleLoanSelect}
                  >
                    <option value="" className="bg-[#0b1220]">-- Choose an active loan --</option>
                    {loans.map(loan => (
                      <option key={loan.id} value={loan.id} className="bg-[#0b1220]">
                        {loan.loan_type.toUpperCase()} Loan (Bal: ₹{Number(loan.remaining_balance).toLocaleString()})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">Plan Title</label>
                <input 
                  required
                  placeholder={planType === 'saving' ? "e.g. New MacBook Pro" : "e.g. Home Loan Payoff"}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none focus:border-cyan-500"
                  value={formData.title}
                  onChange={e => setFormData({...formData, title: e.target.value})}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                    {planType === 'saving' ? "Target Amount (₹)" : "Repayment Amount (₹)"}
                  </label>
                  <input 
                    required
                    type="number"
                    placeholder="50000"
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none focus:border-cyan-500"
                    value={formData.target_amount}
                    onChange={e => setFormData({...formData, target_amount: e.target.value})}
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">Extra Saving (₹/mo)</label>
                  <input 
                    required
                    type="number"
                    placeholder="2500"
                    className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none focus:border-cyan-500"
                    value={formData.monthly_saving}
                    onChange={e => setFormData({...formData, monthly_saving: e.target.value})}
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">Target Date</label>
                <input 
                  required
                  type="date"
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none focus:border-cyan-500"
                  value={formData.deadline}
                  onChange={e => setFormData({...formData, deadline: e.target.value})}
                />
              </div>
              <button 
                type="submit"
                className={`w-full mt-4 rounded-2xl py-4 text-sm font-bold text-white transition-all hover:opacity-90 active:scale-[0.98] ${planType === 'saving' ? 'bg-gradient-to-r from-cyan-500 to-blue-600' : 'bg-gradient-to-r from-rose-500 to-orange-600'}`}
              >
                Create {planType === 'saving' ? 'Savings' : 'Repayment'} Plan
              </button>
            </form>
          ) : (
            <div className="space-y-6 py-4">
              <div className="text-center">
                <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-indigo-500/20 text-indigo-400">
                  <Brain className="h-8 w-8" />
                </div>
                <h3 className="text-lg font-bold text-white">Describe Your Goal</h3>
                <p className="text-sm text-slate-400 px-8">TORA will analyze your debt and savings to calculate the best strategy for you.</p>
              </div>
              
              <div className="relative">
                <textarea 
                  rows={3}
                  placeholder="e.g. I want to pay off my car loan by end of this year. How much extra should I pay?"
                  className="w-full resize-none rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-white outline-none focus:border-indigo-500"
                  value={aiInput}
                  onChange={e => setAiInput(e.target.value)}
                />
                <button 
                  disabled={loading || !aiInput.trim()}
                  onClick={handleAiAssistance}
                  className="absolute bottom-3 right-3 rounded-xl bg-indigo-500 p-2 text-white transition hover:bg-indigo-400 disabled:opacity-50"
                >
                  {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
