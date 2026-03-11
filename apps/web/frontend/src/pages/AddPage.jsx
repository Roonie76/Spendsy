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
  Trash2,
  Zap,
} from "lucide-react";
import {
  CATEGORIES,
  TABS,
} from "../../../../../packages/shared/config/constants";
import { buildAuthHeader } from "../../../../../packages/shared/utils/helpers";
import UnitSelector from "../components/domain/UnitSelector";
import TransactionItem from "../components/domain/TransactionItem";
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

  // --- OFFLINE SCANNER STATE ---
  const [parsing, setParsing] = useState(false);
  const [draftTransactions, setDraftTransactions] = useState([]);
  const [ocrProgress, setOcrProgress] = useState(0);
  const [isScanned, setIsScanned] = useState(false);
  const [alreadyPersisted, setAlreadyPersisted] = useState(false);
  const fileRef = useRef(null);

  const parsedSummary = useMemo(() => {
    return draftTransactions.reduce(
      (acc, tx) => {
        const amount = Number(tx.amount || 0);
        const normalizedType = String(tx.type || tx.tx_type || "expense").toLowerCase();
        if (normalizedType === "income") acc.income += amount;
        else acc.expense += amount;
        acc.balance = acc.income - acc.expense;
        return acc;
      },
      { income: 0, expense: 0, balance: 0 },
    );
  }, [draftTransactions]);

  useEffect(() => {
    // No-op for now; previously loaded offline drafts from IndexedDB.
  }, [mode]);

  const handleSave = async (e) => {
    e.preventDefault();

    // 1. Validation: Ensure user is logged in
    if (!user || (!user.user_id && !user.id)) {
      showToast("Error: User session not found. Please re-login.", "error");
      return;
    }

    setIsSubmitting(true);

    const finalAmount = parseFloat(amount) * transUnit;
    const normalizedType = String(type || "").trim().toLowerCase();
    if (!["income", "expense"].includes(normalizedType)) {
      setIsSubmitting(false);
      showToast("Select transaction type: Income or Expense", "error");
      return;
    }

    // 2. Updated formData to match the finance service payload
    const formData = {
      title: desc, // Matches 'title' in models.py
      amount: finalAmount,
      type: normalizedType, // 'income' or 'expense'
      category: cat, // Matches the slug/id of the category
      is_recurring: isRecurring, // Note: Ensure this is added to models.py
    };

    try {
      const data = await apiFetch(`${apiBaseUrl}/transactions`, {
        method: "POST",
        body: JSON.stringify(formData),
      });

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

  const handleFile = async (e) => {
    const f = e.target.files[0];
    if (!f) return;

    setParsing(true);
    setIsScanned(false);
    setAlreadyPersisted(false);

    try {
      const formData = new FormData();
      formData.append("file", f);

      // We let apiFetch handle auth via cookie, but since this is FormData,
      // the browser needs to set the Content-Type with the boundary string.
      // We must explicitly ensure we don't set Content-Type: application/json here.
      // apiFetch should handle FormData automatically if not overridden.
      const data = await apiFetch(`${apiBaseUrl}/parse-statement`, {
        method: "POST",
        body: formData,
        // Optional: specify headers: {} to override any default if necessary, 
        // but apiFetch typically relies on the caller not setting Content-Type for FormData
      });

      const parserPayload = data?.data || data;

      if (Array.isArray(parserPayload.transactions) && parserPayload.transactions.length) {
        setDraftTransactions(parserPayload.transactions);
        setAlreadyPersisted(true);
        if (refreshData) {
          await refreshData();
        }
        showToast("Statement uploaded successfully.", "success");
      } else {
        showToast("No transactions found in statement", "error");
      }
    } catch (err) {
      console.error("Parser upload error:", err);
      showToast(
        `Error uploading file to parser: ${err?.message || "Unknown error"}`,
        "error",
      );
    } finally {
      setParsing(false);
    }
  };

  const handleSyncToCloud = () => {
    if (alreadyPersisted) {
      showToast("These parsed transactions are already saved.", "info");
      return;
    }

    // 1. Session Check
    if (!user || (!user.user_id && !user.id)) {
      showToast("User session not found. Please re-login.", "error");
      return;
    }

    triggerConfirm(
      `Sync ${draftTransactions.length} items to your Database?`,
      async () => {
        setIsSubmitting(true);
        try {
          // Map the promises for individual POST requests
          const promises = draftTransactions.map((t) => {
            // Data Normalization for Django Backend
            const normalizedType =
              t.type?.toLowerCase().includes("income") ||
              t.type?.toLowerCase() === "cr"
                ? "income"
                : "expense";

            return apiFetch(`${apiBaseUrl}/transactions`, {
              method: "POST",
              body: JSON.stringify({
                title: t.description || t.title || "Scanned Transaction",
                amount: parseFloat(t.amount),
                type: normalizedType,
                category: t.category?.toLowerCase() || "other",
                is_recurring: false,
              }),
            })
            // apiFetch throws on error, so we catch it and return an object indicating failure
            .then(res => ({ ok: true }))
            .catch(err => ({ ok: false }));
          });

          const results = await Promise.all(promises);

          // Check if any requests failed
          const failed = results.filter((r) => !r.ok);

          if (failed.length === 0) {
            setDraftTransactions([]);
            showToast("All items synced to Cloud!", "success");

            if (refreshData) refreshData(); // <--- THIS triggers the frontend to pull the new Django data

            setTimeout(() => setActiveTab(TABS.HOME), 1500);
          } else {
            showToast(
              `Synced ${results.length - failed.length} items. ${failed.length} failed.`,
              "warning",
            );
          }
        } catch (e) {
          console.error("Sync Error:", e);
          showToast("Sync failed. Check server connection.", "error");
        } finally {
          setIsSubmitting(false);
        }
      },
    );
  };

  const clearLocalData = async () => {
    triggerConfirm("Discard all local drafts?", async () => {
      setDraftTransactions([]);
      setAlreadyPersisted(false);
      showToast("Drafts cleared", "info");
    });
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
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
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
                  onClick={() => setCat(c.id)}
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
            className="space-y-6"
          >
            <motion.div
              whileHover={{ scale: 1.01, borderColor: "rgba(59,130,246,0.5)" }}
              onClick={() => !parsing && fileRef.current.click()}
              className={`border-2 border-dashed border-white/10 rounded-[2.5rem] p-12 text-center cursor-pointer transition-all bg-white/[0.02] relative overflow-hidden ${
                parsing ? "opacity-80 cursor-not-allowed" : ""
              }`}
            >
              {parsing ? (
                <div className="relative z-10">
                  <Loader2 className="w-12 h-12 text-blue-400 mx-auto mb-4 animate-spin" />
                  <h3 className="font-bold text-white text-lg">
                    Processing Locally...
                  </h3>
                  {ocrProgress > 0 && (
                    <div className="mt-4 w-48 mx-auto bg-white/5 rounded-full h-1.5 overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${ocrProgress}%` }}
                        className="bg-blue-500 h-full"
                      />
                    </div>
                  )}
                  <p className="text-[10px] text-slate-500 mt-4 uppercase tracking-widest">
                    Privacy Protected: No Cloud processing
                  </p>
                </div>
              ) : (
                <div className="relative z-10">
                  <div className="w-16 h-16 bg-blue-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-blue-500/20">
                    <UploadCloud className="w-8 h-8 text-blue-400" />
                  </div>
                  <h3 className="font-bold text-white text-lg">
                    Scan Statement
                  </h3>
                  <p className="text-xs text-slate-500 mt-2">
                    SBI, HDFC, ICICI, Axis • PDF, CSV, or XLSX
                  </p>
                </div>
              )}
              <input
                type="file"
                ref={fileRef}
                onChange={handleFile}
                className="hidden"
                accept=".pdf,.csv,.xlsx"
                disabled={parsing}
              />
            </motion.div>

            {draftTransactions.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4"
              >
                <div className="flex justify-between items-center px-1">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full animate-ping" />
                    <h3 className="font-bold text-white">
                      Offline Drafts ({draftTransactions.length})
                    </h3>
                  </div>
                  <button
                    onClick={clearLocalData}
                    className="p-2 hover:bg-rose-500/10 rounded-full text-rose-400 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4">
                    <p className="text-[10px] uppercase tracking-wider text-emerald-300/80">Income</p>
                    <p className="text-xl font-black text-emerald-300">
                      ₹{parsedSummary.income.toFixed(2)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4">
                    <p className="text-[10px] uppercase tracking-wider text-rose-300/80">Expense</p>
                    <p className="text-xl font-black text-rose-300">
                      ₹{parsedSummary.expense.toFixed(2)}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-blue-500/30 bg-blue-500/10 p-4">
                    <p className="text-[10px] uppercase tracking-wider text-blue-300/80">Balance</p>
                    <p className="text-xl font-black text-blue-200">
                      ₹{parsedSummary.balance.toFixed(2)}
                    </p>
                  </div>
                </div>

                {draftTransactions.some((t) => t.confidence < 70) && (
                  <div className="bg-amber-500/10 border border-amber-500/20 p-4 rounded-2xl flex items-start gap-3">
                    <AlertTriangle className="w-5 h-5 text-amber-500 shrink-0" />
                    <div>
                      <p className="text-sm text-amber-200 font-bold">
                        Review Needed
                      </p>
                      <p className="text-xs text-amber-200/70">
                        Some scans were low-quality. Please verify amounts
                        before syncing.
                      </p>
                    </div>
                  </div>
                )}

                <div className="max-h-[400px] overflow-y-auto space-y-3 mb-6 pr-2 custom-scrollbar">
                  {draftTransactions.map((t, i) => (
                    <motion.div
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      key={i}
                    >
                      <TransactionItem item={t} />
                    </motion.div>
                  ))}
                </div>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleSyncToCloud}
                  disabled={isSubmitting || alreadyPersisted}
                  className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 py-4 rounded-2xl font-black text-white shadow-xl shadow-indigo-900/40 flex items-center justify-center gap-3"
                >
                  {isSubmitting ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Save className="w-5 h-5" />
                  )}
                  {isSubmitting
                    ? "Syncing to Cloud..."
                    : alreadyPersisted
                      ? "Already Saved"
                      : "Push All to Cloud"}
                </motion.button>
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default AddPage;
