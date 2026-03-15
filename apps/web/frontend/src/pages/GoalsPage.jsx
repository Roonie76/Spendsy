/**
 * GoalsPage.jsx – Saving Goals Dashboard (Phase 6)
 *
 * A premium, animated goals management page where users can create,
 * track, and complete personal financial goals like "Emergency Fund"
 * or "New Car".
 */

import React, { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Target,
  Plus,
  Trash2,
  CheckCircle2,
  Calendar,
  TrendingUp,
  X,
  ChevronRight,
} from "lucide-react";
import { apiFetch, API_BASE } from "../api";
import { formatIndianCompact } from "../../../../../packages/shared/utils/helpers";
import { cn } from "../../../../../packages/shared/utils/cn";

// ─── Category config ──────────────────────────────────────────────────────────

const CATEGORY_META = {
  emergency: { label: "Emergency Fund", color: "bg-rose-500", icon: "🛡️" },
  travel: { label: "Travel", color: "bg-sky-500", icon: "✈️" },
  education: { label: "Education", color: "bg-violet-500", icon: "🎓" },
  asset: { label: "Asset Purchase", color: "bg-amber-500", icon: "🏠" },
  retirement: { label: "Retirement", color: "bg-emerald-500", icon: "🌱" },
  savings: { label: "Savings", color: "bg-blue-500", icon: "💰" },
  other: { label: "Other", color: "bg-gray-500", icon: "📌" },
};

// ─── Add Goal Modal ───────────────────────────────────────────────────────────

function AddGoalModal({ onClose, onSave, theme }) {
  const [form, setForm] = useState({
    title: "",
    description: "",
    target_amount: "",
    current_amount: "0",
    target_date: "",
    category: "savings",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!form.title || !form.target_amount) {
      setError("Title and target amount are required.");
      return;
    }
    setSaving(true);
    try {
      const result = await apiFetch(`${API_BASE}/goals`, {
        method: "POST",
        body: JSON.stringify({
          title: form.title,
          description: form.description || undefined,
          target_amount: parseFloat(form.target_amount),
          current_amount: parseFloat(form.current_amount || "0"),
          target_date: form.target_date || undefined,
          category: form.category,
        }),
      });
      onSave(result.data);
      onClose();
    } catch (err) {
      setError(err.message || "Failed to create goal.");
    } finally {
      setSaving(false);
    }
  };

  const inputClass = cn(
    "w-full rounded-2xl border px-4 py-3 text-sm font-medium outline-none transition-colors",
    theme === "dark"
      ? "bg-white/5 border-white/10 text-white placeholder-white/30 focus:border-blue-400"
      : "bg-gray-50 border-gray-200 text-gray-900 placeholder-gray-400 focus:border-blue-500"
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.92 }}
        transition={{ type: "spring", stiffness: 400, damping: 25 }}
        className={cn(
          "relative w-full max-w-md rounded-[2.5rem] border p-8 shadow-2xl",
          theme === "dark"
            ? "bg-[#0d1117] border-white/10"
            : "bg-white border-gray-100"
        )}
      >
        <button
          onClick={onClose}
          className="absolute top-6 right-6 opacity-40 hover:opacity-100 transition-opacity"
        >
          <X className={cn("w-5 h-5", theme === "dark" ? "text-white" : "text-gray-900")} />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-2xl bg-blue-500/10">
            <Target className="w-5 h-5 text-blue-500" />
          </div>
          <h2 className={cn("text-xl font-black tracking-tight", theme === "dark" ? "text-white" : "text-gray-900")}>
            New Goal
          </h2>
        </div>

        {error && (
          <p className="mb-4 text-xs font-bold text-rose-400 bg-rose-500/10 px-4 py-2 rounded-xl">
            {error}
          </p>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            className={inputClass}
            placeholder="Goal title (e.g. Emergency Fund)"
            value={form.title}
            onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
          />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] font-black uppercase tracking-widest opacity-40 mb-1 block">Target (₹)</label>
              <input
                className={inputClass}
                type="number"
                min="1"
                placeholder="100000"
                value={form.target_amount}
                onChange={(e) => setForm((f) => ({ ...f, target_amount: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-[10px] font-black uppercase tracking-widest opacity-40 mb-1 block">Saved So Far (₹)</label>
              <input
                className={inputClass}
                type="number"
                min="0"
                placeholder="0"
                value={form.current_amount}
                onChange={(e) => setForm((f) => ({ ...f, current_amount: e.target.value }))}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] font-black uppercase tracking-widest opacity-40 mb-1 block">Target Date</label>
              <input
                className={inputClass}
                type="date"
                value={form.target_date}
                onChange={(e) => setForm((f) => ({ ...f, target_date: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-[10px] font-black uppercase tracking-widest opacity-40 mb-1 block">Category</label>
              <select
                className={cn(inputClass, "cursor-pointer")}
                value={form.category}
                onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
              >
                {Object.entries(CATEGORY_META).map(([k, v]) => (
                  <option key={k} value={k}>{v.icon} {v.label}</option>
                ))}
              </select>
            </div>
          </div>

          <input
            className={inputClass}
            placeholder="Short description (optional)"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          />

          <button
            type="submit"
            disabled={saving}
            className="w-full py-3.5 rounded-2xl bg-blue-600 text-white text-sm font-black tracking-widest uppercase hover:bg-blue-500 transition-colors disabled:opacity-50"
          >
            {saving ? "Creating…" : "Create Goal"}
          </button>
        </form>
      </motion.div>
    </div>
  );
}

// ─── Goal Card ────────────────────────────────────────────────────────────────

function GoalCard({ goal, onDelete, onUpdate, theme }) {
  const meta = CATEGORY_META[goal.category] || CATEGORY_META.other;
  const pct = Math.min(100, parseFloat(goal.progress_percent || 0));
  const isComplete = goal.is_completed;

  const bouncySpring = { type: "spring", stiffness: 500, damping: 22 };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.94 }}
      whileHover={{ y: -4 }}
      transition={bouncySpring}
      className={cn(
        "relative p-6 rounded-[2.5rem] border shadow-xl",
        isComplete
          ? "bg-emerald-500/5 border-emerald-500/20"
          : theme === "dark"
          ? "bg-white/[0.04] border-white/10 backdrop-blur-md"
          : "bg-white border-white shadow-lg"
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{meta.icon}</span>
          <div>
            <h3 className={cn("font-black text-base tracking-tight", theme === "dark" ? "text-white" : "text-gray-900")}>
              {goal.title}
            </h3>
            <span className={cn(
              "text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full",
              `${meta.color}/10 text-${meta.color.replace("bg-", "")}`
            )}>
              {meta.label}
            </span>
          </div>
        </div>
        {isComplete ? (
          <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0" />
        ) : (
          <button
            onClick={() => onDelete(goal.id)}
            className="opacity-20 hover:opacity-70 transition-opacity"
          >
            <Trash2 className={cn("w-4 h-4", theme === "dark" ? "text-white" : "text-gray-900")} />
          </button>
        )}
      </div>

      {/* Progress */}
      <div className="mb-4">
        <div className="flex justify-between text-[11px] font-bold opacity-50 mb-2">
          <span>₹{parseFloat(goal.current_amount || 0).toLocaleString("en-IN")}</span>
          <span>₹{parseFloat(goal.target_amount || 0).toLocaleString("en-IN")}</span>
        </div>
        <div className="h-3 rounded-full bg-white/5 overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 1.2, ease: "circOut" }}
            className={cn(
              "h-full rounded-full",
              isComplete ? "bg-emerald-500" : meta.color.replace("bg-", "bg-")
            )}
          />
        </div>
        <p className={cn("text-right text-[10px] font-black mt-1", isComplete ? "text-emerald-500" : "opacity-40")}>
          {isComplete ? "🎉 Goal Reached!" : `${pct}% complete`}
        </p>
      </div>

      {/* Footer */}
      <div className="flex gap-3 flex-wrap text-[10px] font-bold opacity-40">
        {goal.target_date && (
          <span className="flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            By {new Date(goal.target_date).toLocaleDateString("en-IN", { month: "short", year: "numeric" })}
          </span>
        )}
        {goal.projected_monthly_saving && !isComplete && (
          <span className="flex items-center gap-1">
            <TrendingUp className="w-3 h-3" />
            Save ₹{parseFloat(goal.projected_monthly_saving).toLocaleString("en-IN")}/mo
          </span>
        )}
      </div>

      {/* Quick Add Progress */}
      {!isComplete && (
        <div className="mt-4 flex gap-2">
          {[1000, 5000, 10000].map((amt) => (
            <button
              key={amt}
              onClick={() => onUpdate(goal.id, parseFloat(goal.current_amount) + amt)}
              className={cn(
                "flex-1 py-2 rounded-xl text-[10px] font-black uppercase tracking-wider transition-colors",
                theme === "dark"
                  ? "bg-white/5 hover:bg-blue-500/20 hover:text-blue-400 text-white/60"
                  : "bg-gray-100 hover:bg-blue-50 hover:text-blue-600 text-gray-500"
              )}
            >
              +₹{(amt / 1000).toFixed(0)}K
            </button>
          ))}
        </div>
      )}
    </motion.div>
  );
}

// ─── Main GoalsPage ───────────────────────────────────────────────────────────

export default function GoalsPage({ theme = "dark" }) {
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  const loadGoals = async () => {
    try {
      const res = await apiFetch(`${API_BASE}/goals`);
      setGoals(res.data || []);
    } catch (e) {
      console.error("Failed to load goals:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGoals();
  }, []);

  const handleDelete = async (id) => {
    try {
      await apiFetch(`${API_BASE}/goals/${id}`, { method: "DELETE" });
      setGoals((g) => g.filter((x) => x.id !== id));
    } catch (e) {
      console.error("Failed to delete goal:", e);
    }
  };

  const handleUpdate = async (id, newAmount) => {
    try {
      const res = await apiFetch(`${API_BASE}/goals/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ current_amount: newAmount }),
      });
      setGoals((g) => g.map((x) => (x.id === id ? res.data : x)));
    } catch (e) {
      console.error("Failed to update goal:", e);
    }
  };

  const stats = useMemo(() => {
    const active = goals.filter((g) => !g.is_completed);
    const completed = goals.filter((g) => g.is_completed);
    const totalTarget = active.reduce((s, g) => s + parseFloat(g.target_amount || 0), 0);
    const totalSaved = active.reduce((s, g) => s + parseFloat(g.current_amount || 0), 0);
    return { active: active.length, completed: completed.length, totalTarget, totalSaved };
  }, [goals]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={cn("text-3xl font-black tracking-tighter", theme === "dark" ? "text-white" : "text-gray-900")}>
            Saving Goals
          </h1>
          <p className="text-xs font-bold opacity-40 mt-1 tracking-wide">
            Track progress toward your financial milestones
          </p>
        </div>
        <motion.button
          id="add-goal-btn"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-5 py-3 rounded-2xl bg-blue-600 text-white text-xs font-black uppercase tracking-widest hover:bg-blue-500 transition-colors shadow-lg shadow-blue-500/30"
        >
          <Plus className="w-4 h-4" />
          Add Goal
        </motion.button>
      </div>

      {/* Summary Tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Active Goals", value: stats.active, color: "text-blue-500" },
          { label: "Completed", value: stats.completed, color: "text-emerald-500" },
          { label: "Total Target", value: formatIndianCompact(stats.totalTarget), color: "text-violet-500" },
          { label: "Total Saved", value: formatIndianCompact(stats.totalSaved), color: "text-amber-500" },
        ].map(({ label, value, color }) => (
          <div
            key={label}
            className={cn(
              "p-5 rounded-[2rem] border",
              theme === "dark"
                ? "bg-white/[0.03] border-white/8 backdrop-blur-md"
                : "bg-white border-gray-100 shadow-sm"
            )}
          >
            <p className="text-[10px] font-black uppercase tracking-[0.2em] opacity-40 mb-1">{label}</p>
            <p className={cn("text-2xl font-black tracking-tighter", color)}>{value}</p>
          </div>
        ))}
      </div>

      {/* Goal Cards Grid */}
      {loading ? (
        <div className="text-center py-20 opacity-20">
          <Target className="w-12 h-12 mx-auto mb-3 stroke-[1px]" />
          <p className="text-xs font-black uppercase tracking-widest">Loading Goals…</p>
        </div>
      ) : goals.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-24 opacity-20"
        >
          <Target className="w-16 h-16 mx-auto mb-4 stroke-[1px]" />
          <p className="text-sm font-black uppercase tracking-widest">No Goals Yet</p>
          <p className="text-xs mt-2">Click "Add Goal" to start tracking your savings milestones</p>
        </motion.div>
      ) : (
        <motion.div layout className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          <AnimatePresence>
            {goals.map((goal) => (
              <GoalCard
                key={goal.id}
                goal={goal}
                theme={theme}
                onDelete={handleDelete}
                onUpdate={handleUpdate}
              />
            ))}
          </AnimatePresence>
        </motion.div>
      )}

      {/* Add Goal Modal */}
      <AnimatePresence>
        {showModal && (
          <AddGoalModal
            theme={theme}
            onClose={() => setShowModal(false)}
            onSave={(newGoal) => setGoals((g) => [newGoal, ...g])}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
