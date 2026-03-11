import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  TABS,
  APP_VERSION,
} from "../../../../packages/shared/config/constants";
import { cn } from "../../../../packages/shared/utils/cn";
import { motion, AnimatePresence } from "framer-motion";
import {
  Zap,
  Sun,
  Moon,
  ArrowDown,
  ArrowUp,
  Pin,
  PinOff,
  Layout as LayoutIcon,
} from "lucide-react";
import { formatIndianCompact, buildAuthHeader } from "../../../../packages/shared/utils/helpers";
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
import AICopilot from "./components/ai/AICopilot";

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
  const [activeTab, setActiveTab] = useState(TABS.HOME);
  const [toast, setToast] = useState({ show: false, msg: "", type: "info" });
  const [theme, setTheme] = useState(
    () => localStorage.getItem("app_theme") || "dark",
  );
  const [showWizard, setShowWizard] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const [serverSummary, setServerSummary] = useState(null);
  const [wealthItems, setWealthItems] = useState([]);
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
  const authToken =
    currentUser?.token ||
    localStorage.getItem("access_token") ||
    localStorage.getItem("auth_token") ||
    localStorage.getItem("token");
  const apiFetch = useCallback(
    (url, options = {}) => {
      const headers = { ...(options.headers || {}) };
      const authHeader = buildAuthHeader(authToken);
      if (authHeader) {
        headers.Authorization = authHeader;
      }
      return fetch(url, { ...options, headers });
    },
    [authToken],
  );

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
      const response = await apiFetch(`${API_BASE_URL}/transactions`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.message || "Failed to fetch transactions");
      }

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

      console.log("Sorted Data (Newest Entry First):", cleanedData);
      setTransactions([...cleanedData]);
      return cleanedData;
    } catch (err) {
      console.error("Fetch Error:", err);
      throw err;
    }
  }

  async function fetchSettings() {
    if (!currentUser?.id) return;
    try {
      const response = await apiFetch(`${API_BASE_URL}/profile/${currentUser.id}`);
      const data = await response.json();
      if (response.ok) setSettings(data?.data || data);
    } catch (err) {
      console.error("Failed to load settings:", err);
    }
  }

  const fetchSummary = useCallback(async () => {
    if (!currentUser?.id) return;
    try {
      const response = await apiFetch(`${API_BASE_URL}/summary`);
      const data = await response.json();
      if (response.ok) setServerSummary(data?.data || null);
    } catch (err) {
      console.error("Failed to load summary:", err);
    }
  }, [currentUser?.id, apiFetch]);

  const fetchWealth = useCallback(async () => {
    if (!currentUser?.id) return;
    try {
      const response = await apiFetch(`${API_BASE_URL}/wealth`);
      if (response.ok) {
        const data = await response.json();
        setWealthItems(data?.data || data);
      }
    } catch (err) {
      showToast("Could not sync portfolio", "error");
    }
  }, [currentUser?.id, showToast]);

  const fetchTaxProfile = useCallback(async () => {
    if (!currentUser?.id) return;
    try {
      // Ensure this matches your Django urls.py exactly
      const response = await apiFetch(`${API_BASE_URL}/tax-profile/${currentUser.id}`);

      if (response.ok) {
        const data = await response.json();
        // If Django returns a single object, but your state expects initialDefaultProfile keys:
        const payload = data?.data || data;
        setTaxProfile(payload);
        localStorage.setItem("tax_profile", JSON.stringify(payload));
      }
    } catch (e) {
      console.error("Network error during tax profile sync", e);
    }
  }, [currentUser?.id, apiFetch]);

  const updateTaxProfile = async (localProfile) => {
    if (!currentUser?.id) {
      showToast("Session expired. Please login again.", "error");
      return;
    }

    try {
      const response = await apiFetch(`${API_BASE_URL}/tax-profile/${currentUser.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(localProfile),
      });

      if (response.ok) {
        const savedData = await response.json();
        const payload = savedData?.data || savedData;
        setTaxProfile(payload);
        localStorage.setItem("tax_profile", JSON.stringify(payload));
        showToast("Profile synced!", "success");
      }
    } catch (error) {
      showToast("Network error", "error");
    }
  };

  useEffect(() => {
    if (currentUser?.id) {
      fetchHistory();
      fetchSettings();
      fetchSummary();
      fetchWealth();
      fetchTaxProfile(); // Add this!
    }
  }, [currentUser?.id, fetchWealth, fetchTaxProfile, fetchSummary]); // Add fetchTaxProfile to dependencies

  // Inside your App() function, add this useEffect or update your existing one
  useEffect(() => {
    if (currentUser?.id && !currentUser.email) {
      // If we have an ID but no email, fetch the full profile from Django
      const fetchFullProfile = async () => {
        try {
          const response = await apiFetch(`${API_BASE_URL}/profile/${currentUser.id}`);
          const data = await response.json();
          const payload = data?.data || data;
          if (response.ok) {
            // Merge the existing user data with the new email/details from Django
            setCurrentUser((prev) => ({
              ...prev,
              email: payload.email || payload.user_email, // Match your Django field name
            }));
          }
        } catch (err) {
          console.error("Could not fetch full user profile:", err);
        }
      };
      fetchFullProfile();
    }
  }, [currentUser?.id]);

  const deleteTransaction = async (id) => {
    try {
      // Use the constant!
      const response = await apiFetch(`${API_BASE_URL}/transactions/${id}`, {
        method: "DELETE",
      });
      if (response.ok) {
        setTransactions((prev) => prev.filter((t) => t.id !== id));
        fetchSummary();
      } else {
        showToast("Delete failed on server", "error");
      }
    } catch (error) {
      console.error("Delete failed:", error);
      showToast("Delete failed", "error");
    }
  };
  const updateTransaction = async (updatedTx) => {
    try {
      const response = await apiFetch(`${API_BASE_URL}/transactions/${updatedTx.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: updatedTx.description,
          amount: updatedTx.amount,
          type: updatedTx.type.toLowerCase(),
          category: updatedTx.category.toLowerCase(),
          date: updatedTx.date,
        }),
      });

      if (response.ok) {
        showToast("Transaction updated!", "success");
        fetchHistory();
      } else {
        showToast("Update failed on server", "error");
      }
    } catch (err) {
      showToast("Connection error", "error");
    }
  };
  const bulkDeleteTransactions = async (items) => {
    if (!Array.isArray(items) || items.length === 0) return;

    const idsToDelete = items.map((item) => item.id).filter(Boolean);
    const deleteCalls = idsToDelete.map((id) =>
      apiFetch(`${API_BASE_URL}/transactions/${id}`, { method: "DELETE" }),
    );
    const results = await Promise.allSettled(deleteCalls);

    const successCount = results.filter(
      (r) => r.status === "fulfilled" && r.value?.ok,
    ).length;
    const failedCount = idsToDelete.length - successCount;

    await fetchHistory();
    await fetchSummary();

    if (failedCount === 0) {
      showToast(`Deleted ${successCount} transactions`, "success");
    } else {
      showToast(
        `Deleted ${successCount} transactions, ${failedCount} failed`,
        "warning",
      );
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
      const response = await apiFetch(`${API_BASE_URL}/wealth/${updatedItem.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedItem),
      });

      if (response.ok) {
        showToast("Portfolio updated!", "success");
        fetchWealth();
      } else {
        showToast("Failed to update item", "error");
      }
    } catch (err) {
      showToast("Connection error", "error");
    }
  };
  const saveSettings = async (dataToSave) => {
    try {
      const response = await apiFetch(`${API_BASE_URL}/profile/${currentUser.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dataToSave),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Update failed");
      }

      const data = await response.json();
      const payload = data?.data || data;
      setSettings(payload);
      showToast("Settings saved!", "success");
      return true;
    } catch (err) {
      console.error("Save Error:", err);
      showToast(err.message, "error");
      return false;
    }
  };

  const executeDeleteWealth = async (itemId) => {
    try {
      const response = await apiFetch(`${API_BASE_URL}/wealth/${itemId}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
      });

      if (response.ok) {
        showToast("Item removed", "success");
        fetchWealth();
      }
    } catch (e) {
      showToast("Failed to remove", "error");
    }
  };

  const handleWizardComplete = async (wizardData) => {
    const success = await saveSettings(wizardData);
    if (success) setShowWizard(false);
  };

  useEffect(() => {
    const loadPdfWorker = async () => {
      const src =
        "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
      if (!document.querySelector(`script[src="${src}"]`)) {
        const script = document.createElement("script");
        script.src = src;
        script.async = true;
        script.onload = () => {
          if (window.pdfjsLib) {
            window.pdfjsLib.GlobalWorkerOptions.workerSrc =
              "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
          }
        };
        document.head.appendChild(script);
      }
    };
    loadPdfWorker();
  }, []);

  if (!currentUser) {
    return <LoginScreen onAuthSuccess={setCurrentUser} showToast={showToast} />;
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
        onSignOut={() => {
          setCurrentUser(null);
          setTransactions([]);
          setWealthItems([]);
          localStorage.removeItem("tax_profile"); // Clean up sensitive tax data
          localStorage.removeItem("auth_token");
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          localStorage.removeItem("auth_user");
        }}
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
          <div className="flex gap-3">
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
            {/* <button
              onClick={() => setShowWizard(true)}
              className="px-6 py-4 rounded-2xl bg-blue-600 font-bold hover:bg-blue-700 transition-all"
            >
              Setup Profile
            </button> */}
          </div>
        </header>

        {[TABS.HOME, TABS.ADD, TABS.STATS, TABS.WEALTH].includes(activeTab) && (
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
              {activeTab === TABS.PROFILE && (
                <ProfilePage
                  user={currentUser}
                  settings={settings}
                  onUpdateSettings={saveSettings}
                  onSignOut={() => {
                    setCurrentUser(null);
                    localStorage.removeItem("auth_token");
                    localStorage.removeItem("access_token");
                    localStorage.removeItem("refresh_token");
                    localStorage.removeItem("auth_user");
                  }}
                  triggerConfirm={triggerConfirm}
                />
              )}
              {activeTab === TABS.WEALTH && (
                <WealthPage
                  wealthItems={wealthItems}
                  user={currentUser}
                  authToken={authToken}
                  apiBaseUrl={API_BASE_URL}
                  appId={settings?.appId}
                  onSuccess={fetchWealth}
                  showToast={showToast}
                  triggerConfirm={triggerConfirm}
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
                  refreshProfile={fetchTaxProfile} // Add this
                />
              )}

              {activeTab === TABS.STATS && (
                <StatsPage transactions={transactions} />
              )}

              {activeTab === TABS.ITR && (
                <ITRPage
                  user={currentUser}
                  authToken={authToken}
                  apiBaseUrl={API_BASE_URL} // Pass the base URL here
                  transactions={transactions}
                  setActiveTab={setActiveTab}
                  showToast={showToast}
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

// //Actual code for spendsy -------------------------------------------------------------

// // Context (Logic preserved 100%)
// import { useAuth } from "../../../../packages/shared/context/AuthContext";
// import { useData } from "../../../../packages/shared/context/DataContext";

// // Config & Utils

// // Pages
// import AuditPage from "./pages/AuditPage"; // Section 4
// import StatsPage from "./pages/StatsPage"; // Section 5
// import ITRPage from "./pages/ITRPage"; // ITR Wizard

// export default function App() {

//   // --- 1. Global State (Original Logic) ---
//   const {
//     user,
//     loading,
//     isGuest,
//     error: authError,
//     loginWithGoogle,
//     loginAsGuest,
//     logout,
//   } = useAuth();

//   // --- 2. Local UI State ---

//   const layoutMode = "desktop-full"; // Force desktop view

//   // --- 3. Helpers (Original Logic) ---

//   const triggerConfirm = useCallback((message, action) => {
//     setConfirmModal({ isOpen: true, message, action });
//   }, []);
//   const closeConfirm = useCallback(() => {
//     setConfirmModal({ isOpen: false, message: "", action: null });
//   }, []);
//   const executeConfirm = useCallback(() => {
//     if (confirmModal.action) confirmModal.action();
//     closeConfirm();
//   }, [confirmModal, closeConfirm]);

//   // --- 4. Effects (Original Logic) ---
//   useEffect(() => {
//     const checkBackend = async () => {
//       try {
//         const response = await fetch(`${API_BASE_URL}/test/`);
//         const data = await response.json();
//         console.log("Backend Status:", data.message);
//       } catch (err) {
//         console.error("Backend unreachable:", err);
//         showToast("Backend connection failed", "error");
//       }
//     };

//     if (user) checkBackend();
//   }, [user, showToast]);

// useEffect(() => {
//     // 1. ASYNC PDF WORKER INITIALIZATION
//     const loadPdfWorker = async () => {
//       const src = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
//       if (!document.querySelector(`script[src="${src}"]`)) {
//         const script = document.createElement("script");
//         script.src = src;
//         script.async = true; // Added for performance
//         script.onload = () => {
//           if (window.pdfjsLib) {
//             window.pdfjsLib.GlobalWorkerOptions.workerSrc =
//               "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
//           }
//         };
//         document.head.appendChild(script);
//       }
//     };
//     loadPdfWorker();

//     // 3. ONBOARDING WIZARD TRIGGER
//     // Logic: Only show if user is fully logged in, not a guest,
//     // and Django profile data shows no income.
//     const incomeValue = parseFloat(settings?.monthlyIncome || 0);

//     if (user && !isGuest && settings && incomeValue === 0) {
//       const timer = setTimeout(() => {
//         setShowWizard(true);
//       }, 1500);
//       return () => clearTimeout(timer);
//     }
//   }, [user, isGuest, settings, setIsHeaderPinned, setShowWizard]); // Added setters to dependency array for completeness

//   // --- 5. Data Processing (Original Logic) ---

//   // --- 6. Handlers (Original Logic) ---

// // Inside your main App.jsx

// // Locate this function around line 250

//   // --- 7. RENDER ---
//   if (loading) return <Loading />;
//   if (!user && !isGuest)
//     return (
//       <LoginScreen
//         onLoginGoogle={loginWithGoogle}
//         onGuest={loginAsGuest}
//         error={authError}
//       />
//     );

//   return (
//     <div
//       className={cn(
//         "min-h-screen transition-colors duration-1000 font-sans pb-28 md:pb-0 md:pl-28 scroll-smooth selection:bg-blue-500",
//         theme === "dark"
//           ? "bg-[#08090a] text-white"
//           : "bg-[#cfd9e5] text-slate-900",
//       )}
//     >
//       {/* BACKGROUND SYSTEM */}
//       <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
//         {/* Glowing Gradient Aura */}
//         <motion.div
//           animate={{ scale: [1, 1.2, 1], opacity: [0.15, 0.25, 0.15] }}
//           transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
//           className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,#3b82f6,transparent_75%)] blur-[120px]"
//         />

//         <svg
//           width="100%"
//           height="100%"
//           className={theme === "dark" ? "opacity-[0.15]" : "opacity-[0.25]"}
//         >
//           <defs>
//             <pattern
//               id="diagonal-parallels"
//               width="80"
//               height="80"
//               patternUnits="userSpaceOnUse"
//             >
//               <circle
//                 cx="2"
//                 cy="2"
//                 r="1.5"
//                 fill={theme === "dark" ? "white" : "#475569"}
//               />
//               <line
//                 x1="15"
//                 y1="65"
//                 x2="65"
//                 y2="15"
//                 stroke={theme === "dark" ? "white" : "#475569"}
//                 strokeWidth="1.2"
//                 opacity="0.4"
//               />
//               <line
//                 x1="5"
//                 y1="55"
//                 x2="55"
//                 y2="5"
//                 stroke={theme === "dark" ? "white" : "#475569"}
//                 strokeWidth="1.2"
//                 opacity="0.4"
//               />
//             </pattern>
//           </defs>
//           <rect width="100%" height="100%" fill="url(#diagonal-parallels)" />
//         </svg>
//       </div>

//       <ConfirmationDialog
//         isOpen={confirmModal.isOpen}
//         message={confirmModal.message}
//         onConfirm={executeConfirm}
//         onCancel={closeConfirm}
//       />
//       <Toast
//         message={toast.msg}
//         type={toast.type}
//         isVisible={toast.show}
//         onClose={() => setToast((prev) => ({ ...prev, show: false }))}
//       />
//       <WelcomeWizard isOpen={showWizard} onComplete={handleWizardComplete} />

//       <Navigation
//         activeTab={activeTab}
//         setActiveTab={setActiveTab}
//         onSignOut={async () => {
//           await logout();
//           setActiveTab(TABS.HOME);
//         }}
//       />

//       <div
//         className={cn(
//           "mx-auto min-h-screen relative z-10 transition-all duration-700",
//           "max-w-6xl px-12", // Always desktop
//         )}
//       >
//         {/* // --- Header Starts --- */}
//         {![TABS.PROFILE].includes(activeTab) && (
//           <header
//             className={cn(
//               "z-40 pt-10 pb-2 transition-all duration-500",
//               isHeaderPinned
//                 ? "sticky top-0 backdrop-blur-xl border-b border-white/5"
//                 : "relative",
//             )}
//             style={{ opacity: scrollOpacity }}
//           >
//             <div className="flex items-center justify-between mb-2 px-2">
//               {/* 1. CONFIG: LEFT CONTENT (Branding & User Name)
//                */}
//               {[
//                 TABS.HOME,
//                 TABS.HISTORY,
//                 TABS.ADD,
//                 TABS.AUDIT,
//                 TABS.STATS,
//                 TABS.WEALTH,
//                 TABS.ITR,
//               ].includes(activeTab) ? (
//                 <div className="flex flex-col">
//                   <div className="flex items-center gap-2 mb-2">
//                     <div className="p-1.5 bg-blue-500/10 rounded-lg">
//                       <Zap className="w-3.5 h-3.5 text-blue-500 fill-blue-500" />
//                     </div>
//                     <span className="text-[11px] font-bold tracking-[0.3em] uppercase opacity-60">
//                       Spendsy
//                     </span>
//                   </div>
//                   <h1 className="text-4xl font-black tracking-tight leading-tight">
//                     <span
//                       className={
//                         theme === "dark" ? "text-white" : "text-slate-900"
//                       }
//                     >
//                       {displayName}
//                     </span>
//                   </h1>
//                 </div>
//               ) : (
//                 <div /> /* Spacer to keep Right content on the right if Left is hidden */
//               )}

//               {/* 2. CONFIG: RIGHT CONTENT (Theme & Pin Buttons)
//                */}
//               {[TABS.HOME, TABS.ADD, TABS.STATS].includes(activeTab) && (
//                 <div className="flex gap-2 p-1 bg-white/5 border border-white/10 backdrop-blur-md rounded-full shadow-lg">
//                   <button
//                     onClick={toggleTheme}
//                     className={cn(
//                       "p-3 rounded-full transition-all duration-300 active:scale-90",
//                       theme === "dark"
//                         ? "hover:bg-white/10 text-amber-400"
//                         : "hover:bg-slate-200 text-blue-600",
//                     )}
//                   >
//                     {theme === "dark" ? (
//                       <Sun className="w-4 h-4" />
//                     ) : (
//                       <Moon className="w-4 h-4" />
//                     )}
//                   </button>
//                   <button
//                     onClick={togglePin}
//                     className={cn(
//                       "p-3 rounded-full transition-all duration-300 active:scale-90",
//                       isHeaderPinned
//                         ? "bg-blue-500 text-white shadow-md"
//                         : "hover:bg-white/10 text-slate-400",
//                     )}
//                   >
//                     {isHeaderPinned ? (
//                       <Pin className="w-4 h-4 fill-current" />
//                     ) : (
//                       <PinOff className="w-4 h-4" />
//                     )}
//                   </button>
//                 </div>
//               )}
//             </div>

// {/* 3. CONFIG: HERO CARD (Current Balance & Stats) */}
// {[TABS.HOME, TABS.ADD, TABS.STATS].includes(activeTab) && (
//   <motion.div
//     whileHover={{ scale: 1.01, y: -2 }}
//     transition={{ type: "spring", stiffness: 300, damping: 20 }}
//     className={cn(
//       "relative overflow-hidden rounded-[2rem] sm:rounded-[2.5rem] p-6 sm:p-10 transition-all duration-500 border",
//       theme === "dark"
//         ? "bg-gradient-to-br from-white/[0.08] to-white/[0.02] border-white/10 shadow-[0_30px_60px_-15px_rgba(0,0,0,0.5)]"
//         : "bg-gradient-to-br from-white to-slate-50 border-white/60 shadow-[0_20px_40px_-12px_rgba(0,0,0,0.1)]"
//     )}
//   >
//     {/* Ambient Background Glows */}
//     <div className="absolute -top-24 -right-24 w-64 h-64 bg-blue-500/20 blur-[80px] rounded-full pointer-events-none" />
//     <div className="absolute -bottom-24 -left-24 w-64 h-64 bg-purple-500/10 blur-[80px] rounded-full pointer-events-none" />

//     <div className="relative z-10">

//       {/* 1. Header Label */}
//       <div className="flex items-center gap-2 mb-4 sm:mb-6 opacity-50">
//         <LayoutIcon className="w-4 h-4" />
//         <p className="text-[10px] sm:text-xs font-bold uppercase tracking-widest">
//           {activeTab === TABS.WEALTH ? "Net Valuation" : "Total Balance"}
//         </p>
//       </div>

//       {/* 2. Main Balance Figure (Dynamic Sizing Logic) */}
//       {(() => {
//         // A. Calculate the value string first
//         const displayValue = activeTab === TABS.WEALTH
//           ? formatIndianCompact(netWorth.assets - netWorth.liabilities)
//           : `₹${balance.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;

//         // B. Determine font size based on character count (Mobile Only)
//         // Length > 13 (e.g. ₹10,00,000.00) -> text-2xl
//         // Length > 9  (e.g. ₹1,00,000)    -> text-3xl
//         // Short       (e.g. ₹5,000)       -> text-4xl
//         const mobileFontSize =
//           displayValue.length > 13 ? "text-2xl" :
//           displayValue.length > 9 ? "text-3xl" :
//           "text-4xl";

//         return (
//           <h2
//             className={cn(
//               "font-black mb-8 sm:mb-10 tracking-tighter leading-tight tabular-nums bg-clip-text text-transparent bg-gradient-to-r",
//               // Apply dynamic mobile font size, force text-7xl on desktop
//               `${mobileFontSize} sm:text-6xl md:text-7xl`,
//               theme === "dark"
//                 ? "from-white via-white to-white/70"
//                 : "from-slate-900 via-slate-800 to-slate-600"
//             )}
//           >
//             {displayValue}
//           </h2>
//         );
//       })()}

//       {/* 3. Stats Grid */}
//       <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-6">

//         {/* Income Tile */}
//         <div
//           className={cn(
//             "group p-4 sm:p-5 rounded-[1.5rem] sm:rounded-[2rem] border transition-all duration-300",
//             theme === "dark"
//               ? "bg-black/20 border-white/5 hover:bg-white/5"
//               : "bg-white/50 border-slate-200/60 hover:bg-white"
//           )}
//         >
//           <div className="flex flex-col gap-2 sm:gap-4">
//             <div className="flex items-center gap-2">
//               <div className="p-1.5 sm:p-2 rounded-full bg-emerald-500/10 border border-emerald-500/20">
//                 <ArrowDown className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-emerald-500" />
//               </div>
//               <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-emerald-500/80">
//                 Income
//               </span>
//             </div>
//             <p className="font-bold text-lg sm:text-2xl tracking-tight tabular-nums truncate">
//               {activeTab === TABS.WEALTH
//                 ? formatIndianCompact(netWorth.assets)
//                 : `₹${totals.income.toLocaleString("en-IN")}`}
//             </p>
//           </div>
//         </div>

//         {/* Expense Tile */}
//         <div
//           className={cn(
//             "group p-4 sm:p-5 rounded-[1.5rem] sm:rounded-[2rem] border transition-all duration-300",
//             theme === "dark"
//               ? "bg-black/20 border-white/5 hover:bg-white/5"
//               : "bg-white/50 border-slate-200/60 hover:bg-white"
//           )}
//         >
//           <div className="flex flex-col gap-2 sm:gap-4">
//             <div className="flex items-center gap-2">
//               <div className="p-1.5 sm:p-2 rounded-full bg-rose-500/10 border border-rose-500/20">
//                 <ArrowUp className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-rose-500" />
//               </div>
//               <span className="text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-rose-500/80">
//                 Expense
//               </span>
//             </div>
//             <p className="font-bold text-lg sm:text-2xl tracking-tight tabular-nums truncate">
//               {activeTab === TABS.WEALTH
//                 ? formatIndianCompact(netWorth.liabilities)
//                 : `₹${totals.expenses.toLocaleString("en-IN")}`}
//             </p>
//           </div>
//         </div>
//       </div>
//     </div>
//   </motion.div>
// )}

//           </header>
//         )}
//         {/* // --- Header Ends --- */}

//         <main
//           className={cn(
//             "pb-4",
//             [TABS.PROFILE, TABS.HISTORY, TABS.AUDIT, TABS.ITR].includes(
//               activeTab,
//             )
//               ? "pt-5"
//               : "pt-8",
//           )}
//         >

//           <AnimatePresence mode="wait">
//           {/* <AnimatePresence mode="wait"> */}
//             <motion.div
//               key={activeTab}
//               initial={{ opacity: 0, scale: 0.98, x: 20 }}
//               animate={{ opacity: 1, scale: 1, x: 0 }}
//               exit={{ opacity: 0, scale: 0.98, x: -20 }}
//               transition={{ duration: 0.3, ease: [0.19, 1, 0.22, 1] }} // Snappy Slide
//             >

//             </motion.div>
//           </AnimatePresence>

//
//         </main>
//       </div>
//     </div>
//   );
// }
