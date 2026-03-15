//Database needed
// Section 6 Wealth Page
import React, { useState } from "react";
import { AreaChart, Area, Tooltip, ResponsiveContainer } from "recharts";
// import { db } from "../../../../../packages/shared/config/constants";
import { formatIndianCompact, buildAuthHeader } from "../../../../../packages/shared/utils/helpers";
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

  // --- 1. Calculate Live Net Worth ---
  const totalAssets = wealthItems
    .filter((i) => i.type === "asset")
    .reduce((acc, i) => acc + parseFloat(i.amount || i.value || 0), 0);
  const totalLiabilities = wealthItems
    .filter((i) => i.type === "liability")
    .reduce((acc, i) => acc + parseFloat(i.amount || i.value || 0), 0);
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
      const response = await apiFetch(`${apiBaseUrl}/wealth`, {
        method: "POST",
        body: JSON.stringify({
          title: data.title, // Correctly mapped
          amount: parseFloat(data.amount) * parseFloat(data.unit),
          type: data.type,
          category: "General",
        }),
      });

      setWealthName("");
      setWealthAmount("");
      showToast("Item added successfully!", "success");
      onSuccess(); // <--- CRITICAL: Refetches data from Django
    } catch (error) {
      showToast("Server error", "error");
    }
  };

  const requestAddWealth = (e) => {
    e.preventDefault();
    if (!wealthName || !wealthAmount || !user) return;

    // Create the data object HERE to pass to the trigger
    const newItem = {
      title: wealthName,
      amount: wealthAmount,
      type: wealthType,
      unit: wealthUnit,
    };

    triggerConfirm("Confirm adding this asset/liability?", () =>
      executeAddWealth(newItem),
    );
  };

  const executeDeleteWealth = async (id) => {
    try {
      // Correct URL format matching your Django urls.py
      await apiFetch(`${apiBaseUrl}/wealth/${id}`, {
        method: "DELETE",
      });

      showToast("Item removed", "success");
      onSuccess(); // <--- CRITICAL: Refetches data from Django
    } catch (e) {
      showToast("Failed to remove", "error");
    }
  };

  const requestDeleteWealth = (id) =>
    triggerConfirm("Remove this item?", () => executeDeleteWealth(id));

  // --- 3. Handlers ---

  // ADD THIS NEW HANDLER HERE
  const executeUpdateWealth = async (id, updatedData) => {
    try {
      await apiFetch(`${apiBaseUrl}/wealth/${id}`, {
        method: "PUT", // or "PATCH"
        body: JSON.stringify({
          title: updatedData.title,
          amount: updatedData.amount,
        }),
      });

      showToast("Item updated", "success");
      onSuccess(); // Refetch data to refresh the UI
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
          Add Asset / Liability
        </h3>

        <form
          onSubmit={requestAddWealth}
          className="flex flex-col gap-3 sm:gap-4"
        >
          {/* 1. Toggle Buttons */}
          <div className="flex bg-black/30 p-1 rounded-xl border border-white/5">
            <button
              type="button"
              onClick={() => setWealthType("asset")}
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

          {/* 2. Amount Row (Stacked) */}
          <div className="flex gap-2">
            <input
              type="text"
              inputMode="decimal"
              value={wealthAmount}
              onChange={(e) => {
                const val = e.target.value;
                // Allow only valid decimal numbers
                if (val === "" || /^\d+(\.\d{0,2})?$/.test(val)) {
                  setWealthAmount(val);
                }
              }}
              className="w-full flex-1 px-4 py-3 sm:py-4 bg-black/20 border border-white/10 rounded-2xl text-base text-white outline-none placeholder:text-slate-600 focus:border-blue-500/50 transition-colors"
              placeholder="Amount (e.g. 1.5)"
              required
            />
            <div className="shrink-0">
              <UnitSelector currentUnit={wealthUnit} onSelect={setWealthUnit} />
            </div>
          </div>

          {/* 3. Name Row (Stacked) */}
          <input
            type="text"
            value={wealthName}
            onChange={(e) => setWealthName(e.target.value)}
            className="w-full px-4 py-3 sm:py-4 bg-black/20 border border-white/10 rounded-2xl text-base text-white outline-none placeholder:text-slate-600 focus:border-blue-500/50 transition-colors"
            placeholder="Name (e.g. House, Car Loan)"
            required
          />

          {/* 4. Submit Button */}
          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-500 text-white py-3 sm:py-4 rounded-2xl font-bold shadow-lg shadow-blue-900/20 active:scale-95 transition-all mt-2"
          >
            Add Item
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
                onDelete={() => requestDeleteWealth(item.id)}
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
