import { useState, useMemo } from "react";
import { Trash2, Filter, ChevronDown, ChevronUp, AlertTriangle, CheckSquare, Square } from "lucide-react";
import { CATEGORIES as SHARED_CATEGORIES } from "@shared/config/constants";
import { normalizeDate } from "@shared/utils/helpers";

const CATEGORY_OPTIONS = ["all", ...SHARED_CATEGORIES.map(c => c.id)];
const TYPES = ["all", "income", "expense"];

export default function CustomDeletePanel({ transactions = [], onBulkDelete, onClose, showToast }) {
  const [filters, setFilters] = useState({
    type: "all",
    category: "all",
    dateFrom: "",
    dateTo: "",
    amountMin: "",
    amountMax: "",
  });
  const [expanded, setExpanded] = useState(true);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [confirmVisible, setConfirmVisible] = useState(false);

  const filtered = useMemo(() => {
    return transactions.filter((t) => {
      if (filters.type !== "all" && t.type !== filters.type) return false;
      if (filters.category !== "all" && t.category !== filters.category) return false;

      // Date comparison via normalizeDate — safe for Firestore timestamps & strings
      if (filters.dateFrom) {
        const d = normalizeDate(t.date);
        const from = new Date(filters.dateFrom);
        from.setHours(0, 0, 0, 0);
        if (!d || d < from) return false;
      }
      if (filters.dateTo) {
        const d = normalizeDate(t.date);
        const to = new Date(filters.dateTo);
        to.setHours(23, 59, 59, 999);
        if (!d || d > to) return false;
      }

      // Amount comparison with NaN guard
      const amt = parseFloat(t.amount);
      if (filters.amountMin) {
        const min = parseFloat(filters.amountMin);
        if (!Number.isFinite(amt) || !Number.isFinite(min) || amt < min) return false;
      }
      if (filters.amountMax) {
        const max = parseFloat(filters.amountMax);
        if (!Number.isFinite(amt) || !Number.isFinite(max) || amt > max) return false;
      }

      return true;
    });
  }, [transactions, filters]);

  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    setSelectedIds(new Set(filtered.map((t) => t.id)));
  };

  const clearSelection = () => setSelectedIds(new Set());

  const handleDelete = () => {
    const items = filtered.filter((t) => selectedIds.has(t.id));
    onBulkDelete(items);
    setConfirmVisible(false);
    onClose?.();
  };

  const totalAmount = filtered
    .filter((t) => selectedIds.has(t.id))
    .reduce((sum, t) => {
      const a = parseFloat(t.amount);
      return sum + (Number.isFinite(a) ? a : 0);
    }, 0);

  return (
    <div className="rounded-3xl border border-red-500/20 bg-red-500/5 p-5">
      {/* Header */}
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded((p) => !p)}
      >
        <div className="flex items-center gap-2 text-red-400 font-bold">
          <Trash2 className="w-4 h-4" />
          <span className="text-sm uppercase tracking-widest">Custom Delete</span>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4 text-red-400" /> : <ChevronDown className="w-4 h-4 text-red-400" />}
      </div>

      {expanded && (
        <div className="mt-4 space-y-4">
          {/* Filters */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {/* Type */}
            <div>
              <label className="text-[10px] uppercase tracking-widest opacity-50 block mb-1">Type</label>
              <select
                className="w-full rounded-xl bg-slate-900/50 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500/50 transition-all [&>option]:bg-slate-900 [&>option]:text-white"
                value={filters.type}
                onChange={(e) => setFilters((f) => ({ ...f, type: e.target.value }))}
              >
                {TYPES.map((t) => (
                  <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                ))}
              </select>
            </div>

            {/* Category */}
            <div>
              <label className="text-[10px] uppercase tracking-widest opacity-50 block mb-1">Category</label>
              <select
                className="w-full rounded-xl bg-slate-900/50 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500/50 transition-all [&>option]:bg-slate-900 [&>option]:text-white"
                value={filters.category}
                onChange={(e) => setFilters((f) => ({ ...f, category: e.target.value }))}
              >
                {CATEGORY_OPTIONS.map((c) => (
                  <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                ))}
              </select>
            </div>

            {/* Date From */}
            <div>
              <label className="text-[10px] uppercase tracking-widest opacity-50 block mb-1">Date From</label>
              <input
                type="date"
                className="w-full rounded-xl bg-slate-900/50 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500/50 transition-all [color-scheme:dark]"
                value={filters.dateFrom}
                onChange={(e) => setFilters((f) => ({ ...f, dateFrom: e.target.value }))}
              />
            </div>

            {/* Date To */}
            <div>
              <label className="text-[10px] uppercase tracking-widest opacity-50 block mb-1">Date To</label>
              <input
                type="date"
                className="w-full rounded-xl bg-slate-900/50 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500/50 transition-all [color-scheme:dark]"
                value={filters.dateTo}
                onChange={(e) => setFilters((f) => ({ ...f, dateTo: e.target.value }))}
              />
            </div>

            {/* Min Amount */}
            <div>
              <label className="text-[10px] uppercase tracking-widest opacity-50 block mb-1">Min Amount (₹)</label>
              <input
                type="number"
                placeholder="0"
                className="w-full rounded-xl bg-slate-900/50 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500/50 transition-all"
                value={filters.amountMin}
                onChange={(e) => setFilters((f) => ({ ...f, amountMin: e.target.value }))}
              />
            </div>

            {/* Max Amount */}
            <div>
              <label className="text-[10px] uppercase tracking-widest opacity-50 block mb-1">Max Amount (₹)</label>
              <input
                type="number"
                placeholder="Any"
                className="w-full rounded-xl bg-slate-900/50 border border-white/10 px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500/50 transition-all"
                value={filters.amountMax}
                onChange={(e) => setFilters((f) => ({ ...f, amountMax: e.target.value }))}
              />
            </div>
          </div>

          {/* Results List */}
          <div className="border border-white/10 rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 border-b border-white/10 text-xs opacity-50">
              <span>{filtered.length} matched</span>
              <div className="flex gap-3">
                <button onClick={selectAll} className="hover:opacity-100 transition-opacity">Select All</button>
                <button onClick={clearSelection} className="hover:opacity-100 transition-opacity">Clear</button>
              </div>
            </div>
            <div className="max-h-64 overflow-y-auto divide-y divide-white/5">
              {filtered.length === 0 ? (
                <p className="text-center py-6 text-xs opacity-40">No transactions match filters</p>
              ) : (
                filtered.map((t) => (
                  <div
                    key={t.id}
                    className="flex items-center gap-3 px-4 py-2 hover:bg-white/5 cursor-pointer transition-colors"
                    onClick={() => toggleSelect(t.id)}
                  >
                    {selectedIds.has(t.id) ? (
                      <CheckSquare className="w-4 h-4 text-red-400 shrink-0" />
                    ) : (
                      <Square className="w-4 h-4 opacity-30 shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{t.title || t.description}</p>
                      <p className="text-xs opacity-40">{t.date} · {t.category}</p>
                    </div>
                    <span className={`text-sm font-semibold ${t.type === "income" ? "text-emerald-400" : "text-rose-400"}`}>
                      ₹{(Number.isFinite(parseFloat(t.amount)) ? parseFloat(t.amount) : 0).toLocaleString("en-IN")}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Action Bar */}
          {selectedIds.size > 0 && (
            <div className="flex items-center justify-between">
              <div className="text-xs opacity-60">
                <span className="font-bold text-red-400">{selectedIds.size}</span> selected ·{" "}
                ₹{totalAmount.toLocaleString("en-IN", { minimumFractionDigits: 2 })} total
              </div>
              {!confirmVisible ? (
                <button
                  onClick={() => setConfirmVisible(true)}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-500/90 hover:bg-red-500 text-white text-xs font-bold transition-colors"
                >
                  <Trash2 className="w-3 h-3" />
                  Delete {selectedIds.size} transactions
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <span className="text-xs text-amber-400 font-semibold">This cannot be undone.</span>
                  <button
                    onClick={() => setConfirmVisible(false)}
                    className="px-3 py-1.5 rounded-xl border border-white/10 text-xs hover:bg-white/10"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleDelete}
                    className="px-3 py-1.5 rounded-xl bg-red-600 hover:bg-red-500 text-white text-xs font-bold"
                  >
                    Confirm Delete
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
