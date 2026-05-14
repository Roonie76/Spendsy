import React, { useState, useEffect, useMemo, useCallback, useRef } from "react";
import {
  TABS,
  APP_VERSION,
  TORA_BASE_URL,
} from "@shared/config/constants";
import { cn } from "@shared/utils/cn";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  Sun,
  Moon,
  ArrowDown,
  ArrowUp,
  ChevronLeft,
  Layout as LayoutIcon,
  Settings as SettingsIcon,
} from "lucide-react";
import spendsyLogo from "./assets/spendsy_logo.png";
import { AreaChart, Area, ResponsiveContainer, Tooltip } from "recharts";
import { formatIndianCompact, normalizeDate, formatLocalDate } from "@shared/utils/helpers";
import { Navigation } from "./components/ui/Navigation";
import ErrorBoundary from "./components/ui/ErrorBoundary";
import { Toast, ConfirmationDialog } from "./components/ui/Shared";
import AlertsBell from "./components/ui/AlertsBell";

import WelcomeWizard from "./components/onboarding/WelcomeWizard";
import LoginScreen from "./pages/LoginScreen";
import HomePage from "./pages/HomePage";
import HistoryPage from "./pages/HistoryPage";
import AddPage from "./pages/AddPage";
import WealthPage from "./pages/WealthPage";
import ProfilePage from "./pages/ProfilePage";
import AuditPage from "./pages/AuditPage";
import StatsPage from "./pages/StatsPage";
import ITRPage from "./pages/ITRPage";
import DebitCardsPage from "./pages/DebitCardsPage";
import CreditCardsPage from "./pages/CreditCardsPage";
import SettingsPage from "./pages/SettingsPage";
import BankAccountsPage from "./pages/BankAccountsPage";
import GoalsPage from "./pages/GoalsPage";
import PlannerPage from "./pages/PlannerPage";
import ActiveLoansPage from "./pages/ActiveLoansPage";
import BudgetPage from "./pages/BudgetPage";
import AICopilot from "./components/ai/AICopilot";
import { apiFetch, authApi, clearStoredAuth } from "./api";

export default function App() {
  const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || "http://localhost:8080";
  const API_BASE_URL = import.meta.env.VITE_FINANCE_URL
    ? `${import.meta.env.VITE_FINANCE_URL}`
    : `${GATEWAY_URL}/finance`;
  const AI_BASE_URL = import.meta.env.VITE_AI_URL || `${GATEWAY_URL}/tora`;
  const initialDefaultProfile = useMemo(
    () => ({
      annualRent: 0,
      annualEPF: 0,
      npsContribution: 0,
      healthInsuranceSelf: 0,
      healthInsuranceParents: 0,
      homeLoanInterest: 0,
      educationLoanInterest: 0,
      isBusiness: false,
    }),
    [],
  );

  const [currentUser, setCurrentUser] = useState(() => {
    const saved = localStorage.getItem("auth_user");
    if (!saved) return null;
    try {
      return JSON.parse(saved);
    } catch {
      return null;
    }
  });
  const [activeTab, setActiveTab] = useState(() => {
    return localStorage.getItem("active_tab") || TABS.HOME;
  });
  const [settingsSection, setSettingsSection] = useState(null);

  const navigateToTab = useCallback((tab) => {
    setActiveTab((prev) => {
      if (prev !== tab) {
        window.history.pushState({ tab }, "", "");
      }
      return tab;
    });
  }, []);

  useEffect(() => {
    const handlePopState = (event) => {
      if (event.state?.tab) {
        setActiveTab(event.state.tab);
      }
    };
    window.addEventListener("popstate", handlePopState);
    
    // Set initial state if none exists
    if (!window.history.state) {
      window.history.replaceState({ tab: activeTab }, "", "");
    }
    
    return () => window.removeEventListener("popstate", handlePopState);
  }, [activeTab]);
  const [toast, setToast] = useState({ show: false, msg: "", type: "info" });
  const [theme, setTheme] = useState(
    () => localStorage.getItem("app_theme") || "dark",
  );
  const [showWizard, setShowWizard] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [serverSummary, setServerSummary] = useState(null);
  const [wealthItems, setWealthItems] = useState([]);
  const [netWorthHistory, setNetWorthHistory] = useState([]);
  const [sessionReady, setSessionReady] = useState(() => !currentUser);
  const [settings, setSettings] = useState({
    monthlyBudget: 0,
    monthlyIncome: 0,
  });
  const [taxProfile, setTaxProfile] = useState(() => {
    const saved = localStorage.getItem("tax_profile");
    try {
      return saved ? JSON.parse(saved) : initialDefaultProfile;
    } catch (e) {
      console.error("Failed to parse tax profile:", e);
      return initialDefaultProfile;
    }
  });

  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    message: "",
    action: null,
  });
  const unauthorizedHandledRef = useRef(false);
  const authToken =
    currentUser?.token ||
    localStorage.getItem("access_token") ||
    localStorage.getItem("auth_token") ||
    localStorage.getItem("token");
  // Removed local apiFetch in favor of the centralized one imported from ./api.js


  const localTotals = useMemo(() => {
    if (!Array.isArray(transactions)) return { income: 0, expenses: 0 };
    return transactions.reduce(
      (acc, curr) => {
        const amt = parseFloat(curr.amount || 0);
        if (curr.type === "income") acc.income += amt;
        else if (curr.type === "expense") acc.expenses += amt;
        return acc;
      },
      { income: 0, expenses: 0 },
    );
  }, [transactions]);

  const totals = useMemo(() => {
    // 1. Calculate local monthly totals first
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();

    const localMonthly = transactions.reduce(
      (acc, t) => {
        if (t.is_transfer) return acc;
        const d = normalizeDate(t.date);
        if (!d || d.getMonth() !== currentMonth || d.getFullYear() !== currentYear) return acc;

        const amt = parseFloat(t.amount || 0);
        if (t.type === "income") acc.income += amt;
        else if (t.type === "expense") acc.expenses += amt;
        return acc;
      },
      { income: 0, expenses: 0 },
    );

    return {
      income:
        serverSummary?.income !== undefined
          ? Number(serverSummary.income)
          : localTotals.income,
      expenses:
        serverSummary?.expense !== undefined
          ? Number(serverSummary.expense)
          : localTotals.expenses,
      monthIncome:
        serverSummary?.month_income !== undefined
          ? Number(serverSummary.month_income)
          : localMonthly.income,
      monthExpense:
        serverSummary?.month_expense !== undefined
          ? Number(serverSummary.month_expense)
          : localMonthly.expenses,
    };
  }, [serverSummary, localTotals, transactions]);

  const balance =
    serverSummary?.balance !== undefined
      ? Number(serverSummary.balance)
      : totals.income - totals.expenses;

  // Total-Balance-card range selector.
  // Lifetime uses the authoritative server summary (already excludes
  // transfers). All other ranges are computed client-side from the
  // transactions list so we don't need a backend round-trip per click.
  const BALANCE_RANGES = [
    { id: "1D", label: "1D", days: 1 },
    { id: "1W", label: "1W", days: 7 },
    { id: "1M", label: "1M", days: 30 },
    { id: "3M", label: "3M", days: 90 },
    { id: "6M", label: "6M", days: 180 },
    { id: "1Y", label: "1Y", days: 365 },
    { id: "LIFE", label: "Lifetime", days: null },
  ];
  const [balanceRange, setBalanceRange] = useState("LIFE");

  // Re-fetch summary from backend whenever the hero card's time range changes.
  // This ensures we get full-history aggregates even if only recent transactions are loaded.
  useEffect(() => {
    if (currentUser?.id) {
      fetchSummary(balanceRange);
    }
  }, [balanceRange, currentUser?.id]);


  const rangedTotals = useMemo(() => {
    if (!Array.isArray(transactions)) return { income: 0, expenses: 0 };
    
    const cfg = BALANCE_RANGES.find((r) => r.id === balanceRange);
    const hasRange = cfg && cfg.days !== null;
    
    let cutoff = null;
    if (hasRange) {
      cutoff = new Date();
      cutoff.setHours(0, 0, 0, 0);
      cutoff.setDate(cutoff.getDate() - (cfg.days - 1));
    }

    const res = transactions.reduce(
      (acc, t) => {
        // Solely from transactions: ignore server summary for this calculation.
        // Also exclude transfers as they are not income/expense.
        if (t.is_transfer) return acc;
        
        // Apply date filter if range is selected
        if (cutoff) {
          const d = normalizeDate(t.date);
          if (!d || d < cutoff) return acc;
        }

        const amt = parseFloat(t.amount || 0);
        const type = String(t.type || "").toLowerCase();
        
        if (type === "income" || type === "credit") {
          acc.income += amt;
        } else if (type === "expense" || type === "debit") {
          acc.expenses += amt;
        }
        return acc;
      },
      { income: 0, expenses: 0 },
    );

    // If the server summary matches our current range, it's the source of truth.
    // Otherwise, fallback to the local calculation (limited to the loaded batch).
    return serverSummary?.period === balanceRange
      ? { 
          income: Number(serverSummary.income), 
          expenses: Number(serverSummary.expense) 
        }
      : res;
  }, [balanceRange, transactions, serverSummary]);

  const rangedBalance = rangedTotals.income - rangedTotals.expenses;

  // ── Sparkline data for the balance hero card ──────────────────────────────
  // Builds a small day-by-day net array for the selected range so the
  // balance card can show a mini trend chart.
  const sparklineData = useMemo(() => {
    if (!Array.isArray(transactions) || transactions.length === 0) return [];
    const cfg = BALANCE_RANGES.find((r) => r.id === balanceRange);
    const days = cfg?.days ?? null;

    // Number of buckets to show (cap at 90 for readability)
    const bucketCount = days ? Math.min(days, 90) : 180;
    const unit = days && days <= 31 ? "day" : "month";

    const dataMap = new Map();
    for (let i = bucketCount - 1; i >= 0; i--) {
      const d = new Date();
      d.setHours(0, 0, 0, 0);
      let key, label;
      if (unit === "day") {
        d.setDate(d.getDate() - i);
        key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
        label = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
      } else {
        d.setDate(1);
        d.setMonth(d.getMonth() - i);
        key = `${d.getFullYear()}-${d.getMonth()}`;
        label = d.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
      }
      dataMap.set(key, { name: label, net: 0, income: 0, expense: 0 });
    }

    transactions.forEach((t) => {
      if (t.is_transfer) return;
      const d = normalizeDate(t.date);
      if (!d) return;
      let key;
      if (unit === "day") {
        key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
      } else {
        key = `${d.getFullYear()}-${d.getMonth()}`;
      }
      if (!dataMap.has(key)) return;
      const entry = dataMap.get(key);
      const amt = parseFloat(t.amount || 0);
      const type = String(t.type || "").toLowerCase();
      if (type === "income" || type === "credit") {
        entry.income += amt;
        entry.net += amt;
      } else if (type === "expense" || type === "debit") {
        entry.expense += amt;
        entry.net -= amt;
      }
    });

    return Array.from(dataMap.values());
  }, [balanceRange, transactions]);

  const sparkPositive = rangedBalance >= 0;

  const netWorth = useMemo(
    () =>
      wealthItems.reduce(
        (acc, curr) => {
          const amt = parseFloat(curr.amount || 0);
          if (curr.type === "asset") acc.assets += amt;
          else acc.liabilities += amt;
          return acc;
        },
        { assets: 0, liabilities: 0 },
      ),
    [wealthItems],
  );

  const firstName =
    currentUser?.username?.split(" ")[0] ||
    currentUser?.displayName?.split(" ")[0] ||
    "Guest";
  const userEmail = currentUser?.email || "No email provided";

  const toggleTheme = () => {
    const newTheme = theme === "dark" ? "light" : "dark";
    setTheme(newTheme);
    localStorage.setItem("app_theme", newTheme);
  };

  const showToast = useCallback((msg, type = "info") => {
    setToast({ show: true, msg, type });
    setTimeout(() => setToast((prev) => ({ ...prev, show: false })), 3000);
  }, []);

  useEffect(() => {
    if (currentUser) localStorage.setItem("auth_user", JSON.stringify(currentUser));
    else localStorage.removeItem("auth_user");
  }, [currentUser]);

  useEffect(() => {
    localStorage.setItem("active_tab", activeTab);
  }, [activeTab]);

  const clearClientSession = useCallback(() => {
    setCurrentUser(null);
    setTransactions([]);
    setServerSummary(null);
    setWealthItems([]);
    setNetWorthHistory([]);
    setSettings({
      monthlyBudget: 0,
      monthlyIncome: 0,
    });
    setTaxProfile(initialDefaultProfile);
    setShowWizard(false);
    setActiveTab(TABS.HOME);
    window.history.pushState({ tab: TABS.HOME }, "", "");
    localStorage.removeItem("tax_profile");
    localStorage.removeItem("auth_user");
    localStorage.removeItem("active_tab");
    clearStoredAuth();
  }, [initialDefaultProfile]);

  const handleLogout = () => {
    triggerConfirm("Are you sure you want to sign out?", clearClientSession);
  };

  const handleUnauthorized = useCallback(
    (message = "Session expired. Please sign in again.") => {
      if (unauthorizedHandledRef.current) return;
      unauthorizedHandledRef.current = true;
      clearClientSession();
      showToast(message, "error");
    },
    [clearClientSession, showToast],
  );

  const handleAuthSuccess = useCallback((user) => {
    unauthorizedHandledRef.current = false;
    setCurrentUser(user);
    setActiveTab(TABS.HOME);
    window.history.pushState({ tab: TABS.HOME }, "", "");
    localStorage.setItem("active_tab", TABS.HOME);
  }, []);

  // Fixed: The triggerConfirm function was defined but the confirmModal state (isOpen, message, action) was never utilized.
  // Switching to the state-based approach for a better UI experience.
  const triggerConfirm = (message, onConfirm) => {
    setConfirmModal({
      isOpen: true,
      message,
      action: () => {
        onConfirm();
        setConfirmModal((prev) => ({ ...prev, isOpen: false }));
      },
    });
  };

  // Note: You must also add the <ConfirmationDialog /> component to your JSX return
  // at the same level as <Toast />:

  async function fetchHistory() {
    if (!currentUser?.id) return;
    setHistoryLoading(true);
    try {
      // Paginate through ALL pages using the cursor returned by the backend.
      // Previously only the first page (50 rows) was loaded, which caused
      // client-side filters like 1D/1W to silently miss older transactions.
      const allItems = [];
      let cursor = undefined;
      const PAGE_LIMIT = 200; // max the backend allows per call

      do {
        const qs = new URLSearchParams({ limit: PAGE_LIMIT });
        if (cursor) qs.set("cursor", cursor);
        const data = await apiFetch(`${API_BASE_URL}/transactions?${qs.toString()}`);
        const payload = data?.data || data;
        const page = Array.isArray(payload) ? payload : payload?.data;

        if (!Array.isArray(page)) {
          throw new Error("Unexpected transaction response shape");
        }

        allItems.push(...page);
        cursor = (payload?.next_cursor) ?? null;
      } while (cursor);

      const cleanedData = allItems.map((item) => {
        const normalizedType = String(item.type || "expense").toLowerCase();
        return {
          ...item,
          id: item.id || item.pk,
          title: item.raw_description || item.description || item.title || "Unnamed",
          raw_description: item.raw_description || item.description || item.title || null,
          amount: parseFloat(item.amount || 0),
          type: normalizedType,
          // Keep date as YYYY-MM-DD string — normalizeDate() handles parsing
          date: item.date || null,
        };
      });

      // Newest-first by ID, fallback to date
      cleanedData.sort((a, b) => {
        if (b.id !== a.id) return b.id - a.id;
        return new Date(b.date) - new Date(a.date);
      });

      setTransactions([...cleanedData]);
      return cleanedData;
    } catch (err) {
      if (err.status === 401) {
        handleUnauthorized();
        return [];
      }
      console.error("Fetch Error:", err);
      return [];
    } finally {
      setHistoryLoading(false);
    }
  }

  async function fetchSettings() {
    if (!currentUser?.id) return;
    try {
      const data = await apiFetch(`${API_BASE_URL}/profile/${currentUser.id}`);
      setSettings(data?.data || data);
    } catch (err) {
      if (err.status === 401) {
        handleUnauthorized();
        return;
      }
      console.error("Failed to load settings:", err);
    }
  }

  const fetchSummary = useCallback(async (periodOverride) => {
    if (!currentUser?.id) return;
    const period = periodOverride || balanceRange;
    try {
      const today = formatLocalDate(new Date());
      const data = await apiFetch(`${API_BASE_URL}/summary?period=${period}&today=${today}`);
      setServerSummary(data?.data || null);
    } catch (err) {
      if (err.status === 401) {
        handleUnauthorized();
        return;
      }
      console.error("Failed to load summary:", err);
    }
  }, [API_BASE_URL, currentUser?.id, handleUnauthorized, balanceRange]);

  const fetchWealth = useCallback(async () => {
    if (!currentUser?.id) return;
    try {
      const data = await apiFetch(`${API_BASE_URL}/wealth`);
      setWealthItems(data?.data || data);
    } catch (err) {
      if (err.status === 401) {
        handleUnauthorized();
        return;
      }
      showToast("Could not sync portfolio", "error");
    }
  }, [API_BASE_URL, currentUser?.id, handleUnauthorized, showToast]);

  const fetchNetWorthHistory = useCallback(async () => {
    if (!currentUser?.id) return;
    try {
      const data = await apiFetch(`${API_BASE_URL}/net-worth/history`);
      setNetWorthHistory(data?.data || data);
    } catch (err) {
      if (err.status === 401) {
        handleUnauthorized();
        return;
      }
      console.error("Failed to fetch net worth history:", err);
    }
  }, [API_BASE_URL, currentUser?.id, handleUnauthorized]);

  const fetchTaxProfile = useCallback(async () => {
    if (!currentUser?.id) return;
    try {
      const data = await apiFetch(`${API_BASE_URL}/tax-profile/${currentUser.id}`);
      const payload = data?.data || data;
      setTaxProfile(payload);
      localStorage.setItem("tax_profile", JSON.stringify(payload));
    } catch (e) {
      if (e.status === 401) {
        handleUnauthorized();
        return;
      }
      console.error("Network error during tax profile sync", e);
    }
  }, [API_BASE_URL, currentUser?.id, handleUnauthorized]); // apiFetch is stable from import

  const updateTaxProfile = async (localProfile) => {
    if (!currentUser?.id) {
      showToast("Session expired. Please login again.", "error");
      return;
    }

    try {
      const savedData = await apiFetch(`${API_BASE_URL}/tax-profile/${currentUser.id}`, {
        method: "POST",
        body: JSON.stringify(localProfile),
      });

      const payload = savedData?.data || savedData;
      setTaxProfile(payload);
      localStorage.setItem("tax_profile", JSON.stringify(payload));
      showToast("Profile synced!", "success");
    } catch (error) {
      if (error.status === 401) {
        handleUnauthorized();
        return;
      }
      showToast("Network error", "error");
    }
  };

  useEffect(() => {
    if (currentUser?.id && sessionReady) {
      fetchHistory();
      fetchSettings();
      fetchSummary();
      fetchWealth();
      fetchNetWorthHistory();
      fetchTaxProfile(); // Add this!
    }
  }, [currentUser?.id, fetchWealth, fetchTaxProfile, fetchSummary, sessionReady]); // Add fetchTaxProfile to dependencies

  useEffect(() => {
    if (!currentUser?.id) {
      unauthorizedHandledRef.current = false;
      setSessionReady(true);
      return;
    }

    let isActive = true;
    setSessionReady(false);

    const validateSession = async () => {
      try {
        const data = await authApi.me();
        if (!isActive) return;

        const payload = data?.data || data;
        unauthorizedHandledRef.current = false;
        setCurrentUser((prev) => (
          prev
            ? {
              ...prev,
              id: payload.id ?? prev.id,
              username: payload.username ?? prev.username,
              email: payload.email ?? prev.email,
              created_at: payload.created_at ?? payload.createdAt ?? payload.date_joined ?? prev.created_at,
            }
            : prev
        ));
        setSessionReady(true);
      } catch (err) {
        if (!isActive) return;

        if (err.status === 401) {
          handleUnauthorized();
          setSessionReady(true);
          return;
        }

        console.error("Failed to validate auth session:", err);
        setSessionReady(true);
      }
    };

    validateSession();

    return () => {
      isActive = false;
    };
  }, [currentUser?.id, handleUnauthorized]);

  // Inside your App() function, add this useEffect or update your existing one
  const refreshUser = useCallback(async () => {
    if (!currentUser?.id) return;
    try {
      // Fetch from Finance microservice
      const finData = await financeApi.profile(currentUser.id);
      const finPayload = finData?.data || finData;
      
      // Fetch from Auth microservice
      const authData = await authApi.me();
      const authPayload = authData?.data || authData;

      setCurrentUser((prev) => ({
        ...prev,
        ...finPayload,
        ...authPayload,
        email: authPayload.email || finPayload.email || prev.email,
      }));
    } catch (err) {
      console.error("Refresh user error:", err);
    }
  }, [currentUser?.id]);

  useEffect(() => {
    if (currentUser?.id && sessionReady && !currentUser.email) {
      refreshUser();
    }
  }, [currentUser?.id, sessionReady, refreshUser]);

  const deleteTransaction = async (txId) => {
    try {
      await apiFetch(`${API_BASE_URL}/transactions/${txId}`, {
        method: "DELETE",
      });
      setTransactions((prev) => prev.filter((t) => (t.uid || t.id) !== txId));
      fetchSummary();
    } catch (error) {
      if (error.status === 401) {
        handleUnauthorized();
        return;
      }
      console.error("Delete failed:", error);
      showToast("Delete failed", "error");
    }
  };
  const updateTransaction = async (updatedTx) => {
    try {
      const txId = updatedTx.uid || updatedTx.id;
      await apiFetch(`${API_BASE_URL}/transactions/${txId}`, {
        method: "PUT",
        body: JSON.stringify({
          title: updatedTx.title || updatedTx.description || "Untitled",
          amount: parseFloat(updatedTx.amount || 0),
          type: (updatedTx.type || "expense").toLowerCase(),
          category: (updatedTx.category || "other").toLowerCase(),
          date: updatedTx.date,
          is_recurring: updatedTx.is_recurring,
        }),
      });
      showToast("Transaction updated!", "success");
      fetchHistory();
      fetchSummary();
    } catch (err) {
      if (err.status === 401) {
        handleUnauthorized();
        return;
      }
      showToast(err.message || "Update failed", "error");
    }
  };
  const bulkDeleteTransactions = async (items) => {
    if (!Array.isArray(items) || items.length === 0) return;

    const idsToDelete = items.map((item) => item.id).filter(Boolean);
    try {
      const response = await apiFetch(`${API_BASE_URL}/transactions/bulk`, {
        method: "DELETE",
        body: JSON.stringify({ ids: idsToDelete }),
      });

      if (response?.ok || response?.deleted_count !== undefined) {
        const deletedCount = response.deleted_count ?? idsToDelete.length;
        showToast(`Deleted ${deletedCount} transactions`, "success");
        await fetchHistory();
        await fetchSummary();
      } else {
        throw new Error(response?.message || "Bulk delete failed");
      }
    } catch (error) {
      if (error.status === 401) {
        handleUnauthorized();
        return;
      }
      console.error("Bulk delete failed:", error);
      showToast("Bulk delete failed", "error");
    }
  };

  const requestDeleteTransaction = (id) =>
    triggerConfirm("Permanently delete?", () => deleteTransaction(id));
  const requestBulkDelete = (items) =>
    triggerConfirm(`Delete ${items.length} items?`, () =>
      bulkDeleteTransactions(items),
    );
  const updateWealthItem = async (updatedItem) => {
    try {
      await apiFetch(`${API_BASE_URL}/wealth/${updatedItem.id}`, {
        method: "PUT",
        body: JSON.stringify(updatedItem),
      });
      showToast("Portfolio updated!", "success");
      fetchWealth();
    } catch (err) {
      if (err.status === 401) {
        handleUnauthorized();
        return;
      }
      showToast(err.message || "Update failed", "error");
    }
  };
  const saveSettings = async (dataToSave) => {
    try {
      const data = await apiFetch(`${API_BASE_URL}/profile/${currentUser.id}`, {
        method: "POST",
        body: JSON.stringify(dataToSave),
      });

      const payload = data?.data || data;
      setSettings(payload);
      showToast("Settings saved!", "success");
      return true;
    } catch (err) {
      if (err.status === 401) {
        handleUnauthorized();
        return false;
      }
      console.error("Save Error:", err);
      showToast(err.message || "Update failed", "error");
      return false;
    }
  };

  const executeDeleteWealth = async (itemId) => {
    try {
      await apiFetch(`${API_BASE_URL}/wealth/${itemId}`, {
        method: "DELETE",
      });
      showToast("Item removed", "success");
      fetchWealth();
    } catch (e) {
      if (e.status === 401) {
        handleUnauthorized();
        return;
      }
      showToast(e.message || "Failed to remove", "error");
    }
  };

  const handleWizardComplete = async (wizardData) => {
    const success = await saveSettings(wizardData);
    if (success) setShowWizard(false);
  };

  if (!currentUser) {
    return <LoginScreen onAuthSuccess={handleAuthSuccess} showToast={showToast} />;
  }
  return (
    <ErrorBoundary>
      <div
      className={cn(
        "min-h-screen transition-colors duration-1000 font-sans pb-28 md:pb-0 md:pl-28",
        theme === "dark"
          ? "bg-[#08090a] text-white"
          : "bg-[#cfd9e5] text-slate-900",
      )}
    >
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,#3b82f6,transparent_75%)] opacity-10 blur-[120px]" />
      </div>

      <Toast
        message={toast.msg}
        type={toast.type}
        isVisible={toast.show}
        onClose={() => setToast((p) => ({ ...p, show: false }))}
      />
      <Navigation
        activeTab={activeTab}
        setActiveTab={navigateToTab}
        onSignOut={() => triggerConfirm("Are you sure you want to sign out?", clearClientSession)}
      />
      <WelcomeWizard isOpen={showWizard} onComplete={handleWizardComplete} />
      <ConfirmationDialog
        isOpen={confirmModal.isOpen}
        message={confirmModal.message}
        onConfirm={confirmModal.action}
        onCancel={() => setConfirmModal((p) => ({ ...p, isOpen: false }))}
      />
      <div className="mx-auto min-h-screen relative z-10 max-w-6xl px-4 sm:px-6 md:px-8 xl:px-12 flex flex-col">
        <header className="pt-6 md:pt-10 mb-6 md:mb-8 flex justify-between items-center md:items-end gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-blue-500 fill-blue-500" />
              <span className="text-[10px] font-bold tracking-[0.3em] uppercase opacity-60">
                Spendsy
              </span>
            </div>
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-black truncate">Hello, {firstName}</h1>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <AlertsBell theme={theme} />
          </div>
        </header>

        {[TABS.HOME, TABS.ADD, TABS.STATS, TABS.WEALTH, TABS.PLANNER].includes(activeTab) && (
          <motion.div
            whileHover={{ scale: 1.01, y: -2 }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            className={cn(
              "relative overflow-hidden rounded-[2rem] md:rounded-[2.5rem] p-6 sm:p-8 md:p-10 mb-6 md:mb-10 border transition-all duration-500",
              theme === "dark"
                ? "bg-gradient-to-br from-white/[0.08] to-white/[0.02] border-white/10 shadow-xl"
                : "bg-gradient-to-br from-white to-slate-50 border-white/60 shadow-xl",
            )}
          >
            <div className="relative z-10">
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-4">
                <div className="flex items-center gap-2 opacity-50">
                  <LayoutIcon className="w-4 h-4" />
                  <p className="text-xs font-bold uppercase tracking-widest">
                    {activeTab === TABS.WEALTH
                      ? "Net Valuation"
                      : "Total Balance"}
                  </p>
                </div>

                {activeTab !== TABS.WEALTH && (
                  <div
                    className={cn(
                      "flex flex-wrap justify-start sm:justify-end gap-1 p-1 rounded-full border -mx-1 sm:mx-0",
                      theme === "dark"
                        ? "bg-white/5 border-white/10"
                        : "bg-slate-100 border-slate-200",
                    )}
                  >
                    {BALANCE_RANGES.map((r) => (
                      <button
                        key={r.id}
                        onClick={() => setBalanceRange(r.id)}
                        className={cn(
                          "text-[10px] font-bold uppercase tracking-widest px-2 sm:px-2.5 py-1 rounded-full transition-colors",
                          balanceRange === r.id
                            ? "bg-blue-600 text-white"
                            : theme === "dark"
                              ? "text-white/60 hover:text-white hover:bg-white/5"
                              : "text-slate-500 hover:text-slate-800 hover:bg-white",
                        )}
                      >
                        {r.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <h2
                className={cn(
                  "font-black mb-3 tracking-tighter text-4xl sm:text-5xl md:text-6xl xl:text-7xl leading-tight break-all",
                  theme === "dark" ? "text-white" : "text-slate-900",
                )}
              >
                {activeTab === TABS.WEALTH
                  ? formatIndianCompact(netWorth.assets - netWorth.liabilities)
                  : `₹${(balanceRange === "LIFE" && rangedBalance < 0 ? 0 : rangedBalance).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}
              </h2>

              {/* ── Sparkline trend chart ──────────────────────────────────── */}
              {activeTab !== TABS.WEALTH && sparklineData.length > 1 && (
                <div className="mb-6 md:mb-8 -mx-1">
                  <ResponsiveContainer width="100%" height={64}>
                    <AreaChart data={sparklineData} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={sparkPositive ? "#10b981" : "#f43f5e"} stopOpacity={0.35} />
                          <stop offset="95%" stopColor={sparkPositive ? "#10b981" : "#f43f5e"} stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <Tooltip
                        contentStyle={{
                          background: theme === "dark" ? "#1e293b" : "#fff",
                          border: "1px solid rgba(255,255,255,0.1)",
                          borderRadius: "0.75rem",
                          fontSize: "11px",
                          color: theme === "dark" ? "#e2e8f0" : "#0f172a",
                          padding: "6px 10px",
                        }}
                        formatter={(v) => [`₹${Math.abs(v).toLocaleString("en-IN")}`, v >= 0 ? "Net in" : "Net out"]}
                        labelFormatter={(l) => l}
                        cursor={{ stroke: "rgba(255,255,255,0.15)", strokeWidth: 1 }}
                      />
                      <Area
                        type="monotone"
                        dataKey="net"
                        stroke={sparkPositive ? "#10b981" : "#f43f5e"}
                        strokeWidth={2}
                        fill="url(#sparkGrad)"
                        dot={false}
                        activeDot={{ r: 3, strokeWidth: 0 }}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3 sm:gap-6">
                <div className="p-4 sm:p-5 rounded-2xl sm:rounded-3xl bg-emerald-500/10 border border-emerald-500/20">
                  <div className="flex items-center gap-2 mb-2 text-emerald-500">
                    <ArrowDown className="w-4 h-4" />
                    <span className="text-xs font-bold uppercase">
                      {activeTab === TABS.WEALTH ? "Assets" : "Income"}
                    </span>
                  </div>
                  <p className="text-lg sm:text-xl md:text-2xl font-bold break-all">
                    {activeTab === TABS.WEALTH
                      ? formatIndianCompact(netWorth.assets)
                      : `₹${rangedTotals.income.toLocaleString("en-IN")}`}
                  </p>
                </div>

                <div className="p-4 sm:p-5 rounded-2xl sm:rounded-3xl bg-rose-500/10 border border-rose-500/20">
                  <div className="flex items-center gap-2 mb-2 text-rose-500">
                    <ArrowUp className="w-4 h-4" />
                    <span className="text-xs font-bold uppercase">
                      {activeTab === TABS.WEALTH ? "Liabilities" : "Expense"}
                    </span>
                  </div>
                  <p className="text-lg sm:text-xl md:text-2xl font-bold break-all">
                    {activeTab === TABS.WEALTH
                      ? formatIndianCompact(netWorth.liabilities)
                      : `₹${rangedTotals.expenses.toLocaleString("en-IN")}`}
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        <main className="flex-1">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.2 }}
            >
              {activeTab === TABS.HOME && (
                <HomePage
                  transactions={transactions}
                  wealthItems={wealthItems}
                  setActiveTab={navigateToTab}
                  onDelete={requestDeleteTransaction}
                  onUpdate={updateTransaction}
                  settings={settings}
                  totals={totals}
                  theme={theme}
                  taxProfile={taxProfile}
                  netWorthHistory={netWorthHistory}
                />
              )}
              {activeTab === TABS.HISTORY && (
                <HistoryPage
                  transactions={transactions}
                  isLoading={historyLoading}
                  setActiveTab={navigateToTab}
                  onDelete={requestDeleteTransaction}
                  onBulkDelete={bulkDeleteTransactions}
                  onUpdate={updateTransaction}
                  apiBaseUrl={API_BASE_URL}
                  onRefresh={fetchHistory}
                  showToast={showToast}
                />
              )}
              {activeTab === TABS.ADD && (
                <AddPage
                  user={currentUser}
                  authToken={authToken}
                  apiBaseUrl={API_BASE_URL}
                  appId={settings?.appId}
                  setActiveTab={navigateToTab}
                  showToast={showToast}
                  triggerConfirm={triggerConfirm}
                  theme={theme}
                  refreshData={async () => {
                    await Promise.all([
                      fetchHistory(), // Refresh data
                      fetchSummary(), // Refresh fast financial totals
                    ]);
                  }}
                />
              )}
                            {activeTab === TABS.SETTINGS && (
                <SettingsPage
                  user={currentUser}
                  settings={settings}
                  onUpdateSettings={saveSettings}
                  showToast={showToast}
                  theme={theme}
                  onBack={() => navigateToTab(TABS.HOME)}
                  triggerConfirm={triggerConfirm}
                  initialSection={settingsSection}
                  onClearSection={() => setSettingsSection(null)}
                  transactions={transactions}
                  onRefreshUser={refreshUser}
                  isLoading={historyLoading}
                />
              )}
              {activeTab === TABS.PROFILE && (
                <ProfilePage
                  user={currentUser}
                  transactions={transactions}
                  settings={settings}
                  wealthItems={wealthItems}
                  showToast={showToast}
                  apiBaseUrl={API_BASE_URL}
                  authToken={authToken}
                  onLogout={handleLogout}
                  setActiveTab={navigateToTab}
                  onUpdateSettings={saveSettings}
                  openSettingsSection={(section) => {
                    setSettingsSection(section);
                    navigateToTab(TABS.SETTINGS);
                  }}
                  isLoading={historyLoading}
                />
              )}
              {activeTab === TABS.DEBIT_CARDS && (
                <DebitCardsPage
                  user={currentUser}
                  authToken={authToken}
                  apiBaseUrl={API_BASE_URL}
                  transactions={transactions}
                />
              )}
              {activeTab === TABS.CREDIT_CARDS && (
                <CreditCardsPage
                  user={currentUser}
                  authToken={authToken}
                  apiBaseUrl={API_BASE_URL}
                  transactions={transactions}
                />
              )}
              {activeTab === TABS.WEALTH && (
                <WealthPage
                  wealthItems={wealthItems}
                  netWorthHistory={netWorthHistory}
                  user={currentUser}
                  authToken={authToken}
                  apiBaseUrl={API_BASE_URL}
                  appId={settings?.appId}
                  onSuccess={async () => {
                    await Promise.all([
                      fetchWealth(),
                      fetchNetWorthHistory(),
                      fetchSummary(),
                    ]);
                  }}
                  showToast={showToast}
                  triggerConfirm={triggerConfirm}
                  isLoading={historyLoading}
                />
              )}
              {activeTab === TABS.PLANNER && (
                <PlannerPage
                  user={currentUser}
                  authToken={authToken}
                  apiBaseUrl={API_BASE_URL}
                  theme={theme}
                  showToast={showToast}
                />
              )}
              {activeTab === TABS.AUDIT && (
                <AuditPage
                  transactions={transactions}
                  wealthItems={wealthItems}
                  taxProfile={taxProfile}
                  onUpdateProfile={updateTaxProfile}
                  showToast={showToast}
                  settings={settings}
                  setActiveTab={navigateToTab}
                  refreshProfile={fetchTaxProfile}
                  user={currentUser}
                  apiBaseUrl={API_BASE_URL}
                  isLoading={historyLoading}
                />
              )}

              {activeTab === TABS.STATS && (
                <StatsPage transactions={transactions} netWorthHistory={netWorthHistory} wealthItems={wealthItems} showToast={showToast} isLoading={historyLoading} />
              )}

              {activeTab === TABS.ITR && (
                <ITRPage
                  user={currentUser}
                  authToken={authToken}
                  apiBaseUrl={API_BASE_URL}
                  transactions={transactions}
                  setActiveTab={navigateToTab}
                  showToast={showToast}
                  refreshProfile={fetchTaxProfile}
                  isLoading={historyLoading}
                />
              )}
            </motion.div>
          </AnimatePresence>
        </main>

        <footer className="py-10 text-center opacity-40 text-xs font-mono tracking-widest uppercase">
          {APP_VERSION} • &copy; {new Date().getFullYear()} Spendsy
        </footer>
      </div>
      <AICopilot
        authToken={authToken}
        aiBaseUrl={AI_BASE_URL}
        userId={currentUser?.id}
      />

    </div>
    </ErrorBoundary>
  );
}
