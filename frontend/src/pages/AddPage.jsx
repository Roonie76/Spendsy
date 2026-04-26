import React, { useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Loader2,
  Zap,
  AlertTriangle,
  CheckCircle2,
  Info,
} from "lucide-react";
import { CATEGORIES } from "@shared/config/constants";
import UnitSelector from "../components/domain/UnitSelector";
import StatementHub from "../components/ui/StatementHub";
import { apiFetch } from "../api";
import { cn } from "@shared/utils/cn";

// Maximum single transaction amount (₹100 Cr)
const MAX_AMOUNT = 1_000_000_000;

const AddPage = ({
  user,
  authToken,
  apiBaseUrl,
  appId,
  setActiveTab,
  showToast,
  triggerConfirm,
  refreshData,
  theme = "dark",
}) => {
  // --- FORM STATE ---
  const [mode, setMode] = useState("manual");
  const [amount, setAmount] = useState("");
  const [desc, setDesc] = useState("");
  const [cat, setCat] = useState("food");
  const [type, setType] = useState("");
  const [transUnit, setTransUnit] = useState(1);
  const [isRecurring, setIsRecurring] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Inline validation state
  const [touched, setTouched] = useState({});
  const amountRef = useRef(null);
  const submitTimerRef = useRef(null);

  // --- VALIDATION HELPERS ---
  const finalAmount = Number(amount || 0) * transUnit;
  const normalizedType = String(type || "").trim().toLowerCase();
  const isTypeValid = ["income", "expense"].includes(normalizedType);
  const isAmountValid = amount !== "" && finalAmount > 0 && finalAmount <= MAX_AMOUNT;
  const isDescValid = desc.trim().length > 0;
  const isFormValid = isTypeValid && isAmountValid && isDescValid;

  const getAmountError = () => {
    if (!touched.amount || amount === "") return null;
    if (Number(amount) === 0) return "Amount cannot be zero";
    if (finalAmount < 0) return "Amount cannot be negative";
    if (finalAmount > MAX_AMOUNT) return "Amount exceeds ₹100 Cr limit";
    return null;
  };

  const amountError = getAmountError();

  // --- FORM RESET ---
  const resetForm = useCallback(() => {
    setAmount("");
    setDesc("");
    setCat("food");
    setType("");
    setTransUnit(1);
    setIsRecurring(false);
    setTouched({});
    // Refocus the amount input for next entry
    setTimeout(() => amountRef.current?.focus(), 100);
  }, []);

  // --- SUBMIT HANDLER with debounce ---
  const handleSave = async (e) => {
    e.preventDefault();

    // Debounce: prevent rapid double-submissions
    if (submitTimerRef.current) return;
    submitTimerRef.current = setTimeout(() => { submitTimerRef.current = null; }, 1000);

    // Mark all fields as touched to show validation
    setTouched({ amount: true, type: true, desc: true });

    // Validate user session
    if (!user || (!user.user_id && !user.id)) {
      showToast("Session expired. Please log in again.", "error");
      return;
    }

    // Validate form
    if (!isTypeValid) {
      showToast("Select a transaction type: Income or Expense", "error");
      return;
    }
    if (!isAmountValid) {
      showToast(amountError || "Enter a valid amount", "error");
      return;
    }
    if (!isDescValid) {
      showToast("Add a description for this transaction", "error");
      return;
    }

    // For recurring transactions, ask for confirmation
    const doSave = async () => {
      setIsSubmitting(true);

      const formData = {
        title: desc.trim(),
        amount: String(finalAmount),
        type: normalizedType,
        category: cat,
        is_recurring: isRecurring,
      };

      try {
        await apiFetch(`${apiBaseUrl}/transactions`, {
          method: "POST",
          body: JSON.stringify(formData),
        });

        showToast(
          isRecurring
            ? `Recurring ${normalizedType} of ₹${finalAmount.toLocaleString("en-IN")} added`
            : `${normalizedType === "income" ? "Income" : "Expense"} of ₹${finalAmount.toLocaleString("en-IN")} saved`,
          "success"
        );
        if (refreshData) refreshData();
        resetForm();
      } catch (err) {
        console.error("Submission Error:", err);
        const msg = err?.response?.status === 429
          ? "Too many requests. Please wait a moment."
          : err?.response?.status >= 500
            ? "Server error. Please try again later."
            : err?.message || "Failed to save transaction";
        showToast(msg, "error");
      } finally {
        setIsSubmitting(false);
      }
    };

    if (isRecurring && triggerConfirm) {
      triggerConfirm(
        `Add recurring monthly ${normalizedType} of ₹${finalAmount.toLocaleString("en-IN")} for "${desc.trim()}"?`,
        doSave
      );
    } else {
      doSave();
    }
  };

  // --- AUTO-FILL DESCRIPTION from category (only if empty or was auto-filled) ---
  const handleCategorySelect = (category) => {
    const prevCatName = CATEGORIES.find((c) => c.id === cat)?.name || "";
    setCat(category.id);
    if (!desc.trim() || desc === prevCatName) {
      setDesc(category.name);
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
      <div
        className={cn(
          "flex p-1.5 rounded-2xl mb-8 border relative",
          theme === "dark"
            ? "bg-slate-900/50 backdrop-blur-xl border-white/5"
            : "bg-slate-100 border-slate-200",
        )}
        role="tablist"
        aria-label="Transaction entry method"
      >
        <div className="flex w-full relative">
          <button
            role="tab"
            aria-selected={mode === "manual"}
            aria-controls="panel-manual"
            onClick={() => setMode("manual")}
            className={cn(
              "relative z-10 flex-1 py-3 rounded-xl text-sm font-bold transition-all duration-300",
              mode === "manual"
                ? theme === "dark" ? "text-white" : "text-slate-900"
                : theme === "dark" ? "text-slate-500 hover:text-slate-300" : "text-slate-400 hover:text-slate-600",
            )}
          >
            Manual
          </button>
          <button
            role="tab"
            aria-selected={mode === "upload"}
            aria-controls="panel-upload"
            onClick={() => setMode("upload")}
            className={cn(
              "relative z-10 flex-1 py-3 rounded-xl text-sm font-bold transition-all duration-300",
              mode === "upload"
                ? theme === "dark" ? "text-white" : "text-slate-900"
                : theme === "dark" ? "text-slate-500 hover:text-slate-300" : "text-slate-400 hover:text-slate-600",
            )}
          >
            Upload
          </button>
          {/* Animated Tab Background */}
          <motion.div
            className={cn(
              "absolute top-0 bottom-0 rounded-xl shadow-lg border",
              theme === "dark"
                ? "bg-white/10 border-white/5"
                : "bg-white border-slate-200 shadow-sm",
            )}
            initial={false}
            animate={{ x: mode === "manual" ? "0%" : "100%", width: "50%" }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
          />
        </div>
      </div>

      <AnimatePresence mode="wait">
        {mode === "manual" ? (
          <motion.form
            id="panel-manual"
            role="tabpanel"
            key="manual-form"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 10 }}
            onSubmit={handleSave}
            className="space-y-6"
            aria-label="Add transaction manually"
          >
            {/* Type Selector */}
            <fieldset>
              <legend className="sr-only">Transaction type</legend>
              <div className={cn(
                "flex p-1 rounded-xl border",
                theme === "dark" ? "bg-white/5 border-white/5" : "bg-slate-50 border-slate-200",
                touched.type && !isTypeValid && "ring-2 ring-rose-500/50",
              )}>
                <button
                  type="button"
                  onClick={() => { setType("income"); setTouched((p) => ({ ...p, type: true })); }}
                  aria-pressed={type === "income"}
                  className={cn(
                    "flex-1 py-3 rounded-lg text-sm font-bold transition-all",
                    type === "income"
                      ? "bg-emerald-500/20 text-emerald-300 shadow-[0_0_20px_rgba(16,185,129,0.1)]"
                      : theme === "dark" ? "text-slate-500" : "text-slate-400",
                  )}
                >
                  Income
                </button>
                <button
                  type="button"
                  onClick={() => { setType("expense"); setTouched((p) => ({ ...p, type: true })); }}
                  aria-pressed={type === "expense"}
                  className={cn(
                    "flex-1 py-3 rounded-lg text-sm font-bold transition-all",
                    type === "expense"
                      ? "bg-rose-500/20 text-rose-300 shadow-[0_0_20px_rgba(244,63,94,0.1)]"
                      : theme === "dark" ? "text-slate-500" : "text-slate-400",
                  )}
                >
                  Expense
                </button>
              </div>
              {touched.type && !isTypeValid && (
                <p className="text-rose-400 text-xs mt-2 flex items-center gap-1" role="alert">
                  <AlertTriangle className="w-3 h-3" aria-hidden="true" />
                  Select Income or Expense
                </p>
              )}
            </fieldset>

            {/* Amount Input */}
            <div className="flex flex-col gap-4">
              <div className="text-center group">
                <label
                  htmlFor="amount-input"
                  className={cn(
                    "block text-xs font-bold uppercase tracking-widest mb-4 transition-colors",
                    theme === "dark"
                      ? "text-slate-500 group-hover:text-blue-400"
                      : "text-slate-400 group-hover:text-blue-500",
                  )}
                >
                  Amount
                </label>
                <div className="relative inline-flex items-baseline justify-center w-full gap-2">
                  <span className={cn("text-2xl sm:text-3xl md:text-4xl font-light", theme === "dark" ? "text-slate-500" : "text-slate-300")}>
                    ₹
                  </span>
                  <input
                    id="amount-input"
                    ref={amountRef}
                    type="text"
                    inputMode="decimal"
                    value={amount}
                    onChange={(e) => {
                      const val = e.target.value;
                      if (val === "" || /^\d+(\.\d{0,2})?$/.test(val)) {
                        setAmount(val);
                      }
                    }}
                    onBlur={() => setTouched((p) => ({ ...p, amount: true }))}
                    aria-invalid={!!amountError}
                    aria-describedby={amountError ? "amount-error" : undefined}
                    className={cn(
                      "flex-1 min-w-0 text-center bg-transparent border-b-2 text-4xl sm:text-5xl md:text-6xl font-black py-3 sm:py-4 outline-none transition-all placeholder:opacity-5",
                      theme === "dark" ? "text-white" : "text-slate-900",
                      amountError
                        ? "border-rose-500"
                        : "border-white/10 focus:border-blue-500",
                    )}
                    placeholder="0"
                    required
                    autoComplete="off"
                  />
                </div>
                {amountError && (
                  <p id="amount-error" className="text-rose-400 text-xs mt-2 flex items-center justify-center gap-1" role="alert">
                    <AlertTriangle className="w-3 h-3" aria-hidden="true" />
                    {amountError}
                  </p>
                )}
                {amount && !amountError && transUnit > 1 && (
                  <p className={cn("text-xs mt-2", theme === "dark" ? "text-blue-400/60" : "text-blue-500/60")}>
                    = ₹{finalAmount.toLocaleString("en-IN")}
                  </p>
                )}
              </div>
              <UnitSelector
                currentUnit={transUnit}
                onSelect={setTransUnit}
                className="max-w-[280px] mx-auto w-full"
              />
            </div>

            {/* Category Grid */}
            <fieldset>
              <legend className={cn(
                "text-xs font-bold uppercase tracking-widest mb-3",
                theme === "dark" ? "text-slate-500" : "text-slate-400",
              )}>
                Category
              </legend>
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 sm:gap-3" role="radiogroup" aria-label="Transaction category">
                {CATEGORIES.map((c) => (
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    key={c.id}
                    type="button"
                    role="radio"
                    aria-checked={cat === c.id}
                    onClick={() => handleCategorySelect(c)}
                    className={cn(
                      "p-3 rounded-2xl border flex flex-col items-center gap-2 transition-all duration-300",
                      cat === c.id
                        ? "bg-blue-500/20 border-blue-500/50 text-white shadow-[0_0_15px_rgba(59,130,246,0.2)]"
                        : theme === "dark"
                          ? "bg-white/5 border-transparent text-slate-500 opacity-60"
                          : "bg-slate-50 border-slate-200 text-slate-400 opacity-70",
                    )}
                  >
                    <c.icon
                      className={cn("w-6 h-6", cat === c.id ? "text-blue-400" : "")}
                      aria-hidden="true"
                    />
                    <span className="text-[10px] font-medium">{c.name}</span>
                  </motion.button>
                ))}
              </div>
            </fieldset>

            {/* Description Input */}
            <div>
              <label htmlFor="desc-input" className="sr-only">Description</label>
              <input
                id="desc-input"
                type="text"
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
                onBlur={() => setTouched((p) => ({ ...p, desc: true }))}
                maxLength={200}
                aria-invalid={touched.desc && !isDescValid}
                className={cn(
                  "w-full p-4 border rounded-xl outline-none transition-all",
                  theme === "dark"
                    ? "bg-white/5 border-white/5 text-white focus:bg-white/10 focus:border-white/20"
                    : "bg-white border-slate-200 text-slate-900 focus:bg-white focus:border-blue-300",
                  touched.desc && !isDescValid && "ring-2 ring-rose-500/50",
                )}
                placeholder="What was this for?"
                required
              />
              {touched.desc && !isDescValid && (
                <p className="text-rose-400 text-xs mt-2 flex items-center gap-1" role="alert">
                  <AlertTriangle className="w-3 h-3" aria-hidden="true" />
                  Description is required
                </p>
              )}
              <p className={cn("text-[10px] mt-1 text-right", theme === "dark" ? "text-slate-600" : "text-slate-400")}>
                {desc.length}/200
              </p>
            </div>

            {/* Repeat Monthly Toggle */}
            <motion.div
              whileTap={{ scale: 0.99 }}
              onClick={() => setIsRecurring(!isRecurring)}
              role="switch"
              aria-checked={isRecurring}
              aria-label="Repeat this transaction monthly"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setIsRecurring(!isRecurring); } }}
              className={cn(
                "p-4 rounded-xl border flex items-center justify-between cursor-pointer transition-all",
                isRecurring
                  ? "bg-blue-500/10 border-blue-500/40"
                  : theme === "dark"
                    ? "bg-white/5 border-white/10"
                    : "bg-slate-50 border-slate-200",
              )}
            >
              <div className="flex items-center gap-3">
                <div
                  className={cn(
                    "w-10 h-10 rounded-full flex items-center justify-center transition-colors",
                    isRecurring
                      ? "bg-blue-500 text-white shadow-lg shadow-blue-500/40"
                      : theme === "dark"
                        ? "bg-white/10 text-slate-400"
                        : "bg-slate-200 text-slate-400",
                  )}
                >
                  <Zap className="w-5 h-5" aria-hidden="true" />
                </div>
                <div>
                  <p className={cn("text-sm font-bold", isRecurring ? "text-blue-300" : theme === "dark" ? "text-slate-300" : "text-slate-600")}>
                    Repeat Monthly
                  </p>
                  <p className={cn("text-[10px]", theme === "dark" ? "text-slate-500" : "text-slate-400")}>
                    Auto-remind me every month
                  </p>
                </div>
              </div>
              <div
                className={cn(
                  "w-12 h-6 rounded-full relative transition-colors",
                  isRecurring ? "bg-blue-600" : theme === "dark" ? "bg-slate-700" : "bg-slate-300",
                )}
                aria-hidden="true"
              >
                <motion.div
                  animate={{ x: isRecurring ? 24 : 4 }}
                  className="absolute top-1 w-4 h-4 bg-white rounded-full shadow-md"
                />
              </div>
            </motion.div>

            {/* Recurring info hint */}
            {isRecurring && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className={cn("flex items-start gap-2 p-3 rounded-lg text-xs", theme === "dark" ? "bg-blue-500/5 text-blue-400/70" : "bg-blue-50 text-blue-600")}
              >
                <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" aria-hidden="true" />
                <span>This will be saved as a recurring entry. You'll be reminded monthly to log it.</span>
              </motion.div>
            )}

            {/* Submit Button */}
            <motion.button
              type="submit"
              whileHover={isFormValid && !isSubmitting ? { scale: 1.02 } : {}}
              whileTap={isFormValid && !isSubmitting ? { scale: 0.98 } : {}}
              disabled={isSubmitting || !isFormValid}
              aria-label={isSubmitting ? "Saving transaction..." : "Save transaction"}
              className={cn(
                "w-full py-4 rounded-2xl font-black text-white shadow-xl transition-all",
                isFormValid && !isSubmitting
                  ? "bg-blue-600 hover:bg-blue-500 shadow-blue-900/40"
                  : "bg-blue-600/40 cursor-not-allowed shadow-none",
                "disabled:opacity-50",
              )}
            >
              {isSubmitting ? (
                <div className="flex items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" aria-hidden="true" />
                  <span>Saving...</span>
                </div>
              ) : (
                <div className="flex items-center justify-center gap-2">
                  <CheckCircle2 className="w-5 h-5" aria-hidden="true" />
                  <span>Save Transaction</span>
                </div>
              )}
            </motion.button>

            {/* Form completeness hint */}
            {!isFormValid && touched.amount && (
              <p className={cn("text-center text-xs", theme === "dark" ? "text-slate-600" : "text-slate-400")}>
                {!isTypeValid && "Select type · "}
                {!isAmountValid && "Enter amount · "}
                {!isDescValid && "Add description"}
              </p>
            )}
          </motion.form>
        ) : (
          <motion.div
            id="panel-upload"
            role="tabpanel"
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
