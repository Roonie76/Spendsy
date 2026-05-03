import React, { useState } from "react";
import { 
  AreaChart, 
  Area, 
  Tooltip, 
  ResponsiveContainer, 
  PieChart as RePieChart, 
  Pie, 
  Cell 
} from "recharts";
import { 
  TrendingUp, 
  Plus, 
  PieChart as PieIcon, 
  Wallet, 
  Camera, 
  PlusCircle,
  LayoutGrid,
  RefreshCw
} from "lucide-react";
import { formatIndianCompact, buildAuthHeader, formatLocalDate } from "@shared/utils/helpers";
import { BANKS, CURRENCY_SYMBOL } from "@shared/config/constants";
import UnitSelector from "../components/domain/UnitSelector";
import WealthItem from "../components/domain/WealthItem";
import { apiFetch } from "../api";
import { WealthSkeleton } from "../components/ui/Skeletons";

const WealthPage = ({
  wealthItems,
  user,
  authToken,
  apiBaseUrl,
  appId,
  showToast,
  triggerConfirm,
  onSuccess,
  netWorthHistory = [],
  isLoading = false,
}) => {
  const [wealthName, setWealthName] = useState("");
  const [wealthAmount, setWealthAmount] = useState("");
  const [wealthType, setWealthType] = useState("asset");
  const [wealthUnit, setWealthUnit] = useState(1);
  const [isLoan, setIsLoan] = useState(false);
  const [loanData, setLoanData] = useState({
    bankName: "",
    principal: "",
    roi: "",
    tenure: "",
    loanType: "personal",
  });

  // --- 1. Calculate Live Net Worth ---
  const totalAssets = wealthItems
    .filter((i) => i.type === "asset")
    .reduce((acc, i) => acc + parseFloat(i.amount || 0), 0);
  const totalLiabilities = wealthItems
    .filter((i) => i.type === "liability")
    .reduce((acc, i) => acc + parseFloat(i.amount || 0), 0);
  const netWorth = totalAssets - totalLiabilities;

  // --- 2. Chart Data ---
  const historyData = netWorthHistory.length > 0 
    ? netWorthHistory.map(s => ({
        month: new Date(s.date).toLocaleDateString("en-US", { month: "short" }),
        value: parseFloat(s.net_worth)
      }))
    : [
        { month: "Today", value: totalAssets - totalLiabilities }
      ];

  // --- 3. Handlers ---
  const executeTakeSnapshot = async () => {
    try {
      await apiFetch(`${apiBaseUrl}/net-worth/snapshot`, {
        method: "POST",
        body: JSON.stringify({
          date: formatLocalDate(new Date()),
          total_assets: totalAssets,
          total_liabilities: totalLiabilities,
          net_worth: netWorth,
        }),
      });
      showToast("Snapshot saved!", "success");
      onSuccess();
    } catch (error) {
      showToast("Failed to save snapshot", "error");
    }
  };

  const executeAddWealth = async (data) => {
    try {
      if (data.isLoan) {
        // Calculate EMI and Remaining Balance for initial entry
        // EMI = [P x R x (1+R)^N]/[(1+R)^N-1]
        const p = parseFloat(data.loan.principal);
        const r = parseFloat(data.loan.roi) / 12 / 100;
        const n = parseInt(data.loan.tenure);
        const emi = (p * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);

        await apiFetch(`${apiBaseUrl}/loans`, {
          method: "POST",
          body: JSON.stringify({
            loan_type: data.loan.loanType,
            bank_name: data.loan.bankName,
            principal_amount: p,
            interest_rate: parseFloat(data.loan.roi),
            tenure_months: n,
            emi_amount: emi.toFixed(2),
            remaining_balance: p.toFixed(2), // Initial balance is principal
          }),
        });
        setLoanData({ bankName: "", principal: "", roi: "", tenure: "", loanType: "personal" });
        setIsLoan(false);
      } else {
        await apiFetch(`${apiBaseUrl}/wealth`, {
          method: "POST",
          body: JSON.stringify({
            title: data.title,
            amount: parseFloat(data.amount) * parseFloat(data.unit),
            type: data.type,
            category: "General",
          }),
        });
      }

      setWealthName("");
      setWealthAmount("");
      showToast("Item added successfully!", "success");
      onSuccess(); 
    } catch (error) {
      showToast("Server error", "error");
    }
  };

  const requestAddWealth = (e) => {
    e.preventDefault();
    if (isLoan) {
      if (!loanData.bankName || !loanData.principal || !loanData.roi || !loanData.tenure) return;
      const loanTypeDisplay = loanData.loanType.charAt(0).toUpperCase() + loanData.loanType.slice(1);
      triggerConfirm(`Add ${loanTypeDisplay} loan from ${loanData.bankName}?`, () =>
        executeAddWealth({ isLoan: true, loan: loanData }),
      );
    } else {
      if (!wealthName || !wealthAmount || !user) return;
      const newItem = {
        title: wealthName,
        amount: wealthAmount,
        type: wealthType,
        unit: wealthUnit,
        isLoan: false
      };
      triggerConfirm("Confirm adding this asset/liability?", () =>
        executeAddWealth(newItem),
      );
    }
  };

  const executeDeleteWealth = async (item) => {
    try {
      const endpoint = item.is_loan ? "loans" : "wealth";
      await apiFetch(`${apiBaseUrl}/${endpoint}/${item.uid}`, {
        method: "DELETE",
      });

      showToast("Item removed", "success");
      onSuccess(); 
    } catch (e) {
      showToast("Failed to remove", "error");
    }
  };

  const requestDeleteWealth = (item) =>
    triggerConfirm(`Remove ${item.title}?`, () => executeDeleteWealth(item));

  const executeUpdateWealth = async (id, updatedData) => {
    // Determine if it's a loan or regular item based on the ID prefix or data
    const isLoanItem = id.startsWith("loan_");
    const item = wealthItems.find(i => i.id === id);
    if (!item) {
        showToast("Item not found", "error");
        return;
    }

    try {
      const endpoint = isLoanItem ? "loans" : "wealth";
      const payload = isLoanItem ? {
        bank_name: updatedData.title,
        remaining_balance: updatedData.amount,
        interest_rate: updatedData.interest_rate,
        tenure_months: updatedData.tenure
      } : {
        title: updatedData.title,
        amount: updatedData.amount
      };

      await apiFetch(`${apiBaseUrl}/${endpoint}/${item.uid}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });

      showToast(`${isLoanItem ? 'Loan' : 'Item'} updated`, "success");
      onSuccess(); 
    } catch (error) {
      showToast("Server connection error", "error");
    }
  };
  
  if (isLoading) return <WealthSkeleton />;

  return (
    <div className="space-y-6 pb-28 animate-in fade-in duration-500">
      {/* Header with Title and Snapshot */}
      <div className="flex justify-between items-center px-1">
        <h2 className="text-xl sm:text-2xl font-bold text-white">Wealth</h2>
        <button
          onClick={executeTakeSnapshot}
          className="flex items-center gap-2 rounded-xl bg-emerald-500/10 px-4 py-2.5 text-xs font-bold text-emerald-300 transition-all hover:bg-emerald-500/20 border border-emerald-500/20 active:scale-95"
        >
          <Camera className="h-4 w-4" />
          Take Snapshot
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Visualizations & List */}
        <div className="lg:col-span-8 space-y-6">
          {/* Net Worth Graph Card */}
          <div className="bg-white/5 backdrop-blur-xl border border-white/10 p-6 rounded-[2rem] relative overflow-hidden shadow-2xl group">
            <div className="absolute -top-24 -right-24 w-64 h-64 bg-emerald-500/10 blur-[80px] rounded-full pointer-events-none group-hover:bg-emerald-500/15 transition-colors"></div>
            
            <div className="relative z-10 mb-8 flex justify-between items-start">
              <div>
                <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-4">
                  <TrendingUp className="w-4 h-4 text-emerald-400" /> Net Worth History
                </h3>
                <div className="flex items-baseline gap-3">
                  <h3 className="text-3xl font-black text-white tracking-tight">
                    {formatIndianCompact(netWorth)}
                  </h3>
                  <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                    <TrendingUp className="w-3 h-3 text-emerald-400" />
                    <span className="text-[10px] font-bold text-emerald-400">
                      {netWorthHistory.length >= 2 ? (() => {
                        const latest = parseFloat(netWorthHistory[netWorthHistory.length - 1].net_worth);
                        const previous = parseFloat(netWorthHistory[netWorthHistory.length - 2].net_worth);
                        if (previous === 0) return '0.0%';
                        const change = ((latest - previous) / previous) * 100;
                        return `${change > 0 ? '+' : ''}${change.toFixed(1)}%`;
                      })() : '0.0%'} 
                    </span>
                  </div>
                </div>
                <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1">Growth vs last month</p>
              </div>
            </div>

            <div className="h-48 w-full">
              <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                <AreaChart data={historyData}>
                  <defs>
                    <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0f172a",
                      border: "1px solid #334155",
                      borderRadius: "12px",
                      padding: "12px"
                    }}
                    itemStyle={{ color: "#fff", fontSize: "12px", fontWeight: "bold" }}
                    formatter={(value) => [`₹${formatIndianCompact(value)}`, "Net Worth"]}
                    labelStyle={{ display: "none" }}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#10b981"
                    strokeWidth={4}
                    fillOpacity={1}
                    fill="url(#colorValue)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Portfolio List */}
          <div className="bg-white/5 backdrop-blur-xl p-6 rounded-[2rem] border border-white/10">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-6">
              <Wallet className="w-4 h-4 text-blue-400" /> Your Portfolio
            </h3>
            {wealthItems.length === 0 ? (
              <div className="text-center py-12 border border-dashed border-white/10 rounded-2xl">
                <p className="text-slate-500 text-xs font-bold uppercase tracking-widest">
                  No assets or liabilities added.
                </p>
                <p className="text-[10px] text-slate-600 mt-1">Add items using the form to start tracking.</p>
              </div>
            ) : (
              <div className="space-y-4 pr-1 max-h-[600px] overflow-y-auto custom-scrollbar">
                {wealthItems.map((item) => (
                  <WealthItem
                    key={item.id}
                    item={item}
                    onDelete={() => requestDeleteWealth(item)}
                    onUpdate={executeUpdateWealth}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Actions & Stats */}
        <div className="lg:col-span-4 space-y-6">
          {/* Add New Item Form */}
          <div className="bg-white/5 backdrop-blur-xl p-6 rounded-[2rem] border border-white/10 shadow-xl">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-6">
              <PlusCircle className="w-4 h-4 text-indigo-400" /> Quick Add
            </h3>

            <form onSubmit={requestAddWealth} className="flex flex-col gap-4">
              <div className="flex bg-black/30 p-1 rounded-xl border border-white/5">
                <button
                  type="button"
                  onClick={() => { setWealthType("asset"); setIsLoan(false); }}
                  className={`flex-1 py-2.5 rounded-lg text-[10px] font-bold transition-all ${wealthType === "asset" ? "bg-emerald-500/20 text-emerald-300" : "text-slate-500"}`}
                >
                  Asset
                </button>
                <button
                  type="button"
                  onClick={() => setWealthType("liability")}
                  className={`flex-1 py-2.5 rounded-lg text-[10px] font-bold transition-all ${wealthType === "liability" ? "bg-rose-500/20 text-rose-300" : "text-slate-500"}`}
                >
                  Liability
                </button>
              </div>

              {wealthType === "liability" && (
                <button
                  type="button"
                  onClick={() => setIsLoan(v => !v)}
                  className={`relative flex items-center gap-3 w-full px-4 py-3 rounded-2xl border transition-all duration-300 ${
                    isLoan
                      ? "bg-rose-500/10 border-rose-500/30 shadow-lg shadow-rose-900/20"
                      : "bg-white/5 border-white/10 hover:border-white/20"
                  }`}
                >
                  <div className={`relative w-8 h-4 rounded-full transition-all duration-300 shrink-0 ${isLoan ? "bg-rose-500" : "bg-white/10"}`}>
                    <div className={`absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-white shadow transition-all duration-300 ${isLoan ? "translate-x-4" : "translate-x-0"}`} />
                  </div>
                  <div className="text-left">
                    <p className={`text-[11px] font-bold transition-colors ${isLoan ? "text-rose-300" : "text-slate-400"}`}>
                      Structured Loan
                    </p>
                  </div>
                  {isLoan && (
                    <span className="ml-auto text-[8px] font-bold bg-rose-500/20 text-rose-300 px-2 py-0.5 rounded-full">
                      ACTIVE
                    </span>
                  )}
                </button>
              )}

              {wealthType === "liability" && isLoan ? (
                <div className="space-y-3 animate-in fade-in slide-in-from-top-2 duration-300">
                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-1">Bank</label>
                    <div className="relative">
                      <select
                        value={loanData.bankName}
                        onChange={e => setLoanData({...loanData, bankName: e.target.value})}
                        className="w-full px-3 pr-8 py-3 bg-black/20 border border-white/10 rounded-2xl text-xs text-white outline-none focus:border-rose-500/50 appearance-none"
                        required
                      >
                        <option value="" disabled className="bg-[#0f172a] text-white">Select Bank</option>
                        {BANKS.map(bank => (
                          <option key={bank} value={bank} className="bg-[#0f172a] text-white">{bank}</option>
                        ))}
                        <option value="Other" className="bg-[#0f172a] text-white">Other</option>
                      </select>
                      <svg className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd"/></svg>
                    </div>
                  </div>

                  <div className="flex flex-col gap-1">
                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-1">Principal ₹</label>
                    <input
                      type="number"
                      value={loanData.principal}
                      onChange={e => setLoanData({...loanData, principal: e.target.value})}
                      className="w-full px-3 py-3 bg-black/20 border border-white/10 rounded-2xl text-xs text-white outline-none placeholder:text-slate-700 focus:border-rose-500/50 transition-colors"
                      placeholder="Principal amount"
                      required
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex flex-col gap-1">
                      <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-1">Rate %</label>
                      <input
                        type="number" step="0.1"
                        value={loanData.roi}
                        onChange={e => setLoanData({...loanData, roi: e.target.value})}
                        className="w-full px-3 py-3 bg-black/20 border border-white/10 rounded-2xl text-xs text-white outline-none placeholder:text-slate-700 focus:border-rose-500/50"
                        placeholder="ROI" required
                      />
                    </div>
                    <div className="flex flex-col gap-1">
                      <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider px-1">Tenure Mo.</label>
                      <input
                        type="number"
                        value={loanData.tenure}
                        onChange={e => setLoanData({...loanData, tenure: e.target.value})}
                        className="w-full px-3 py-3 bg-black/20 border border-white/10 rounded-2xl text-xs text-white outline-none placeholder:text-slate-700 focus:border-rose-500/50"
                        placeholder="Months" required
                      />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      inputMode="decimal"
                      value={wealthAmount}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val === "" || /^\d+(\.\d{0,2})?$/.test(val)) setWealthAmount(val);
                      }}
                      className="w-full flex-1 px-4 py-3 bg-black/20 border border-white/10 rounded-2xl text-sm text-white outline-none placeholder:text-slate-700 focus:border-blue-500/50 transition-colors"
                      placeholder="Amount"
                      required
                    />
                    <div className="shrink-0">
                      <UnitSelector currentUnit={wealthUnit} onSelect={setWealthUnit} />
                    </div>
                  </div>

                  <input
                    type="text"
                    value={wealthName}
                    onChange={(e) => setWealthName(e.target.value)}
                    className="w-full px-4 py-3 bg-black/20 border border-white/10 rounded-2xl text-sm text-white outline-none placeholder:text-slate-700 focus:border-blue-500/50 transition-colors"
                    placeholder={wealthType === 'asset' ? "e.g. Gold, House" : "e.g. Credit Card"}
                    required
                  />
                </div>
              )}

              <button
                type="submit"
                className="w-full bg-blue-600 hover:bg-blue-500 text-white py-3.5 rounded-2xl font-bold shadow-lg shadow-blue-900/20 active:scale-95 transition-all mt-2 text-xs uppercase tracking-widest"
              >
                Add {isLoan ? 'Structured Loan' : 'Item'}
              </button>
            </form>
          </div>

          {/* Portfolio Allocation Pie Chart */}
          {wealthItems.filter(i => i.type === 'asset').length > 0 && (
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 p-6 rounded-[2rem] relative overflow-hidden">
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-6">
                <PieIcon className="w-4 h-4 text-amber-400" /> Asset Allocation
              </h3>
              <div className="space-y-6">
                <div className="h-48 relative">
                  <ResponsiveContainer width="100%" height="100%">
                    <RePieChart>
                      <Pie
                        data={(() => {
                          const assets = wealthItems.filter(i => i.type === 'asset');
                          const groups = assets.reduce((acc, item) => {
                            const title = (item.title || 'Other').split(' ')[0];
                            acc[title] = (acc[title] || 0) + parseFloat(item.amount || 0);
                            return acc;
                          }, {});
                          const data = Object.entries(groups).map(([name, value]) => ({ name, value }));
                          return data;
                        })()}
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                        stroke="none"
                      >
                        {(() => {
                          const assets = wealthItems.filter(i => i.type === 'asset');
                          const groups = assets.reduce((acc, item) => {
                            const title = (item.title || 'Other').split(' ')[0];
                            acc[title] = (acc[title] || 0) + parseFloat(item.amount || 0);
                            return acc;
                          }, {});
                          return Object.entries(groups).map((_, index) => (
                            <Cell key={`cell-${index}`} fill={['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6'][index % 5]} />
                          ));
                        })()}
                      </Pie>
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '12px' }}
                        itemStyle={{ color: '#fff', fontSize: '10px', fontWeight: 'bold' }}
                        formatter={(value) => formatIndianCompact(value)}
                      />
                    </RePieChart>
                  </ResponsiveContainer>
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <p className="text-[10px] text-slate-500 font-bold uppercase">Assets</p>
                    <p className="text-sm font-black text-white">{formatIndianCompact(totalAssets)}</p>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 gap-2 max-h-40 overflow-y-auto custom-scrollbar pr-1">
                  {(() => {
                    const assets = wealthItems.filter(i => i.type === 'asset');
                    const groups = assets.reduce((acc, item) => {
                      const title = (item.title || 'Other').split(' ')[0];
                      acc[title] = (acc[title] || 0) + parseFloat(item.amount || 0);
                      return acc;
                    }, {});
                    return Object.entries(groups).sort((a, b) => b[1] - a[1]).map(([name, value], idx) => {
                      const pct = ((value / totalAssets) * 100).toFixed(1);
                      const color = ['bg-emerald-500', 'bg-blue-500', 'bg-amber-500', 'bg-rose-500', 'bg-violet-500'][idx % 5];
                      return (
                        <div key={name} className="flex items-center justify-between p-2 rounded-xl bg-white/5 border border-white/5">
                          <div className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${color}`} />
                            <span className="text-[10px] font-bold text-slate-400 truncate max-w-[80px]">{name}</span>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-[10px] font-black text-white">{pct}%</span>
                            <span className="text-[9px] text-slate-500 font-bold">{formatIndianCompact(value)}</span>
                          </div>
                        </div>
                      );
                    });
                  })()}
                </div>
              </div>
            </div>
          )}
        </div>
    </div>
  </div>
  );
};

export default WealthPage;
