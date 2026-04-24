import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, AlertTriangle, Calendar, Save, Trash2, CheckCircle2 } from "lucide-react";

const ReviewSkippedModal = ({ isOpen, onClose, items, onSave, statementType }) => {
  const [reviewList, setReviewList] = useState([]);

  React.useEffect(() => {
    if (items && items.length > 0) {
      setReviewList(
        items.map((item, idx) => ({
          ...item,
          tempId: idx,
          selectedDate: new Date().toISOString().split("T")[0],
          isSelected: true,
        }))
      );
    } else {
      setReviewList([]);
    }
  }, [items, isOpen]);

  const toggleSelect = (tempId) => {
    setReviewList((prev) =>
      prev.map((item) =>
        item.tempId === tempId ? { ...item, isSelected: !item.isSelected } : item
      )
    );
  };

  const updateDate = (tempId, date) => {
    setReviewList((prev) =>
      prev.map((item) =>
        item.tempId === tempId ? { ...item, selectedDate: date } : item
      )
    );
  };

  const handleBulkSave = () => {
    const toSave = reviewList
      .filter((item) => item.isSelected)
      .map((item) => ({
        ...item,
        date: item.selectedDate,
        source: "manual", // Mark as manual since date was manually provided
        account_type: statementType,
      }));
    onSave(toSave);
    onClose();
  };

  if (!isOpen) return null;

  const selectedCount = reviewList.filter((i) => i.isSelected).length;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-slate-950/80 backdrop-blur-md"
        />
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 20 }}
          className="relative w-full max-w-lg bg-slate-900 border border-white/10 rounded-[2.5rem] shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
        >
          {/* Header */}
          <div className="p-6 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-500/20 rounded-xl">
                <AlertTriangle className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <h3 className="text-white font-bold text-lg">Review Skipped Items</h3>
                <p className="text-xs text-slate-500">Dates couldn't be parsed automatically</p>
              </div>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full text-slate-400">
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
            {reviewList.map((item) => (
              <div
                key={item.tempId}
                className={`p-4 rounded-2xl border transition-all ${
                  item.isSelected
                    ? "bg-white/5 border-white/10"
                    : "bg-transparent border-white/5 opacity-50"
                }`}
              >
                <div className="flex justify-between items-start mb-3">
                  <div className="flex-1 min-w-0 pr-4">
                    <p className="text-sm font-bold text-blue-50 truncate">
                      {item.description || "Untitled Transaction"}
                    </p>
                    <p className="text-lg font-black text-white mt-0.5">
                      ₹{parseFloat(item.amount).toLocaleString("en-IN")}
                    </p>
                  </div>
                  <button
                    onClick={() => toggleSelect(item.tempId)}
                    className={`p-2 rounded-xl transition-colors ${
                      item.isSelected
                        ? "text-rose-400 hover:bg-rose-400/10"
                        : "text-emerald-400 hover:bg-emerald-400/10"
                    }`}
                  >
                    {item.isSelected ? <Trash2 className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
                  </button>
                </div>

                {item.isSelected && (
                  <div className="flex items-center gap-3 bg-white/5 p-2 rounded-xl">
                    <Calendar className="w-3.5 h-3.5 text-blue-400" />
                    <input
                      type="date"
                      value={item.selectedDate}
                      onChange={(e) => updateDate(item.tempId, e.target.value)}
                      className="bg-transparent text-xs text-blue-200 outline-none w-full"
                    />
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-white/5 bg-white/[0.02] flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 py-3 rounded-2xl font-bold text-slate-400 hover:bg-white/5 transition-all"
            >
              Skip All
            </button>
            <button
              onClick={handleBulkSave}
              disabled={selectedCount === 0}
              className="flex-[2] py-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 rounded-2xl font-bold text-white shadow-lg shadow-blue-900/20 flex items-center justify-center gap-2 transition-all"
            >
              <Save className="w-4 h-4" />
              Save {selectedCount} Transactions
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default ReviewSkippedModal;
