import React, { useState, useEffect, useMemo, useCallback, useRef } from "react";
import {
  TABS,
  APP_VERSION,
} from "@shared/config/constants";
import { cn } from "@shared/utils/cn";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  Sun,
  Moon,
  ArrowDown,
  ArrowUp,
  Layout as LayoutIcon,
} from "lucide-react";
import { formatIndianCompact } from "@shared/utils/helpers";
import { Navigation } from "./components/ui/Navigation";
import { Toast, ConfirmationDialog } from "./components/ui/Shared";

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
  const AI_BASE_URL = import.meta.env.VITE_AI_URL || `${GATEWAY_URL}/ai`;
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
  const [toast, setToast] = useState({ show: false, msg: "", type: "info" });
  const [theme, setTheme] = useState(
    () => localStorage.getItem("app_theme") || "dark",
  );
  const [showWizard, setShowWizard] = useState(false);
  const [transactions, setTransactions] = useState([]);
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

  const totals = useMemo(
    () => ({
      income:
        serverSummary?.income !== undefined
          ? Number(serverSummary.income)
          : localTotals.income,
      expenses:
        serverSummary?.expense !== undefined
          ? Number(serverSummary.expense)
          : localTotals.expenses,
    }),
    [serverSummary, localTotals],
  );

  const balance =
    serverSummary?.balance !== undefined
      ? Number(serverSummary.balance)
      : totals.income - totals.expenses;
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
    localStorage.removeItem("tax_profile");
    localStorage.removeItem("auth_user");
    clearStoredAuth();
  }, [initialDefaultProfile]);

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
    try {
      const data = await apiFetch(`${API_BASE_URL}/transactions`);
      const payload = data?.data || data;
      const items = Array.isArray(payload) ? payload : payload?.data;

      if (!Array.isArray(items)) {
        throw new Error("Unexpected transaction response shape");
      }

      const cleanedData = items.map((item) => {
        const normalizedType = String(item.type || "expense").toLowerCase();

        return {
          ...item,
          // Use item.id from Django or fallback to item.pk
          id: item.id || item.pk,
          title: item.raw_description || item.description || item.title || "Unnamed",
          raw_description: item.raw_description || item.description || item.title || null,
          amount: parseFloat(item.amount || 0),
          type: normalizedType,
          date: item.date || new Date().toISOString(),
        };
      });

      // SORTING LOGIC: Descending order of entry (ID)
      // If IDs are equal or missing, it falls back to Date
      cleanedData.sort((a, b) => {
        if (b.id !== a.id) {
          return b.id - a.id;
        }
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

  const fetchSummary = useCallback(async () => {
    if (!currentUser?.id) return;
    try {
      const data = await apiFetch(`${API_BASE_URL}/summary`);
      setServerSummary(data?.data || null);
    } catch (err) {
      if (err.status === 401) {
        handleUnauthorized();
        return;
      }
      console.error("Failed to load summary:", err);
    }
  }, [API_BASE_URL, currentUser?.id, handleUnauthorized]);

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
  useEffect(() => {
    if (currentUser?.id && sessionReady && !currentUser.email) {
      // If we have an ID but no email, fetch the full profile from Django
      const fetchFullProfile = async () => {
        try {
          const data = await apiFetch(`${API_BASE_URL}/profile/${currentUser.id}`);
          const payload = data?.data || data;
          setCurrentUser((prev) => ({
            ...prev,
            email: payload.email || payload.user_email,
          }));
        } catch (err) {
          if (err.status === 401) {
            handleUnauthorized();
            return;
          }
          console.error("Could not fetch full user profile:", err);
        }
      };
      fetchFullProfile();
    }
  }, [API_BASE_URL, currentUser?.email, currentUser?.id, handleUnauthorized, sessionReady]);

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
        setActiveTab={setActiveTab}
        onSignOut={() => triggerConfirm("Are you sure you want to sign out?", clearClientSession)}
      />
      <WelcomeWizard isOpen={showWizard} onComplete={handleWizardComplete} />
      <ConfirmationDialog
        isOpen={confirmModal.isOpen}
        message={confirmModal.message}
        onConfirm={confirmModal.action}
        onCancel={() => setConfirmModal((p) => ({ ...p, isOpen: false }))}
      />
      <div className="mx-auto min-h-screen relative z-10 max-w-6xl px-12 flex flex-col">
        <header className="pt-10 mb-8 flex justify-between items-end">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-blue-500 fill-blue-500" />
              <span className="text-[10px] font-bold tracking-[0.3em] uppercase opacity-60">
                Spendsy
              </span>
            </div>
            <h1 className="text-5xl font-black">Hello, {firstName}</h1>
          </div>
          {/* <div className="flex gap-3">
            <button
              onClick={toggleTheme}
              className="p-4 rounded-full bg-white/5 border border-white/10"
            >
              {theme === "dark" ? (
                <Sun className="w-5 h-5 text-amber-400" />
              ) : (
                <Moon className="w-5 h-5 text-blue-600" />
              )}
            </button>
          </div> */}
        </header>

        {[TABS.HOME, TABS.ADD, TABS.STATS, TABS.WEALTH, TABS.PLANNER].includes(activeTab) && (
          <motion.div
            whileHover={{ scale: 1.01, y: -2 }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            className={cn(
              "relative overflow-hidden rounded-[2.5rem] p-10 mb-10 border transition-all duration-500",
              theme === "dark"
                ? "bg-gradient-to-br from-white/[0.08] to-white/[0.02] border-white/10 shadow-xl"
                : "bg-gradient-to-br from-white to-slate-50 border-white/60 shadow-xl",
            )}
          >
            <div className="relative z-10">
              <div className="flex items-center gap-2 mb-4 opacity-50">
                <LayoutIcon className="w-4 h-4" />
                <p className="text-xs font-bold uppercase tracking-widest">
                  {activeTab === TABS.WEALTH
                    ? "Net Valuation"
                    : "Total Balance"}
                </p>
              </div>

              <h2
                className={cn(
                  "font-black mb-10 tracking-tighter text-7xl leading-tight",
                  theme === "dark" ? "text-white" : "text-slate-900",
                )}
              >
                {activeTab === TABS.WEALTH
                  ? formatIndianCompact(netWorth.assets - netWorth.liabilities)
                  : `₹${balance.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}
              </h2>

              <div className="grid grid-cols-2 gap-6">
                <div className="p-5 rounded-3xl bg-emerald-500/10 border border-emerald-500/20">
                  <div className="flex items-center gap-2 mb-2 text-emerald-500">
                    <ArrowDown className="w-4 h-4" />
                    <span className="text-xs font-bold uppercase">
                      {activeTab === TABS.WEALTH ? "Assets" : "Income"}
                    </span>
                  </div>
                  <p className="text-2xl font-bold">
                    {activeTab === TABS.WEALTH
                      ? formatIndianCompact(netWorth.assets)
                      : `₹${totals.income.toLocaleString("en-IN")}`}
                  </p>
                </div>

                <div className="p-5 rounded-3xl bg-rose-500/10 border border-rose-500/20">
                  <div className="flex items-center gap-2 mb-2 text-rose-500">
                    <ArrowUp className="w-4 h-4" />
                    <span className="text-xs font-bold uppercase">
                      {activeTab === TABS.WEALTH ? "Liabilities" : "Expense"}
                    </span>
                  </div>
                  <p className="text-2xl font-bold">
                    {activeTab === TABS.WEALTH
                      ? formatIndianCompact(netWorth.liabilities)
                      : `₹${totals.expenses.toLocaleString("en-IN")}`}
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
                  setActiveTab={setActiveTab}
                  onDelete={requestDeleteTransaction}
                  onUpdate={updateTransaction}
                  settings={settings}
                  theme={theme}
                />
              )}
              {activeTab === TABS.HISTORY && (
                <HistoryPage
                  transactions={transactions}
                  setActiveTab={setActiveTab}
                  onDelete={requestDeleteTransaction}
                  onBulkDelete={requestBulkDelete}
                  onUpdate={updateTransaction}
                />
              )}
              {activeTab === TABS.ADD && (
                <AddPage
                  user={currentUser}
                  authToken={authToken}
                  apiBaseUrl={API_BASE_URL}
                  appId={settings?.appId}
                  setActiveTab={setActiveTab}
                  showToast={showToast}
                  triggerConfirm={triggerConfirm}
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
                  onBack={() => setActiveTab(TABS.PROFILE)}
                  onSignOut={() => triggerConfirm("Are you sure you want to sign out?", clearClientSession)}
                  triggerConfirm={triggerConfirm}
                  theme={theme}
                  onThemeChange={(newTheme) => {
                    setTheme(newTheme);
                    localStorage.setItem("app_theme", newTheme);
                  }}
                  transactions={transactions}
                  onDeleteAll={() => bulkDeleteTransactions(transactions)}
                  showToast={showToast}
                  onNavigateImport={() => setActiveTab(TABS.ADD)}
                />
              )}
              {activeTab === TABS.GOALS && (
                <GoalsPage theme={theme} />
              )}
              {activeTab === TABS.BANK_ACCOUNTS && (
                <BankAccountsPage
                  setActiveTab={setActiveTab}
                  onBack={() => setActiveTab(TABS.PROFILE)}
                />
              )}
              {activeTab === TABS.PROFILE && (
                <ProfilePage
                  user={currentUser}
                  wealthItems={wealthItems}
                  transactions={transactions}
                  settings={settings}
                  onUpdateSettings={saveSettings}
                  onSignOut={clearClientSession}
                  triggerConfirm={triggerConfirm}
                  setActiveTab={setActiveTab}
                />
              )}
              {activeTab === TABS.LOANS && (
                <ActiveLoansPage
                  wealthItems={wealthItems}
                  onBack={() => setActiveTab(TABS.PROFILE)}
                />
              )}
              {activeTab === TABS.BUDGET && (
                <BudgetPage
                  settings={settings}
                  onUpdateSettings={saveSettings}
                  triggerConfirm={triggerConfirm}
                  onBack={() => setActiveTab(TABS.PROFILE)}
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
                />
              )}
              {activeTab === TABS.PLANNER && (
                <PlannerPage
                  user={currentUser}
                  authToken={authToken}
                  apiBaseUrl={API_BASE_URL}
                  theme={theme}
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
                  setActiveTab={setActiveTab}
                  refreshProfile={fetchTaxProfile}
                  user={currentUser}
                  apiBaseUrl={API_BASE_URL}
                />
              )}

              {activeTab === TABS.STATS && (
                <StatsPage transactions={transactions} netWorthHistory={netWorthHistory} wealthItems={wealthItems} />
              )}

              {activeTab === TABS.ITR && (
                <ITRPage
                  user={currentUser}
                  authToken={authToken}
                  apiBaseUrl={API_BASE_URL} // Pass the base URL here
                  transactions={transactions}
                  setActiveTab={setActiveTab}
                  showToast={showToast}
                  refreshProfile={fetchTaxProfile}
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
  );
}

