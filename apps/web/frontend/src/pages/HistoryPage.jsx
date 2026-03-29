//Database needed
// Section 2 History Page
import React, { useState, useMemo } from 'react';
import { Search, X, Trash2, Filter, SlidersHorizontal, Download } from 'lucide-react';
import TransactionItem from '../components/domain/TransactionItem';
import FilterModal from '../components/ui/FilterModal';
import EditTransactionModal from '../components/ui/EditTransactionModal';
import CustomDeletePanel from '../components/ui/CustomDeletePanel';
import { TABS } from '../../../../../packages/shared/config/constants';
import { normalizeDate } from '../../../../../packages/shared/utils/helpers';
import { downloadCSV } from "../../../../../packages/shared/utils/exportUtils";

const HistoryPage = ({ transactions, onDelete, onBulkDelete, setActiveTab, onUpdate }) => {
    // UI State
    const [page, setPage] = useState(1);
    const PER_PAGE = 20;
    const [searchTerm, setSearchTerm] = useState('');
    const [showCustomDelete, setShowCustomDelete] = useState(false);
    
    // Modal States
    const [isFilterOpen, setIsFilterOpen] = useState(false);
    const [editingTransaction, setEditingTransaction] = useState(null);

    // Complex Filter State
    const [filters, setFilters] = useState({
        startDate: '',
        endDate: '',
        minAmount: '',
        maxAmount: '',
        categories: [], // Array of category IDs
        types: [],      // ['income', 'expense']
        accountTypes: [], // ['debit', 'credit']
        sortBy: 'date-desc' // 'date-desc', 'date-asc', 'amount-desc', 'amount-asc'

    });

    // 1. Calculate Active Filters Badge
    const activeFilterCount = useMemo(() => {
        let count = 0;
        if (filters.startDate) count++;
        if (filters.endDate) count++;
        if (filters.minAmount) count++;
        if (filters.maxAmount) count++;
        if (filters.categories.length > 0) count++;
        if (filters.types.length > 0) count++;
        if (filters.accountTypes.length > 0) count++;

        return count;
    }, [filters]);

    // 2. Filter & Sort Logic
    const filtered = useMemo(() => {
        let data = [...transactions];

        // Text Search
        if (searchTerm) { 
            const term = searchTerm.toLowerCase(); 
            data = data.filter(t => t.title.toLowerCase().includes(term) || t.amount.toString().includes(term)); 
        }

        // Date Range
        if (filters.startDate) {
            const start = new Date(filters.startDate);
            start.setHours(0,0,0,0);
            data = data.filter(t => normalizeDate(t.date) >= start);
        }
        if (filters.endDate) {
            const end = new Date(filters.endDate);
            end.setHours(23,59,59,999);
            data = data.filter(t => normalizeDate(t.date) <= end);
        }

        // Amount Range
        if (filters.minAmount) {
            data = data.filter(t => parseFloat(t.amount) >= parseFloat(filters.minAmount));
        }
        if (filters.maxAmount) {
            data = data.filter(t => parseFloat(t.amount) <= parseFloat(filters.maxAmount));
        }

        // Categories
        if (filters.categories.length > 0) {
            data = data.filter(t => filters.categories.includes(t.category));
        }

        // Types
        if (filters.types.length > 0) {
            data = data.filter(t => filters.types.includes(t.type));
        }

        // Account Types
        if (filters.accountTypes.length > 0) {
            data = data.filter(t => filters.accountTypes.includes(t.account_type));
        }

        
        // Sorting
        data.sort((a, b) => {
            const dateA = normalizeDate(a.date).getTime();
            const dateB = normalizeDate(b.date).getTime();
            const amtA = parseFloat(a.amount);
            const amtB = parseFloat(b.amount);

            switch(filters.sortBy) {
                case 'date-asc': return dateA - dateB;
                case 'amount-desc': return amtB - amtA;
                case 'amount-asc': return amtA - amtB;
                case 'date-desc': 
                default: return dateB - dateA;
            }
        });

        return data;
    }, [transactions, searchTerm, filters]);

    // 3. Pagination Logic
    const visible = filtered.slice(0, page * PER_PAGE);

    return (
        <div className="space-y-6 pb-4 animate-in fade-in">
            {/* --- Header --- */}
            <div className="flex justify-between items-center mb-2">
                <h2 className="text-2xl font-bold text-white">All Transactions</h2>
                <div className="flex gap-2">
                    {/* Custom Delete Button */}
                    <button
                        onClick={() => setShowCustomDelete((p) => !p)}
                        className={`p-2 rounded-full transition-colors ${
                            showCustomDelete
                              ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                              : 'bg-white/10 hover:bg-white/20 text-slate-400'
                        }`}
                        title="Custom Delete"
                    >
                        <Trash2 className="w-5 h-5" />
                    </button>
                    {/* Export Button */}
                    <button 
                        onClick={() => downloadCSV(filtered)} 
                        className="p-2 bg-white/10 rounded-full hover:bg-white/20 text-emerald-400 transition-colors"
                        title="Download CSV"
                    >
                        <Download className="w-5 h-5" />
                    </button>
                    
                    <button onClick={() => setActiveTab(TABS.HOME)} className="p-2 bg-white/10 rounded-full hover:bg-white/20 transition-colors">
                        <X className="w-5 h-5 text-white" />
                    </button>
                </div>
            </div>

            {/* Custom Delete Panel */}
            {showCustomDelete && (
                <CustomDeletePanel
                    transactions={transactions}
                    onBulkDelete={onBulkDelete}
                    onClose={() => setShowCustomDelete(false)}
                />
            )}
            
            {/* --- Search and Filter Bar --- */}
            <div className="space-y-3 sticky top-4 z-30 bg-slate-950/90 backdrop-blur-xl py-3 -mx-2 px-2 rounded-2xl border-b border-white/5 shadow-lg">
                <div className="flex gap-3">
                    <div className="relative flex-1">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4" />
                        <input 
                            type="text" 
                            placeholder="Search by name or amount..." 
                            value={searchTerm} 
                            onChange={(e) => setSearchTerm(e.target.value)} 
                            className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-sm text-white outline-none focus:bg-white/10 focus:border-blue-500/50 transition-all" 
                        />
                    </div>
                    <button 
                        onClick={() => setIsFilterOpen(true)} 
                        className={`p-3 border rounded-xl relative transition-all ${
                            activeFilterCount > 0 
                            ? 'bg-blue-600 border-blue-500 text-white' 
                            : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10'
                        }`}
                    >
                        {activeFilterCount > 0 ? <SlidersHorizontal className="w-5 h-5" /> : <Filter className="w-5 h-5" />}
                        {activeFilterCount > 0 && (
                            <span className="absolute -top-1.5 -right-1.5 bg-rose-500 text-white text-[10px] font-bold w-5 h-5 flex items-center justify-center rounded-full border-2 border-slate-900">
                                {activeFilterCount}
                            </span>
                        )}
                    </button>
                </div>
                
                {/* Active Filter Summary (Pills) */}
                {activeFilterCount > 0 && (
                    <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1">
                        {filters.startDate && <div className="px-3 py-1 bg-blue-500/20 text-blue-300 text-[10px] rounded-full border border-blue-500/30 whitespace-nowrap">After: {filters.startDate}</div>}
                        {filters.endDate && <div className="px-3 py-1 bg-blue-500/20 text-blue-300 text-[10px] rounded-full border border-blue-500/30 whitespace-nowrap">Before: {filters.endDate}</div>}
                        {filters.minAmount && <div className="px-3 py-1 bg-emerald-500/20 text-emerald-300 text-[10px] rounded-full border border-emerald-500/30 whitespace-nowrap">Min: ₹{filters.minAmount}</div>}
                        {filters.maxAmount && <div className="px-3 py-1 bg-emerald-500/20 text-emerald-300 text-[10px] rounded-full border border-emerald-500/30 whitespace-nowrap">Max: ₹{filters.maxAmount}</div>}
                        {filters.types.map(t => <div key={t} className="px-3 py-1 bg-purple-500/20 text-purple-300 text-[10px] rounded-full border border-purple-500/30 capitalize whitespace-nowrap">{t}</div>)}
                        {filters.accountTypes.map(t => <div key={t} className={`px-3 py-1 text-[10px] rounded-full border capitalize whitespace-nowrap ${t === 'credit' ? 'bg-purple-500/20 text-purple-300 border-purple-500/30' : 'bg-blue-500/20 text-blue-300 border-blue-500/30'}`}>{t}</div>)}
                    </div>

                )}
            </div>

            {/* --- Results Header --- */}
            <div className="flex justify-between items-center px-1">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">{filtered.length} Results</span>
                {filtered.length > 0 && (
                    <button onClick={() => onBulkDelete(filtered)} className="text-xs text-rose-400 hover:text-rose-300 flex items-center gap-1 transition-colors">
                        <Trash2 className="w-3 h-3"/> Delete All Found
                    </button>
                )}
            </div>

            {/* --- Transaction List --- */}
            <div className="space-y-3 min-h-[50vh]">
                {filtered.length === 0 ? (
                    <div className="text-center py-20 opacity-50">
                        <Filter className="w-12 h-12 mx-auto mb-3 text-slate-600" />
                        <p className="text-slate-400 text-sm">No transactions match your filters.</p>
                        <button onClick={() => setFilters({startDate: '', endDate: '', minAmount: '', maxAmount: '', categories: [], types: [], accountTypes: [], sortBy: 'date-desc'})} className="mt-4 text-blue-400 text-sm font-bold hover:underline">Clear Filters</button>
                    </div>

                ) : (
                    visible.map(t => (
                        <TransactionItem 
                            key={t.id} 
                            item={t} 
                            onDelete={onDelete} 
                            onEdit={setEditingTransaction}
                        />
                    ))
                )}
            </div>
            
            {visible.length < filtered.length && (
                <button onClick={() => setPage(p => p + 1)} className="w-full py-4 text-center text-slate-400 text-sm font-bold bg-white/5 rounded-2xl mt-4 hover:bg-white/10 transition-colors">Load More</button>
            )}

            {/* --- Modals --- */}
            <FilterModal 
                isOpen={isFilterOpen} 
                onClose={() => setIsFilterOpen(false)} 
                currentFilters={filters}
                onApply={setFilters}
            />

            <EditTransactionModal
                isOpen={!!editingTransaction}
                onClose={() => setEditingTransaction(null)}
                transaction={editingTransaction}
                onSave={onUpdate}
            />
        </div>
    );
};

export default HistoryPage;