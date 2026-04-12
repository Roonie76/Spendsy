//No database needed
import React, { useState, useEffect } from 'react';
import { X, Check, RotateCcw, Calendar, IndianRupee } from 'lucide-react';
import { CATEGORIES } from '@shared/config/constants';

const FilterModal = ({ isOpen, onClose, currentFilters, onApply }) => {
    // Local state for the modal form
    const [localFilters, setLocalFilters] = useState(currentFilters);

    // Reset local state when modal opens with new props
    useEffect(() => {
        setLocalFilters(currentFilters);
    }, [currentFilters, isOpen]);

    if (!isOpen) return null;

    const handleCategoryToggle = (catId) => {
        setLocalFilters(prev => {
            const exists = prev.categories.includes(catId);
            return {
                ...prev,
                categories: exists 
                    ? prev.categories.filter(c => c !== catId) 
                    : [...prev.categories, catId]
            };
        });
    };

    const handleTypeToggle = (type) => {
        setLocalFilters(prev => {
            const exists = prev.types.includes(type);
            return {
                ...prev,
                types: exists 
                    ? prev.types.filter(t => t !== type) 
                    : [...prev.types, type]
            };
        });
    };

    const handleAccountTypeToggle = (type) => {
        setLocalFilters(prev => {
            const exists = prev.accountTypes.includes(type);
            return {
                ...prev,
                accountTypes: exists 
                    ? prev.accountTypes.filter(t => t !== type) 
                    : [...prev.accountTypes, type]
            };
        });
    };


    return (
        <div className="fixed inset-0 z-[60] flex items-end md:items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-[#0f172a] border border-white/10 w-full md:max-w-md h-[85vh] md:h-auto md:max-h-[85vh] rounded-t-[2rem] md:rounded-[2rem] shadow-2xl flex flex-col">
                
                {/* Header */}
                <div className="p-6 border-b border-white/5 flex justify-between items-center shrink-0">
                    <h3 className="text-xl font-bold text-white">Filter & Sort</h3>
                    <div className="flex gap-2">
                        <button 
                            onClick={() => setLocalFilters({
                                startDate: '', endDate: '', minAmount: '', maxAmount: '', categories: [], types: [], accountTypes: [], sortBy: 'date-desc'
                            })}

                            className="p-2 bg-white/5 rounded-full hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
                            title="Reset"
                        >
                            <RotateCcw className="w-5 h-5" />
                        </button>
                        <button onClick={onClose} className="p-2 bg-white/5 rounded-full hover:bg-white/10 text-slate-400 hover:text-white transition-colors">
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Scrollable Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
                    
                    {/* Sort By */}
                    <div className="space-y-3">
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Sort Order</label>
                        <div className="grid grid-cols-2 gap-2">
                            {[
                                { label: 'Newest First', value: 'date-desc' },
                                { label: 'Oldest First', value: 'date-asc' },
                                { label: 'Amount: High to Low', value: 'amount-desc' },
                                { label: 'Amount: Low to High', value: 'amount-asc' },
                            ].map(opt => (
                                <button
                                    key={opt.value}
                                    onClick={() => setLocalFilters({...localFilters, sortBy: opt.value})}
                                    className={`py-3 px-4 rounded-xl text-xs font-bold border transition-all ${
                                        localFilters.sortBy === opt.value 
                                        ? 'bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-900/20' 
                                        : 'bg-white/5 border-transparent text-slate-400 hover:bg-white/10'
                                    }`}
                                >
                                    {opt.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Transaction Type */}
                    <div className="space-y-3">
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Type</label>
                        <div className="flex gap-2">
                            {['income', 'expense'].map(type => {
                                const isActive = localFilters.types.includes(type);
                                return (
                                    <button
                                        key={type}
                                        onClick={() => handleTypeToggle(type)}
                                        className={`flex-1 py-3 rounded-xl text-sm font-bold capitalize border transition-all flex items-center justify-center gap-2 ${
                                            isActive
                                            ? (type === 'income' ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300' : 'bg-rose-500/20 border-rose-500/50 text-rose-300')
                                            : 'bg-white/5 border-transparent text-slate-400'
                                        }`}
                                    >
                                        {isActive && <Check className="w-3 h-3" />} {type}
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Card Type */}
                    <div className="space-y-3">
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Card Type</label>
                        <div className="flex gap-2">
                            {['debit', 'credit'].map(type => {
                                const isActive = localFilters.accountTypes.includes(type);
                                return (
                                    <button
                                        key={type}
                                        onClick={() => handleAccountTypeToggle(type)}
                                        className={`flex-1 py-3 rounded-xl text-sm font-bold capitalize border transition-all flex items-center justify-center gap-2 ${
                                            isActive
                                            ? (type === 'credit' ? 'bg-purple-500/20 border-purple-500/50 text-purple-300' : 'bg-blue-500/20 border-blue-500/50 text-blue-300')
                                            : 'bg-white/5 border-transparent text-slate-400'
                                        }`}
                                    >
                                        {isActive && <Check className="w-3 h-3" />} {type} Card
                                    </button>
                                );
                            })}
                        </div>
                    </div>


                    {/* Date Range */}
                    <div className="space-y-3">
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Date Range</label>
                        <div className="flex gap-3">
                            <div className="flex-1 relative">
                                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                <input 
                                    type="date" 
                                    value={localFilters.startDate}
                                    onChange={(e) => setLocalFilters({...localFilters, startDate: e.target.value})}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-10 pr-3 text-white text-xs outline-none focus:border-blue-500"
                                />
                            </div>
                            <span className="text-slate-500 self-center">-</span>
                            <div className="flex-1 relative">
                                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                                <input 
                                    type="date" 
                                    value={localFilters.endDate}
                                    onChange={(e) => setLocalFilters({...localFilters, endDate: e.target.value})}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-10 pr-3 text-white text-xs outline-none focus:border-blue-500"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Amount Range */}
                    <div className="space-y-3">
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Amount Range (₹)</label>
                        <div className="flex gap-3">
                            <div className="flex-1 relative">
                                <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-500" />
                                <input 
                                    type="number" 
                                    placeholder="Min"
                                    value={localFilters.minAmount}
                                    onChange={(e) => setLocalFilters({...localFilters, minAmount: e.target.value})}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-8 pr-3 text-white text-sm outline-none focus:border-blue-500"
                                />
                            </div>
                            <div className="flex-1 relative">
                                <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3 text-slate-500" />
                                <input 
                                    type="number" 
                                    placeholder="Max"
                                    value={localFilters.maxAmount}
                                    onChange={(e) => setLocalFilters({...localFilters, maxAmount: e.target.value})}
                                    className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-8 pr-3 text-white text-sm outline-none focus:border-blue-500"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Categories */}
                    <div className="space-y-3">
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Categories</label>
                        <div className="flex flex-wrap gap-2">
                            {CATEGORIES.map(cat => {
                                const isActive = localFilters.categories.includes(cat.id);
                                return (
                                    <button
                                        key={cat.id}
                                        onClick={() => handleCategoryToggle(cat.id)}
                                        className={`px-3 py-2 rounded-lg text-xs font-bold border transition-all flex items-center gap-1 ${
                                            isActive 
                                            ? 'bg-blue-600 border-blue-500 text-white' 
                                            : 'bg-white/5 border-transparent text-slate-400 hover:bg-white/10'
                                        }`}
                                    >
                                        {isActive && <Check className="w-3 h-3" />}
                                        <cat.icon className="w-3 h-3" />
                                        {cat.name}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </div>

                {/* Footer Actions */}
                <div className="p-6 border-t border-white/5 shrink-0 bg-[#0f172a]">
                    <button 
                        onClick={() => { onApply(localFilters); onClose(); }}
                        className="w-full bg-blue-600 hover:bg-blue-500 text-white py-4 rounded-xl font-bold shadow-lg shadow-blue-900/20 transition-all active:scale-95"
                    >
                        Apply Filters
                    </button>
                </div>
            </div>
        </div>
    );
};

export default FilterModal;