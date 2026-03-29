//Database needed
// Section 6 Wealth Page
import React, { useState } from "react";
import { AreaChart, Area, Tooltip, ResponsiveContainer } from "recharts";
// import { db } from "../../../../../packages/shared/config/constants";
import { formatIndianCompact, buildAuthHeader } from "@shared/utils/helpers";
import { BANKS } from "@shared/config/constants";
import UnitSelector from "../components/domain/UnitSelector";
import WealthItem from "../components/domain/WealthItem";
import { apiFetch } from "../api";

const WealthPage = ({
  wealthItems,
  user,
  authToken,
  apiBaseUrl,
  appId,
  showToast,
  triggerConfirm,
  onSuccess, // <--- ADD THIS HERE
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

  // --- 2. Mock History Data ---
  const historyData = [
    { month: "Sep", value: netWorth * 0.85 },
    { month: "Oct", value: netWorth * 0.9 },
    { month: "Nov", value: netWorth * 0.92 },
    { month: "Dec", value: netWorth * 0.98 },
    { month: "Jan", value: netWorth },
  ];

  // --- 3. Handlers ---
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
  
  return (
    <div className="space-y-6 pb-28 animate-in slide-in-from-bottom-8">
      {/* NEW: Net Worth Graph Card */}
      <div className="bg-gradient-to-br from-emerald-900/40 to-teal-900/40 border border-white/10 p-5 sm:p-6 rounded-[2rem] sm:rounded-[2.5rem] relative overflow-hidden shadow-2xl">
        <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/10 blur-[80px] rounded-full pointer-events-none"></div>

        <div className="relative z-10 mb-4 flex justify-between items-end">
          <div>
            <p className="text-[10px] sm:text-xs text-emerald-200 font-bold uppercase tracking-wider mb-1">
              Total Net Worth
            </p>
            {/* Responsive Font Size */}
            <h3 className="text-2xl sm:text-3xl font-bold text-white">
              {formatIndianCompact(netWorth)}
            </h3>
          </div>
          <div className="text-right">
            <p className="text-[10px] text-emerald-200/60 font-bold">
              vs last month
            </p>
            <p className="text-xs sm:text-sm font-bold text-emerald-300">
              +2.4%
            </p>
          </div>
        </div>

        <div className="h-32 w-full -ml-2">
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
                  borderRadius: "8px",
                }}
                itemStyle={{ color: "#fff", fontSize: "12px" }}
                formatter={(value) => [
                  `₹${formatIndianCompact(value)}`,
                  "Net Worth",
                ]}
                labelStyle={{ display: "none" }}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#10b981"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorValue)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      {/* Add New Item Form */}
      <div className="bg-white/5 backdrop-blur-xl p-5 sm:p-6 rounded-[2rem] sm:rounded-[2.5rem] border border-white/10">
        <h3 className="text-base sm:text-lg font-bold text-white mb-4 sm:mb-6">
          Add {wealthType === 'liability' && isLoan ? 'Loan Details' : 'Asset / Liability'}
        </h3>

        <form onSubmit={requestAddWealth} className="flex flex-col gap-3 sm:gap-4">
          <div className="flex bg-black/30 p-1 rounded-xl border border-white/5">
            <button
              type="button"
              onClick={() => { setWealthType("asset"); setIsLoan(false); }}
              className={`flex-1 py-2 sm:py-3 rounded-lg text-[10px] sm:text-xs font-bold transition-all ${wealthType === "asset" ? "bg-emerald-500/20 text-emerald-300" : "text-slate-500"}`}
            >
              Asset
            </button>
            <button
              type="button"
              onClick={() => setWealthType("liability")}
              className={`flex-1 py-2 sm:py-3 rounded-lg text-[10px] sm:text-xs font-bold transition-all ${wealthType === "liability" ? "bg-rose-500/20 text-rose-300" : "text-slate-500"}`}
            >
              Liability
            </button>
          </div>

          {wealthType === "liability" && (
            <div className="flex items-center gap-2 mb-2 px-2">
              <input 
                type="checkbox" 
                id="isLoan" 
                checked={isLoan} 
                onChange={e => setIsLoan(e.target.checked)}
                className="w-4 h-4 rounded border-white/10 bg-black/20 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="isLoan" className="text-xs font-bold text-slate-400 cursor-pointer">
                Structured Loan (Tenure, ROI, Bank)
              </label>
            </div>
          )}

          {wealthType === "liability" && isLoan ? (
            <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
              <select
                value={loanData.bankName}
                onChange={e => setLoanData({...loanData, bankName: e.target.value})}
                className="w-full px-4 py-3 bg-black/20 border border-white/10 rounded-2xl text-sm text-white outline-none focus:border-rose-500/50 appearance-none"
                required
              >
                <option value="" disabled>Select Bank</option>
                {BANKS.map(bank => (
                  <option key={bank} value={bank}>{bank}</option>
                ))}
                <option value="Other">Other</option>
              </select>

              <div className="space-y-1">
                <div className="flex justify-between px-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Principal Amount</label>
                  <span className="text-[10px] font-bold text-rose-300">₹{formatIndianCompact(loanData.principal || 0)}</span>
                </div>
                <input
                  type="range"
                  min="10000"
                  max="10000000"
                  step="10000"
                  value={loanData.principal || 10000}
                  onChange={e => setLoanData({...loanData, principal: e.target.value})}
                  className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-rose-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <select 
                  value={loanData.loanType}
                  onChange={e => setLoanData({...loanData, loanType: e.target.value})}
                  className="w-full px-4 py-3 bg-black/20 border border-white/10 rounded-2xl text-sm text-white outline-none focus:border-rose-500/50"
                >
                  <option value="personal">Personal Loan</option>
                  <option value="home">Home Loan</option>
                  <option value="car">Car Loan</option>
                  <option value="student">Student Loan</option>
                </select>
                <input
                  type="number"
                  value={loanData.tenure}
                  onChange={e => setLoanData({...loanData, tenure: e.target.value})}
                  className="w-full px-4 py-3 bg-black/20 border border-white/10 rounded-2xl text-sm text-white outline-none placeholder:text-slate-600 focus:border-rose-500/50"
                  placeholder="Tenure (Months)"
                  required
                />
              </div>

              <div className="space-y-1">
                <div className="flex justify-between px-1">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Interest Rate (%)</label>
                  <span className="text-[10px] font-bold text-rose-300">{loanData.roi || 10}%</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="30"
                  step="0.1"
                  value={loanData.roi || 10}
                  onChange={e => setLoanData({...loanData, roi: e.target.value})}
                  className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-rose-500"
                />
              </div>
            </div>
          ) : (
            <>
              <div className="flex gap-2">
                <input
                  type="text"
                  inputMode="decimal"
                  value={wealthAmount}
                  onChange={(e) => {
                    const val = e.target.value;
                    if (val === "" || /^\d+(\.\d{0,2})?$/.test(val)) setWealthAmount(val);
                  }}
                  className="w-full flex-1 px-4 py-3 sm:py-4 bg-black/20 border border-white/10 rounded-2xl text-base text-white outline-none placeholder:text-slate-600 focus:border-blue-500/50 transition-colors"
                  placeholder="Amount (e.g. 1.5)"
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
                className="w-full px-4 py-3 sm:py-4 bg-black/20 border border-white/10 rounded-2xl text-base text-white outline-none placeholder:text-slate-600 focus:border-blue-500/50 transition-colors"
                placeholder={wealthType === 'asset' ? "Name (e.g. House, Gold)" : "Name (e.g. Credit Card, Friend)"}
                required
              />
            </>
          )}

          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-500 text-white py-3 sm:py-4 rounded-2xl font-bold shadow-lg shadow-blue-900/20 active:scale-95 transition-all mt-2"
          >
            Add {isLoan ? `${loanData.loanType.charAt(0).toUpperCase() + loanData.loanType.slice(1)} Loan` : 'Item'}
          </button>
        </form>
      </div>


      {/* List */}
      <div>
        <h3 className="text-xs sm:text-sm font-bold text-slate-500 uppercase tracking-widest mb-4 px-2">
          Your Portfolio
        </h3>
        {wealthItems.length === 0 ? (
          <p className="text-center text-slate-500 text-xs sm:text-sm py-8">
            No assets or liabilities added.
          </p>
        ) : (
          <div className="space-y-3">
            {wealthItems.map((item) => (
              <WealthItem
                key={item.id}
                item={item}
                onDelete={() => requestDeleteWealth(item)}
                onUpdate={executeUpdateWealth} // <--- ADD THIS LINE
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default WealthPage;
