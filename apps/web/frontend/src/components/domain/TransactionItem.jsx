// Database needed
import React from "react";
import { Trash2, AlertTriangle, Edit2, ShieldCheck, User } from "lucide-react"; // Import ShieldCheck
import { CATEGORIES } from "../../../../../../packages/shared/config/constants";
import { normalizeDate } from "../../../../../../packages/shared/utils/helpers";

const TransactionItem = ({ item, onDelete, onEdit }) => {
  const category =
    CATEGORIES.find((c) => c.id === item.category) ||
    CATEGORIES.find((c) => c.id === "other");
  const Icon = category.icon;
  const isExpense = item.type === "expense";

  // Logic: If it has a 'confidence' score (from OCR), it's Verified.
  const isVerified = item.confidence > 0;

  let displayDate = "Unknown";
  try {
    const d = normalizeDate(item.date);
    displayDate = d.toLocaleDateString();
  } catch (e) {}

  const isFlagged = item.status === "flagged" || (item.reconciliation_flags && item.reconciliation_flags.length > 0);

  return (
    <div
      onClick={() => onEdit && onEdit(item)}
      className={`group flex items-center p-4 bg-white/5 backdrop-blur-md border ${isFlagged ? "border-rose-500/50 bg-rose-500/5" : "border-white/10"} rounded-3xl mb-3 transition-all hover:bg-white/10 relative overflow-hidden cursor-pointer`}
    >
      <div className={`p-3.5 rounded-2xl mr-4 ${category.color} shrink-0`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0 pr-4">
        <div className="flex items-center gap-2">
          {/* INTEGRITY BADGE */}
          {isVerified ? (
            <ShieldCheck
              className="w-3 h-3 text-emerald-400"
              title="Verified by Bank Statement"
            />
          ) : (
            <User
              className="w-3 h-3 text-slate-500"
              title="Manual User Entry"
            />
          )}
          {isFlagged && (
            <AlertTriangle className="w-4 h-4 text-rose-500" title="Reconciliation Failed - Review Required" />
          )}
          <h4 className="font-semibold text-blue-50 truncate text-base">
            {item.title}
          </h4>
        </div>

        <div className="flex items-center text-xs text-blue-300/70 mt-1">
          <span className="capitalize">{category.name}</span>
          <span className="mx-1.5 opacity-50">•</span>
          <span>{displayDate}</span>
          
          {isFlagged && item.reconciliation_flags && item.reconciliation_flags.length > 0 && (
            <span className="ml-2 text-[10px] text-rose-400 flex items-center gap-0.5 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
              {item.reconciliation_flags.join(", ")}
            </span>
          )}
          
          {item.confidence && item.confidence < 80 && !isFlagged && (
            <span className="ml-2 text-[10px] text-yellow-500 flex items-center gap-0.5 bg-yellow-500/10 px-2 py-0.5 rounded">
              <AlertTriangle className="w-3 h-3 mr-1" /> Verify
            </span>
          )}
        </div>
      </div>
      <div className="text-right shrink-0 flex flex-col items-end">
        <p
          className={`font-bold text-lg ${isExpense ? "text-rose-300" : "text-emerald-300"}`}
        >
          {isExpense ? "-" : "+"}₹
          {parseFloat(item.amount).toLocaleString("en-IN")}
        </p>

        <div className="flex gap-1 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {onEdit && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onEdit(item);
              }}
              className="p-2 text-slate-500 hover:text-blue-400 hover:bg-blue-500/10 rounded-full"
            >
              <Edit2 className="w-3.5 h-3.5" />
            </button>
          )}
          {onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(item.id);
              }}
              className="p-2 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-full"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default TransactionItem;
