//Database needed
// Section 3 Add New Page
import React, { useState, useRef, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion"; // Added Framer Motion
import {
  Loader2,
  UploadCloud,
  AlertTriangle,
  WifiOff,
  Save,
  Zap,
} from "lucide-react";
import {
  CATEGORIES,
  TABS,
} from "../../../../../packages/shared/config/constants";
import { buildAuthHeader } from "../../../../../packages/shared/utils/helpers";
import UnitSelector from "../components/domain/UnitSelector";
import TransactionItem from "../components/domain/TransactionItem";
import StatementHub from "../components/ui/StatementHub";
import { apiFetch, API_BASE } from "../api";

const AddPage = ({
  user,
  authToken,
  apiBaseUrl,
  appId,
  setActiveTab,
  showToast,
  triggerConfirm,
  refreshData,
}) => {
  // --- MANUAL ENTRY STATE ---
  const [mode, setMode] = useState("manual");
  const [amount, setAmount] = useState("");
  const [desc, setDesc] = useState("");
  const [cat, setCat] = useState("food");
  const [type, setType] = useState("");
  const [transUnit, setTransUnit] = useState(1);
  const [isRecurring, setIsRecurring] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Removed offline scanning states, now handled by StatementHub.
  // --- OFFLINE SCANNER STATE ---
  const [draftTransactions, setDraftTransactions] = useState([]);

  const handleSave = async (e) => {
    e.preventDefault();

    // 1. Validation: Ensure user is logged in
    if (!user || (!user.user_id && !user.id)) {
      showToast("Error: User session not found. Please re-login.", "error");
      return;
    }

    setIsSubmitting(true);

    const finalAmount = Number(amount) * transUnit;
    console.log("AddPage: amount input =", { rawAmount: amount, parsedAmount: Number(amount), transUnit, finalAmount });
    const normalizedType = String(type || "").trim().toLowerCase();
    if (!["income", "expense"].includes(normalizedType)) {
      setIsSubmitting(false);
      showToast("Select transaction type: Income or Expense", "error");
      return;
    }

    // 2. Updated formData to match the finance service payload
    const formData = {
      title: desc, // Matches 'title' in models.py
      amount: String(finalAmount), // Send as string to avoid float precision loss
      type: normalizedType, // 'income' or 'expense'
      category: cat, // Matches the slug/id of the category
      is_recurring: isRecurring, // Note: Ensure this is added to models.py
    };

    try {
      const data = await apiFetch(`${apiBaseUrl}/transactions`, {
        method: "POST",
        body: JSON.stringify(formData),
      });

      console.log("AddPage transaction response:", data);
      showToast(isRecurring ? "Recurring bill added!" : "Added!", "success");
      if (refreshData) refreshData();
      // Clear form
      setAmount("");
      setDesc("");
      setTransUnit(1);
      setIsRecurring(false);
    } catch (e) {
      console.error("Submission Error:", e);
      showToast(`Server Error: ${e.message}`, "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="max-w-xl mx-auto pb-12"
    >
      {/* Tab Switcher */}
      <div className="flex bg-slate-900/50 backdrop-blur-xl p-1.5 rounded-2xl mb-8 border border-white/5 relative">
        <div className="flex w-full relative">
          <button
            onClick={() => setMode("manual")}
            className={`relative z-10 flex-1 py-3 rounded-xl text-sm font-bold transition-all duration-300 ${
              mode === "manual"
                ? "text-white"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            Manual
          </button>
          <button
            onClick={() => setMode("upload")}
            className={`relative z-10 flex-1 py-3 rounded-xl text-sm font-bold transition-all duration-300 ${
              mode === "upload"
                ? "text-white"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            Upload{" "}
            {draftTransactions.length > 0 && (
              <span className="bg-blue-500 text-white text-[9px] px-1.5 py-0.5 rounded-full ml-1 animate-pulse">
                {" "}
                {draftTransactions.length}{" "}
              </span>
            )}
          </button>
          {/* Animated Tab Background */}
          <motion.div
            className="absolute top-0 bottom-0 bg-white/10 rounded-xl shadow-lg border border-white/5"
            initial={false}
            animate={{ x: mode === "manual" ? "0%" : "100%", width: "50%" }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
          />
        </div>
      </div>

      <AnimatePresence mode="wait">
        {mode === "manual" ? (
          <motion.form
            key="manual-form"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 10 }}
            onSubmit={handleSave}
            className="space-y-6"
          >
            <div className="flex bg-white/5 p-1 rounded-xl border border-white/5">
              <button
                type="button"
                onClick={() => setType("expense")}
                className={`flex-1 py-3 rounded-lg text-sm font-bold transition-all ${
                  type === "expense"
                    ? "bg-rose-500/20 text-rose-300 shadow-[0_0_20px_rgba(244,63,94,0.1)]"
                    : "text-slate-500"
                }`}
              >
                Expense
              </button>
              <button
                type="button"
                onClick={() => setType("income")}
                className={`flex-1 py-3 rounded-lg text-sm font-bold transition-all ${
                  type === "income"
                    ? "bg-emerald-500/20 text-emerald-300 shadow-[0_0_20px_rgba(16,185,129,0.1)]"
                    : "text-slate-500"
                }`}
              >
                Income
              </button>
            </div>

            <div className="flex flex-col gap-6">
              <div className="text-center group">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-4 group-hover:text-blue-400 transition-colors">
                  Amount
                </label>
                <div className="relative inline-block w-full">
                  <span className="absolute left-1/2 -ml-20 top-1/2 -translate-y-1/2 text-slate-500 text-4xl font-light">
                    ₹
                  </span>
                  <input
                    type="text"
                    inputMode="decimal"
                    value={amount}
                    onChange={(e) => {
                      const val = e.target.value;
                      // Allow only valid decimal numbers
                      if (val === "" || /^\d+(\.\d{0,2})?$/.test(val)) {
                        setAmount(val);
                      }
                    }}
                    className="w-full text-center bg-transparent border-b-2 border-white/10 text-6xl font-black text-white py-4 outline-none focus:border-blue-500 transition-all placeholder:text-white/5"
                    placeholder="0"
                    required
                  />
                </div>
              </div>
              <UnitSelector
                currentUnit={transUnit}
                onSelect={setTransUnit}
                className="max-w-[280px] mx-auto w-full"
              />
            </div>

            <div className="grid grid-cols-4 gap-3">
              {CATEGORIES.map((c) => (
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  key={c.id}
                  type="button"
                  onClick={() => {
                    setCat(c.id);
                    if (!desc.trim()) {
                      setDesc(c.name);
                    }
                  }}
                  className={`p-3 rounded-2xl border flex flex-col items-center gap-2 transition-all duration-300 ${
                    cat === c.id
                      ? "bg-blue-500/20 border-blue-500/50 text-white shadow-[0_0_15px_rgba(59,130,246,0.2)]"
                      : "bg-white/5 border-transparent text-slate-500 opacity-60"
                  }`}
                >
                  <c.icon
                    className={`w-6 h-6 ${cat === c.id ? "text-blue-400" : ""}`}
                  />
                  <span className="text-[10px] font-medium">{c.name}</span>
                </motion.button>
              ))}
            </div>

            <input
              type="text"
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              className="w-full p-4 bg-white/5 border border-white/5 rounded-xl text-white outline-none focus:bg-white/10 focus:border-white/20 transition-all"
              placeholder="What was this for?"
              required
            />

            <motion.div
              whileTap={{ scale: 0.99 }}
              onClick={() => setIsRecurring(!isRecurring)}
              className={`p-4 rounded-xl border flex items-center justify-between cursor-pointer transition-all ${
                isRecurring
                  ? "bg-blue-500/10 border-blue-500/40"
                  : "bg-white/5 border-white/10"
              }`}
            >
              <div className="flex items-center gap-3">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors ${
                    isRecurring
                      ? "bg-blue-500 text-white shadow-lg shadow-blue-500/40"
                      : "bg-white/10 text-slate-400"
                  }`}
                >
                  <Zap className="w-5 h-5" />
                </div>
                <div>
                  <p
                    className={`text-sm font-bold ${
                      isRecurring ? "text-blue-300" : "text-slate-300"
                    }`}
                  >
                    Repeat Monthly
                  </p>
                  <p className="text-[10px] text-slate-500">
                    Auto-remind me every month
                  </p>
                </div>
              </div>
              <div
                className={`w-12 h-6 rounded-full relative transition-colors ${
                  isRecurring ? "bg-blue-600" : "bg-slate-700"
                }`}
              >
                <motion.div
                  animate={{ x: isRecurring ? 24 : 4 }}
                  className="absolute top-1 w-4 h-4 bg-white rounded-full shadow-md"
                />
              </div>
            </motion.div>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              disabled={isSubmitting}
              className="w-full bg-blue-600 hover:bg-blue-500 py-4 rounded-2xl font-black text-white shadow-xl shadow-blue-900/40 transition-all disabled:opacity-50"
            >
              {isSubmitting ? (
                <div className="flex items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Processing...</span>
                </div>
              ) : (
                "Save Transaction"
              )}
            </motion.button>
          </motion.form>
        ) : (
          <motion.div
            key="upload-section"
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
          >
             <StatementHub 
              user={user} 
              apiBaseUrl={apiBaseUrl} 
              showToast={showToast}
              refreshData={refreshData}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default AddPage;
