//Database needed
// Section 2 History Page
import React, { useEffect, useMemo, useState, useRef, useCallback } from 'react';
import { AlertTriangle, CheckCircle2, LoaderCircle, Search, X, Trash2, Filter, SlidersHorizontal, Download, Undo2 } from 'lucide-react';
import TransactionItem from '../components/domain/TransactionItem';
import FilterModal from '../components/ui/FilterModal';
import EditTransactionModal from '../components/ui/EditTransactionModal';
import CustomDeletePanel from '../components/ui/CustomDeletePanel';
import { TABS } from '@shared/config/constants';
import { normalizeDate } from '@shared/utils/helpers';
import { downloadCSV } from "@shared/utils/exportUtils";

const SkeletonRow = () => (
    <div className="flex items-center p-4 bg-white/5 border border-white/10 rounded-3xl mb-3 animate-pulse">
        <div className="w-12 h-12 rounded-2xl bg-white/10 mr-4 shrink-0" />
        <div className="flex-1 space-y-2">
            <div className="h-4 bg-white/10 rounded w-2/3" />
            <div className="h-3 bg-white/5 rounded w-1/3" />
        </div>
        <div className="h-5 bg-white/10 rounded w-16 shrink-0" />
    </div>
);

const HistoryPage = ({ transactions, isLoading, onDelete, onBulkDelete, setActiveTab, onUpdate, apiBaseUrl, onRefresh }) => {
    // UI State
    const [page, setPage] = useState(1);
    const PER_PAGE = 20;
    const [searchTerm, setSearchTerm] = useState('');
    const [debouncedSearchTerm, setDebouncedSearchTerm] = useState('');
    const [showCustomDelete, setShowCustomDelete] = useState(false);
    const [filterError, setFilterError] = useState('');
    const [exportStatus, setExportStatus] = useState('idle');
    const [pendingBulkDelete, setPendingBulkDelete] = useState(null);
    
    // Modal States
    const [isFilterOpen, setIsFilterOpen] = useState(false);
    const [editingTransaction, setEditingTransaction] = useState(null);

    // Undo state for bulk delete
    const [undoBar, setUndoBar] = useState(null); // { items: [], timeoutId }
    const undoRef = useRef(null);

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

    useEffect(() => {
        const timer = window.setTimeout(() => {
            setDebouncedSearchTerm(searchTerm.trim());
            setPage(1);
        }, 250);
        return () => window.clearTimeout(timer);
    }, [searchTerm]);

    useEffect(() => {
        setPage(1);
    }, [filters]);

    const validateFilters = (nextFilters) => {
        if (nextFilters.startDate && nextFilters.endDate && nextFilters.startDate > nextFilters.endDate) {
            return 'Start date cannot be after end date.';
        }

        const min = nextFilters.minAmount === '' ? null : Number(nextFilters.minAmount);
        const max = nextFilters.maxAmount === '' ? null : Number(nextFilters.maxAmount);

        if ((min !== null && (!Number.isFinite(min) || min < 0)) || (max !== null && (!Number.isFinite(max) || max < 0))) {
            return 'Amounts must be zero or greater.';
        }

        if (min !== null && max !== null && min > max) {
            return 'Minimum amount cannot exceed maximum amount.';
        }

        return '';
    };

    const applyFilters = (nextFilters) => {
        const message = validateFilters(nextFilters);
        if (message) {
            setFilterError(message);
            return false;
        }

        setFilterError('');
        setFilters(nextFilters);
        return true;
    };

    const clearFilters = () => {
        setFilterError('');
        setFilters({startDate: '', endDate: '', minAmount: '', maxAmount: '', categories: [], types: [], accountTypes: [], sortBy: 'date-desc'});
    };

    const requestBulkDelete = () => {
        if (filtered.length === 0) return;
        setPendingBulkDelete(filtered);
    };

    const UNDO_DELAY_MS = 5000;

    const confirmBulkDelete = useCallback(() => {
        if (!pendingBulkDelete?.length) return;
        const items = pendingBulkDelete;
        setPendingBulkDelete(null);

        // Clear any previous undo timer
        if (undoRef.current) window.clearTimeout(undoRef.current);

        // Show undo bar — delay actual deletion
        const tid = window.setTimeout(() => {
            onBulkDelete(items);
            setUndoBar(null);
        }, UNDO_DELAY_MS);
        undoRef.current = tid;
        setUndoBar({ items, timeoutId: tid });
    }, [pendingBulkDelete, onBulkDelete]);

    const handleUndo = useCallback(() => {
        if (undoBar?.timeoutId) window.clearTimeout(undoBar.timeoutId);
        undoRef.current = null;
        setUndoBar(null);
    }, [undoBar]);

    // Cleanup on unmount
    useEffect(() => {
        return () => { if (undoRef.current) window.clearTimeout(undoRef.current); };
    }, []);

    const handleExport = () => {
        if (exportStatus === 'loading') return;

        setExportStatus('loading');
        try {
            downloadCSV(filtered);
            setExportStatus('success');
        } catch {
            setExportStatus('error');
        } finally {
            window.setTimeout(() => setExportStatus('idle'), 1800);
        }
    };

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

    // Set of IDs pending undo — hide them from the list
    const undoIds = useMemo(() => {
        if (!undoBar?.items) return new Set();
        return new Set(undoBar.items.map(t => t.id));
    }, [undoBar]);

    // 2. Filter & Sort Logic
    const filtered = useMemo(() => {
        let data = transactions.filter(t => !undoIds.has(t.id));

        // Text Search
        if (debouncedSearchTerm) { 
            const term = debouncedSearchTerm.toLowerCase(); 
            data = data.filter(t => String(t.title || '').toLowerCase().includes(term) || String(t.amount ?? '').includes(term)); 
        }

        // Date Range
        if (filters.startDate) {
            const start = new Date(filters.startDate);
            start.setHours(0,0,0,0);
            data = data.filter(t => {
                const d = normalizeDate(t.date);
                return d && d >= start;
            });
        }
        if (filters.endDate) {
            const end = new Date(filters.endDate);
            end.setHours(23,59,59,999);
            data = data.filter(t => {
                const d = normalizeDate(t.date);
                return d && d <= end;
            });
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

        // Account Types / MT Logic
        if (filters.accountTypes.length > 0) {
            data = data.filter(t => {
                const results = [];
                if (filters.accountTypes.includes('debit')) results.push(t.account_type?.toLowerCase() === 'debit');
                if (filters.accountTypes.includes('credit')) results.push(t.account_type?.toLowerCase() === 'credit');
                if (filters.accountTypes.includes('manual')) results.push(t.source === 'manual' || (t.confidence == null || t.confidence <= 0));
                return results.some(r => r === true);
            });
        }

        
        // Sorting
        data.sort((a, b) => {
            // Sort undated rows to the bottom so they don't poison the ordering
            const dA = normalizeDate(a.date);
            const dB = normalizeDate(b.date);
            const dateA = dA ? dA.getTime() : -Infinity;
            const dateB = dB ? dB.getTime() : -Infinity;
            const amtA = Number.parseFloat(a.amount) || 0;
            const amtB = Number.parseFloat(b.amount) || 0;

            switch(filters.sortBy) {
                case 'date-asc': return dateA - dateB;
                case 'amount-desc': return amtB - amtA;
                case 'amount-asc': return amtA - amtB;
                case 'date-desc': 
                default: return dateB - dateA;
            }
        });

        return data;
    }, [transactions, debouncedSearchTerm, filters, undoIds]);

    // 3. Pagination Logic
    const visible = filtered.slice(0, page * PER_PAGE);

    return (
        <div className="space-y-4 sm:space-y-6 pb-4 animate-in fade-in">
            {/* --- Header --- */}
            <div className="flex justify-between items-center mb-2 gap-2">
                <h2 className="text-xl sm:text-2xl font-bold text-white truncate">All Transactions</h2>
                <div className="flex gap-2 shrink-0">
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
                        onClick={handleExport}
                        disabled={exportStatus === 'loading' || filtered.length === 0}
                        className="p-2 bg-white/10 rounded-full hover:bg-white/20 text-emerald-400 transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                        title="Download CSV"
                        aria-label="Download CSV"
                    >
                        {exportStatus === 'loading' ? <LoaderCircle className="w-5 h-5 animate-spin" /> : <Download className="w-5 h-5" />}
                    </button>
                    
                    <button onClick={() => setActiveTab(TABS.HOME)} className="p-2 bg-white/10 rounded-full hover:bg-white/20 transition-colors" aria-label="Close history">
                        <X className="w-5 h-5 text-white" />
                    </button>
                </div>
            </div>

            {exportStatus === 'success' && (
                <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200" role="status">
                    <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                    CSV export started.
                </div>
            )}
            {exportStatus === 'error' && (
                <div className="flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200" role="alert">
                    <AlertTriangle className="h-4 w-4" aria-hidden="true" />
                    Could not export these transactions.
                </div>
            )}

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
                        {searchTerm !== debouncedSearchTerm ? (
                            <LoaderCircle className="absolute left-3 top-1/2 -translate-y-1/2 text-blue-400 w-4 h-4 animate-spin" />
                        ) : (
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 w-4 h-4" />
                        )}
                        <input 
                            type="text" 
                            placeholder="Search by name or amount..." 
                            value={searchTerm} 
                            onChange={(e) => setSearchTerm(e.target.value)} 
                            aria-label="Search transactions"
                            className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-sm text-white outline-none focus:bg-white/10 focus:border-blue-500/50 transition-all" 
                        />
                    </div>
                    <button 
                        onClick={() => setIsFilterOpen(true)} 
                        aria-label="Open filters"
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

            {filterError && (
                <div className="flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200" role="alert">
                    <AlertTriangle className="h-4 w-4" aria-hidden="true" />
                    {filterError}
                </div>
            )}

            {/* --- Results Header --- */}
            <div className="flex justify-between items-center px-1">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">{filtered.length} Results</span>
                {filtered.length > 0 && (
                    <button onClick={requestBulkDelete} className="text-xs text-rose-400 hover:text-rose-300 flex items-center gap-1 transition-colors">
                        <Trash2 className="w-3 h-3"/> Delete All Found
                    </button>
                )}
            </div>

            {pendingBulkDelete && (
                <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="bulk-delete-title">
                    <div className="w-full max-w-sm rounded-2xl border border-white/10 bg-slate-950 p-5 shadow-2xl">
                        <div className="mb-4 flex items-start gap-3">
                            <div className="rounded-full bg-rose-500/15 p-2 text-rose-300">
                                <AlertTriangle className="h-5 w-5" aria-hidden="true" />
                            </div>
                            <div>
                                <h3 id="bulk-delete-title" className="text-base font-bold text-white">Delete filtered transactions?</h3>
                                <p className="mt-1 text-sm text-slate-400">
                                    This will remove {pendingBulkDelete.length} transaction{pendingBulkDelete.length === 1 ? '' : 's'} from the current result set.
                                </p>
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <button
                                type="button"
                                onClick={() => setPendingBulkDelete(null)}
                                className="flex-1 rounded-xl bg-white/10 px-4 py-3 text-sm font-bold text-slate-200 hover:bg-white/15"
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                onClick={confirmBulkDelete}
                                className="flex-1 rounded-xl bg-rose-600 px-4 py-3 text-sm font-bold text-white hover:bg-rose-500"
                            >
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* --- Undo Bar --- */}
            {undoBar && (
                <div className="flex items-center justify-between gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 animate-in slide-in-from-bottom-2" role="status">
                    <span className="text-sm text-amber-200">
                        {undoBar.items.length} transaction{undoBar.items.length === 1 ? '' : 's'} will be deleted
                    </span>
                    <button
                        onClick={handleUndo}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 text-sm font-bold transition-colors"
                    >
                        <Undo2 className="w-3.5 h-3.5" /> Undo
                    </button>
                </div>
            )}

            {/* --- Transaction List --- */}
            <div className="space-y-3 min-h-[50vh]">
                {isLoading && transactions.length === 0 ? (
                    <>
                        <SkeletonRow /><SkeletonRow /><SkeletonRow /><SkeletonRow /><SkeletonRow />
                    </>
                ) : filtered.length === 0 ? (
                    <div className="text-center py-20 opacity-50">
                        <Filter className="w-12 h-12 mx-auto mb-3 text-slate-600" />
                        <p className="text-slate-400 text-sm">No transactions match your filters.</p>
                        <button onClick={clearFilters} className="mt-4 text-blue-400 text-sm font-bold hover:underline">Clear Filters</button>
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
                onApply={applyFilters}
            />

            <EditTransactionModal
                isOpen={!!editingTransaction}
                onClose={() => setEditingTransaction(null)}
                transaction={editingTransaction}
                onSave={onUpdate}
                apiBaseUrl={apiBaseUrl}
                onTransferFlagChanged={onRefresh}
            />
        </div>
    );
};

export default HistoryPage;
