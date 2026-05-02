import React, { useState, useEffect } from 'react';
import { X, Calendar, IndianRupee, Type, ShieldAlert, ArrowLeftRight, Zap } from 'lucide-react';
import { CATEGORIES } from '@shared/config/constants';
import { normalizeDate, formatLocalDate } from '@shared/utils/helpers';
import { apiFetch } from '../../api';

const EditTransactionModal = ({ isOpen, onClose, transaction, onSave, apiBaseUrl, onTransferFlagChanged }) => {
    // 1. Better Initial State: Fallback to empty strings to prevent "Controlled to Uncontrolled" warnings
    const [formData, setFormData] = useState({
        amount: '',
        description: '',
        category: '',
        type: 'expense',
        date: formatLocalDate(new Date()),
        is_recurring: false
    });
    
    const isOriginalVerified = transaction?.confidence > 0;
    const [showWarning, setShowWarning] = useState(false);
    const [isTransfer, setIsTransfer] = useState(false);
    const [transferBusy, setTransferBusy] = useState(false);

    useEffect(() => {
        if (transaction && isOpen) {
            setFormData({
                id: transaction.id,
                uid: transaction.uid,
                amount: transaction.amount || '',
                // Check both description and title to be safe
                description: transaction.description || transaction.title || '',
                category: transaction.category || 'other',
                type: transaction.type || 'expense',
                date: formatLocalDate(transaction.date),
                is_recurring: !!transaction.is_recurring
            });
            setShowWarning(false);
            setIsTransfer(!!transaction.is_transfer);
        }
    }, [transaction, isOpen]);

    const toggleTransferFlag = async () => {
        if (!transaction?.uid || !apiBaseUrl || transferBusy) return;
        const next = !isTransfer;
        setTransferBusy(true);
        try {
            await apiFetch(`${apiBaseUrl}/transactions/${transaction.uid}/transfer-flag`, {
                method: 'PATCH',
                body: JSON.stringify({ is_transfer: next }),
            });
            setIsTransfer(next);
            onTransferFlagChanged && onTransferFlagChanged();
        } catch (err) {
            console.error('Failed to toggle transfer flag', err);
        } finally {
            setTransferBusy(false);
        }
    };

    const handleAmountChange = (e) => {
        const newAmt = e.target.value;
        setFormData(prev => ({ ...prev, amount: newAmt }));
        
        if (isOriginalVerified && parseFloat(newAmt) !== parseFloat(transaction.amount)) {
            setShowWarning(true);
        } else {
            setShowWarning(false);
        }
    };

    if (!isOpen) return null;

    const handleSubmit = (e) => {
        e.preventDefault();
        
        // 2. Format data for Django
        const finalData = {
            ...formData,
            amount: parseFloat(formData.amount),
            // CRITICAL: Send date as a string "YYYY-MM-DD", not new Date() object
            date: formData.date, 
            // Map description to title if your backend specifically expects 'title'
            title: formData.description,
            confidence: showWarning ? 0 : (transaction.confidence || 0)
        };
        
        onSave(finalData);
        onClose();
    };

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in duration-200 p-4">
            <div className="bg-[#0f172a] border border-white/10 w-full max-w-sm rounded-[2rem] shadow-2xl flex flex-col max-h-[90vh]">
                
                <div className="p-6 border-b border-white/5 flex justify-between items-center">
                    <h3 className="text-xl font-bold text-white">Edit Transaction</h3>
                    <button onClick={onClose} className="p-2 bg-white/5 rounded-full hover:bg-white/10 text-slate-400 hover:text-white transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-5 overflow-y-auto custom-scrollbar">
                    
                    {showWarning && (
                        <div className="bg-rose-500/10 border border-rose-500/30 p-4 rounded-xl flex gap-3 animate-in fade-in slide-in-from-top-2">
                            <ShieldAlert className="w-6 h-6 text-rose-500 shrink-0" />
                            <div>
                                <h4 className="text-sm font-bold text-rose-400">Tampering Detected</h4>
                                <p className="text-[10px] text-rose-200/80 leading-relaxed mt-1">
                                    This record was verified. Changing the amount may lead to <strong>Misreporting</strong>.
                                </p>
                            </div>
                        </div>
                    )}

                    <div className="flex gap-4">
                        <div className="flex-1 space-y-2">
                             <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Amount</label>
                             <div className="relative">
                                <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                <input 
                                    type="text"
                                    inputMode="decimal"
                                    value={formData.amount}
                                    onChange={(e) => {
                                      const val = e.target.value;
                                      if (val === "" || /^\d+(\.\d{0,2})?$/.test(val)) {
                                        handleAmountChange(e);
                                      }
                                    }}
                                    className={`w-full bg-white/5 border rounded-xl py-3 pl-10 pr-4 text-white font-bold outline-none focus:border-blue-500 ${showWarning ? 'border-rose-500 text-rose-400' : 'border-white/10'}`}
                                    required
                                />
                             </div>
                        </div>
                        <div className="flex-1 space-y-2">
                             <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Type</label>
                             <select 
                                value={formData.type} 
                                onChange={e => setFormData({...formData, type: e.target.value})} 
                                className="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-white text-sm outline-none focus:border-blue-500 appearance-none capitalize"
                             >
                                <option value="expense" className="bg-[#0f172a]">Expense</option>
                                <option value="income" className="bg-[#0f172a]">Income</option>
                             </select>
                        </div>
                    </div>

                    <div className="space-y-2">
                         <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Date</label>
                         <input 
                            type="date" 
                            value={formData.date} 
                            onChange={e => setFormData({...formData, date: e.target.value})} 
                            className="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-white text-sm outline-none focus:border-blue-500" 
                            required 
                         />
                    </div>

                    <div className="space-y-2">
                         <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Description</label>
                         <input 
                            type="text" 
                            value={formData.description} 
                            onChange={e => setFormData({...formData, description: e.target.value})} 
                            className="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-white text-sm outline-none focus:border-blue-500" 
                            required 
                         />
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Category</label>
                        <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto custom-scrollbar pr-1">
                            {CATEGORIES.map(cat => (
                                <button 
                                    key={cat.id} 
                                    type="button" 
                                    onClick={() => setFormData({...formData, category: cat.id})} 
                                    className={`p-2 rounded-lg text-xs font-bold border transition-all flex items-center gap-2 ${formData.category === cat.id ? 'bg-blue-600 border-blue-500 text-white' : 'bg-white/5 border-transparent text-slate-400 hover:bg-white/10'}`}
                                >
                                    <cat.icon className="w-3 h-3" /> {cat.name}
                                </button>
                            ))}
                        </div>
                    </div>

                    {apiBaseUrl && transaction?.uid && (
                        <button
                            type="button"
                            onClick={toggleTransferFlag}
                            disabled={transferBusy}
                            className={`w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl border transition-colors ${isTransfer ? 'bg-cyan-500/15 border-cyan-500/30 text-cyan-200' : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10'} ${transferBusy ? 'opacity-60 cursor-wait' : 'cursor-pointer'}`}
                        >
                            <span className="flex items-center gap-2 text-sm font-semibold">
                                <ArrowLeftRight className="w-4 h-4" />
                                {isTransfer ? 'Transfer — excluded from totals' : 'Mark as inter-account transfer'}
                            </span>
                            <span className={`text-[10px] font-bold uppercase tracking-wider ${isTransfer ? 'text-cyan-300' : 'text-slate-500'}`}>
                                {isTransfer ? 'ON' : 'OFF'}
                            </span>
                        </button>
                    )}

                    <button
                        type="button"
                        onClick={() => setFormData(prev => ({ ...prev, is_recurring: !prev.is_recurring }))}
                        className={`w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl border transition-colors ${formData.is_recurring ? 'bg-blue-500/15 border-blue-500/30 text-blue-200' : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10'}`}
                    >
                        <span className="flex items-center gap-2 text-sm font-semibold">
                            <Zap className="w-4 h-4" />
                            {formData.is_recurring ? 'Recurring — repeats monthly' : 'Mark as recurring monthly'}
                        </span>
                        <span className={`text-[10px] font-bold uppercase tracking-wider ${formData.is_recurring ? 'text-blue-300' : 'text-slate-500'}`}>
                            {formData.is_recurring ? 'ON' : 'OFF'}
                        </span>
                    </button>

                    <button
                        type="submit"
                        className="w-full bg-blue-600 hover:bg-blue-500 text-white py-4 rounded-xl font-bold shadow-lg shadow-blue-900/20 mt-4"
                    >
                        {showWarning ? 'Confirm & Mark Unverified' : 'Save Changes'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default EditTransactionModal;