/**
 * AlertsBell — header bell icon with an unread count badge plus a
 * lightweight popover showing the most recent alerts and a per-row
 * "mark read" action.
 *
 * Data flow:
 *   - polls /product/alerts?unread_only=true every 60s while mounted
 *   - refreshes immediately when the popover is opened
 *   - optimistically updates the unread count on mark-as-read
 *
 * Intentionally dependency-free beyond lucide icons + the shared
 * cn helper. Keep this cheap — it sits in the header on every page.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Bell, X, TrendingUp, ShoppingBag, AlertTriangle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@shared/utils/cn";
import { alertsApi } from "../../api";

const POLL_INTERVAL_MS = 60_000;

const SEVERITY_STYLES = {
  info: "bg-blue-500/10 border-blue-500/20 text-blue-200",
  warning: "bg-amber-500/10 border-amber-500/20 text-amber-200",
  danger: "bg-rose-500/10 border-rose-500/20 text-rose-200",
};

const TYPE_ICON = {
  spike: TrendingUp,
  large_transaction: AlertTriangle,
  unusual_merchant: ShoppingBag,
};

function timeAgo(iso) {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const mins = Math.max(1, Math.floor((Date.now() - then) / 60_000));
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export default function AlertsBell({ theme = "dark", className }) {
  const [alerts, setAlerts] = useState([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const popoverRef = useRef(null);
  const buttonRef = useRef(null);

  const unreadCount = alerts.length;

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await alertsApi.list({ unreadOnly: true });
      const payload = data?.data ?? data;
      setAlerts(Array.isArray(payload) ? payload : []);
    } catch (err) {
      // Silent fail — bell just shows "0" if the service is down.
      if (err?.status !== 401) {
        console.warn("AlertsBell: refresh failed", err);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load + polling.
  useEffect(() => {
    refresh();
    const id = setInterval(refresh, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  // Refresh on open so the user sees the latest state immediately.
  useEffect(() => {
    if (open) refresh();
  }, [open, refresh]);

  // Close on outside click / Esc.
  useEffect(() => {
    if (!open) return;
    const onDown = (e) => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target) &&
        buttonRef.current &&
        !buttonRef.current.contains(e.target)
      ) {
        setOpen(false);
      }
    };
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const markRead = async (alertId) => {
    // Optimistic update.
    setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    try {
      await alertsApi.markRead(alertId);
    } catch (err) {
      // Revert on failure.
      console.warn("AlertsBell: mark-read failed", err);
      refresh();
    }
  };

  return (
    <div className={cn("relative", className)}>
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={`Alerts (${unreadCount} unread)`}
        className={cn(
          "relative p-3 rounded-full border transition",
          theme === "dark"
            ? "bg-white/5 border-white/10 hover:bg-white/10"
            : "bg-white border-slate-200 hover:bg-slate-50"
        )}
      >
        <Bell
          className={cn(
            "w-5 h-5",
            theme === "dark" ? "text-white/80" : "text-slate-700"
          )}
        />
        {unreadCount > 0 && (
          <span
            className={cn(
              "absolute -top-1 -right-1 min-w-[20px] h-5 px-1 rounded-full text-[10px] font-bold flex items-center justify-center",
              "bg-rose-500 text-white shadow-lg ring-2",
              theme === "dark" ? "ring-[#08090a]" : "ring-[#cfd9e5]"
            )}
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            ref={popoverRef}
            initial={{ opacity: 0, y: -8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className={cn(
              "absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto rounded-2xl border shadow-2xl z-50",
              theme === "dark"
                ? "bg-[#0f1012] border-white/10"
                : "bg-white border-slate-200"
            )}
          >
            <div
              className={cn(
                "px-4 py-3 border-b flex items-center justify-between",
                theme === "dark" ? "border-white/10" : "border-slate-200"
              )}
            >
              <div className="flex items-baseline gap-2">
                <h3
                  className={cn(
                    "text-sm font-bold",
                    theme === "dark" ? "text-white" : "text-slate-900"
                  )}
                >
                  Insights
                </h3>
                <span className="text-xs opacity-50">
                  {unreadCount > 0 ? `${unreadCount} new` : "all caught up"}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="p-1 rounded hover:bg-white/5"
                aria-label="Close"
              >
                <X className="w-4 h-4 opacity-60" />
              </button>
            </div>

            {loading && alerts.length === 0 && (
              <p className="px-4 py-6 text-sm text-center opacity-50">Loading…</p>
            )}
            {!loading && alerts.length === 0 && (
              <div className="px-4 py-8 text-center">
                <p className="text-sm opacity-70">Nothing new since yesterday.</p>
                <p className="text-xs opacity-40 mt-1">
                  TORA checks your finances nightly and flags anything unusual.
                </p>
              </div>
            )}
            <ul className="divide-y divide-white/5">
              {alerts.map((a) => {
                const Icon = TYPE_ICON[a.alert_type] || Bell;
                const stylePill =
                  SEVERITY_STYLES[a.severity] || SEVERITY_STYLES.info;
                return (
                  <li
                    key={a.id}
                    className="px-4 py-3 hover:bg-white/5 transition"
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={cn(
                          "flex-shrink-0 w-9 h-9 rounded-xl border flex items-center justify-center",
                          stylePill
                        )}
                      >
                        <Icon className="w-4 h-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p
                          className={cn(
                            "text-sm font-semibold truncate",
                            theme === "dark" ? "text-white" : "text-slate-900"
                          )}
                        >
                          {a.title}
                        </p>
                        {a.description && (
                          <p
                            className={cn(
                              "text-xs mt-1 leading-snug",
                              theme === "dark" ? "text-white/60" : "text-slate-600"
                            )}
                          >
                            {a.description}
                          </p>
                        )}
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-[10px] uppercase tracking-wide opacity-40">
                            {timeAgo(a.created_at)}
                          </span>
                          <button
                            type="button"
                            onClick={() => markRead(a.id)}
                            className="text-[11px] opacity-60 hover:opacity-100 transition"
                          >
                            Mark read
                          </button>
                        </div>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
