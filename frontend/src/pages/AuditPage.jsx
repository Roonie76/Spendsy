import React, { useState, useEffect, useMemo } from "react";
import {
  Printer,
  Edit3,
  Target,
  Home as HomeIcon,
  AlertOctagon,
  ShieldAlert,
  Bot,
  Sparkles,
  X,
  CheckCircle2,
  Briefcase,
  Landmark,
  Activity,
  GraduationCap,
  Loader2,
  Clock,
  UserCog,
  Wand2,
  ArrowDownCircle,
  Scale,
  FileCheck,
  ArrowRight,
  RefreshCw,
  User,
} from "lucide-react";
import { TaxService } from "@shared/services/taxService";
import { AIService } from "@shared/services/aiService";
import { formatIndianCompact } from "@shared/utils/helpers";
import { TABS } from "@shared/config/constants";
import { apiFetch } from "../api";
import { GenericPageSkeleton } from "../components/ui/Skeletons";

// --- Sub-components ---
const DeductionBar = ({
  label,
  used,
  limit,
  color = "bg-blue-500",
  pace = 0,
}) => (
  <div className="mb-4 break-inside-avoid">
    <div className="flex justify-between text-xs mb-1">
      <span className="text-slate-300 font-medium print:text-black">
        {label}
      </span>
      <span className="text-slate-400 print:text-gray-600">
        {formatIndianCompact(used)} / {formatIndianCompact(limit)}
      </span>
    </div>
    <div className="h-2 w-full bg-black/40 rounded-full overflow-hidden border border-white/5 relative print:bg-gray-200 print:border-gray-300">
      <div
        className={`h-full ${color} rounded-full transition-all duration-500 print:bg-slate-800`}
        style={{ width: `${Math.min(100, (used / limit) * 100)}%` }}
      ></div>
      {pace > 0 && (
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-white/50 print:bg-black"
          style={{ left: `${Math.min(100, pace * 100)}%` }}
          title="Recommended Pace"
        ></div>
      )}
    </div>
  </div>
);

const TaxActionCard = ({ action, section, savings, deadline }) => (
  <div className="p-4 rounded-2xl bg-gradient-to-br from-emerald-900/40 to-emerald-800/20 border border-emerald-500/30 relative overflow-hidden group hover:border-emerald-500/50 transition-all print:border-gray-300 print:bg-white print:text-black break-inside-avoid">
    <div className="flex justify-between items-start mb-2">
      <span className="bg-emerald-500/20 text-emerald-300 text-[10px] font-bold px-2 py-0.5 rounded-md border border-emerald-500/30 uppercase print:bg-gray-100 print:text-black print:border-gray-300">
        {section}
      </span>
      <div className="flex items-center gap-1 text-[10px] text-emerald-200/70 print:text-slate-500">
        <Clock className="w-3 h-3" /> {deadline}
      </div>
    </div>
    <h4 className="font-bold text-white text-sm mb-1 print:text-black">
      {action}
    </h4>
    <p className="text-xs text-emerald-200/60 print:text-slate-600">
      Potential Savings:{" "}
      <span className="text-emerald-300 font-bold print:text-black">
        {savings}
      </span>
    </p>
  </div>
);

const ProfileWizard = ({
  isOpen,
  onClose,
  initialData,
  detectedValues,
  onSave,
}) => {
  const [localProfile, setLocalProfile] = useState(initialData);

  useEffect(() => {
    if (initialData) setLocalProfile(initialData);
  }, [initialData]);

  if (!isOpen) return null;

  const fields = [
    {
      label: "Annual Rent Paid",
      key: "annualRent",
      icon: HomeIcon,
      detected: detectedValues.rent,
    },
    {
      label: "Annual EPF",
      key: "annualEPF",
      icon: Briefcase,
      detected: detectedValues.epf,
    },
    {
      label: "NPS Contribution",
      key: "npsContribution",
      icon: Landmark,
      detected: detectedValues.nps,
    },
    {
      label: "Health Ins. (Self)",
      key: "healthInsuranceSelf",
      icon: Activity,
      detected: detectedValues.health,
    },
    {
      label: "Health Ins. (Parents)",
      key: "healthInsuranceParents",
      icon: Activity,
      detected: 0,
    },
    {
      label: "Home Loan Interest",
      key: "homeLoanInterest",
      icon: HomeIcon,
      detected: 0,
    },
    {
      label: "Edu Loan Interest",
      key: "educationLoanInterest",
      icon: GraduationCap,
      detected: 0,
    },
    {
      label: "Your Age",
      key: "age",
      icon: User,
      detected: 30,
    },
  ];

  const toggles = [
    { label: "I have Business Income", key: "isBusiness", sub: "Select if you earn apart from Salary" },
    { label: "I live in a Metro City", key: "isMetro", sub: "HRA is higher for Metro cities" },
    { label: "Parents are Senior Citizens", key: "parentsAreSenior", sub: "80D deduction limit increases to ₹50k" },
    { label: "I am an NRI", key: "isNRI", sub: "Non-Resident Indian status" },
    { label: "I have Foreign Assets", key: "foreignAssets", sub: "Required for Schedule FA" },
  ];

  return (
    <div className="fixed inset-0 bg-black/80 z-[60] flex items-center justify-center p-4 animate-in fade-in duration-200 print:hidden">
      <div className="bg-[#0f0c29] w-full max-w-xl p-6 rounded-[2rem] border border-white/10 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 bg-white/5 hover:bg-white/10 rounded-full text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
        <h3 className="text-xl font-bold text-white mb-6">
          Update Tax Profile
        </h3>
        <div className="space-y-6 max-h-[75vh] overflow-y-auto pr-2 custom-scrollbar">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {toggles.map((t) => (
              <div
                key={t.key}
                className="flex items-center gap-3 p-4 bg-white/5 rounded-2xl border border-white/10 cursor-pointer hover:bg-white/10 transition-colors"
                onClick={() =>
                  setLocalProfile({
                    ...localProfile,
                    [t.key]: !localProfile[t.key],
                  })
                }
              >
                <div
                  className={`shrink-0 w-5 h-5 rounded-md border flex items-center justify-center ${localProfile[t.key] ? "bg-blue-500 border-blue-500" : "border-slate-500"}`}
                >
                  {localProfile[t.key] && (
                    <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                  )}
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="text-xs font-bold text-white truncate">
                    {t.label}
                  </span>
                  <span className="text-[9px] text-slate-400 line-clamp-1">
                    {t.sub}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-4">
            {fields.map((field) => (
              <div key={field.key} className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                    <field.icon className="w-3 h-3" /> {field.label}
                  </label>
                  {field.detected > 0 && (
                    <button
                      type="button"
                      onClick={() =>
                        setLocalProfile({
                          ...localProfile,
                          [field.key]: Math.round(Number(field.detected) || 0),
                        })
                      }
                      className="text-[9px] font-bold text-cyan-300 bg-cyan-500/10 px-2 py-0.5 rounded flex items-center gap-1 hover:bg-cyan-500/20 active:scale-95 transition-transform"
                    >
                      <ArrowDownCircle className="w-3 h-3" /> Use Detected ₹
                      {formatIndianCompact(field.detected)}
                    </button>
                  )}
                </div>
                <input
                  type="number"
                  value={
                    !localProfile[field.key] || 
                    Number(localProfile[field.key]) === 0 
                      ? "" 
                      : localProfile[field.key]
                  }
                  onChange={(e) => {
                    const val = e.target.value === "" ? 0 : parseFloat(e.target.value);
                    setLocalProfile({
                      ...localProfile,
                      [field.key]: isNaN(val) ? 0 : Math.max(0, val),
                    });
                  }}
                  className="w-full px-4 py-3 bg-black/40 border border-white/10 rounded-xl text-white outline-none focus:border-blue-500/50 transition-colors placeholder:text-slate-600"
                  placeholder={
                    field.detected > 0 ? `Detected: ${field.detected}` : "Enter amount..."
                  }
                />
              </div>
            ))}
          </div>
        </div>
        <div className="pt-6 mt-2 border-t border-white/5">
          <button
            onClick={() => {
              onSave(localProfile);
              onClose();
            }}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white py-4 rounded-xl font-bold shadow-lg shadow-blue-900/20 transition-all"
          >
            Save Profile
          </button>
        </div>
      </div>
    </div>
  );
};

// --- Main AuditPage Component ---
const AuditPage = ({
  transactions,
  wealthItems,
  taxProfile,
  onUpdateProfile,
  showToast,
  settings,
  setActiveTab,
  user,
  apiBaseUrl,
  isLoading,
}) => {
  if (isLoading) return <GenericPageSkeleton />;
  const [adviceCards, setAdviceCards] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showWizard, setShowWizard] = useState(false);
  const [isRateLimited, setIsRateLimited] = useState(false);
  const [itrData, setItrData] = useState(null);

  // 1. Load cached advice on mount
  useEffect(() => {
    const cachedAdvice = localStorage.getItem("tax_audit_advice");
    if (cachedAdvice) {
      try {
        setAdviceCards(JSON.parse(cachedAdvice));
      } catch (e) {
        console.error("Failed to parse cached advice", e);
      }
    }
  }, []);

  // Fetch ITR data
  useEffect(() => {
    if (user?.id && apiBaseUrl) {
      apiFetch(`${apiBaseUrl}/itr-data/${user.id}`)
        .then((data) => setItrData(data))
        .catch((err) => console.error("Failed to fetch ITR data:", err));
    }
  }, [user?.id, apiBaseUrl]);

  const data = useMemo(() => {
    const results = TaxService.calculate(
      transactions,
      taxProfile,
      wealthItems,
      settings,
      itrData,
    );
    const isNewCheaper = results.taxNew <= results.taxOld;
    return {
      ...results,
      isNewCheaper,
      recommendedTaxable: isNewCheaper
        ? results.taxableNew
        : results.taxableOld,
      recommendedTax: isNewCheaper ? results.taxNew : results.taxOld,
    };
  }, [transactions, taxProfile, wealthItems, settings, itrData]);

  const detectedValues = useMemo(() => {
    const result = { rent: 0, epf: 0, health: 0, nps: 0 };
    transactions.forEach((t) => {
      const desc = (t.description || "").toLowerCase();
      const val = parseFloat(t.amount);
      if (t.type === "expense") {
        if (desc.includes("rent") && val > 1000) result.rent += val;
        if (
          desc.includes("ppf") ||
          desc.includes("lic") ||
          desc.includes("elss")
        )
          result.epf += val;
        if (
          (desc.includes("health") || desc.includes("mediclaim")) &&
          !desc.includes("lic")
        )
          result.health += val;
        if (desc.includes("nps")) result.nps += val;
      }
    });
    return result;
  }, [transactions]);

  const userPersona = useMemo(() => {
    const tags = [];
    const hasSalary = data.heads.salary > 0;
    const hasBusiness = taxProfile.isBusiness;
    if (hasSalary && hasBusiness) tags.push("Hybrid (Job + Business)");
    else if (hasBusiness) tags.push("Freelancer");
    else tags.push("Salaried Employee");
    if (data.sources.total > 1500000) tags.push("High Net Worth");
    return tags;
  }, [taxProfile, data]);

  const integrityScore = useMemo(() => {
    if (transactions.length === 0) return 100;
    const verifiedCount = transactions.filter(
      (t) => t.verificationStatus === "verified" || t.confidence > 0,
    ).length;
    return Math.round((verifiedCount / transactions.length) * 100);
  }, [transactions]);

  const integrityColor =
    integrityScore < 50
      ? "text-rose-400"
      : integrityScore < 80
        ? "text-amber-400"
        : "text-emerald-400";
  const integrityLabel =
    integrityScore < 50
      ? "High Audit Risk"
      : integrityScore < 80
        ? "Verification Needed"
        : "Audit Ready";

  // 2. Main AI Fetching Logic with 429 Error Handling
  const getAdvice = async () => {
    if (loading || isRateLimited) return;
    setLoading(true);

    try {
      const contextData = JSON.stringify({
        persona: userPersona.join(", "),
        regime: data.taxNew < data.taxOld ? "New Regime" : "Old Regime",
        income: {
          total: data.sources.total,
          salary: data.heads.salary,
          business: data.heads.business,
        },
        taxLiability: Math.min(data.taxNew, data.taxOld),
        unused80C: data.deductions.c80.limit - data.deductions.c80.used,
      });

      const systemPrompt = `Act as an Indian Tax CA. Generate 3 specific tax-saving actions for this persona based on Indian Income Tax laws (FY 2025-26). Output JSON array only: [{ "action": "...", "section": "...", "savings": "...", "deadline": "..." }]`;

      const result = await AIService.askForJSON(systemPrompt, contextData);
      setAdviceCards(result);
      localStorage.setItem("tax_audit_advice", JSON.stringify(result));
      setIsRateLimited(false);
    } catch (e) {
      console.error("Audit AI Error:", e);

      // Check for 429 specifically
      if (e.message?.includes("429") || e.toString().includes("429")) {
        setIsRateLimited(true);
        showToast("Rate limit reached (429). Please wait 60s.", "error");
        setTimeout(() => setIsRateLimited(false), 60000); // Reset after 1 min
      } else {
        showToast("AI Service Unavailable. Try again shortly.", "error");
      }
    } finally {
      setLoading(false);
    }
  };

  const clearAdvice = () => {
    localStorage.removeItem("tax_audit_advice");
    setAdviceCards([]);
    setIsRateLimited(false);
    showToast("AI Cache Cleared", "info");
  };

  return (
    <div className="space-y-6 pb-4 animate-in fade-in print:pb-0 print:text-black print:bg-white">
      {/* Header */}
      <div className="flex justify-between items-start print:hidden">
        <div>
          <h2 className="text-2xl font-bold text-white mb-2">Tax Audit</h2>
          <div className="flex flex-wrap gap-2">
            <span className="text-[10px] font-bold px-2 py-1 rounded-md bg-white/5 text-slate-400 border border-white/10 flex items-center gap-1">
              <Wand2 className="w-3 h-3" /> Analyzed {transactions.length}{" "}
              Transactions
            </span>
            {userPersona.map((tag) => (
              <span
                key={tag}
                className="text-[10px] font-bold px-2 py-1 rounded-md bg-blue-500/10 text-blue-200 border border-blue-500/20 flex items-center gap-1"
              >
                <UserCog className="w-3 h-3" /> {tag}
              </span>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => window.print()}
            className="p-2 bg-white/10 rounded-full hover:bg-white/20 text-slate-300 transition-colors"
          >
            <Printer className="w-5 h-5" />
          </button>
          <button
            onClick={() => setShowWizard(true)}
            className="p-2 bg-white/10 rounded-full hover:bg-white/20 text-white transition-colors"
          >
            <Edit3 className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Hero Card */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 p-1 rounded-[2rem] shadow-2xl print:hidden">
        <div className="bg-slate-900/50 backdrop-blur-md rounded-[1.8rem] p-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center text-white shadow-lg shadow-blue-500/40">
              <FileCheck className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Ready to File?</h3>
              <p className="text-xs text-blue-200">
                Your estimated tax is ₹{data.recommendedTax.toLocaleString()}.
                {data.isNewCheaper &&
                  ` Saving ₹${(data.taxOld - data.taxNew).toLocaleString()} with New Regime!`}
              </p>
            </div>
          </div>
          <button
            onClick={() => setActiveTab(TABS.ITR)}
            className="w-full md:w-auto px-6 py-3 bg-white text-blue-900 font-bold rounded-xl hover:bg-blue-50 transition-colors flex items-center justify-center gap-2 shadow-lg"
          >
            File ITR Now <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="bg-gradient-to-br from-indigo-900/40 to-blue-900/40 backdrop-blur-xl p-6 rounded-[2rem] border border-white/10 shadow-2xl relative overflow-hidden print:border print:border-gray-300 print:shadow-none print:bg-none print:text-black break-inside-avoid">
        <div className="relative z-10 grid grid-cols-2 gap-6">
          <div>
            <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1 print:text-gray-600">
              Taxable Income
            </p>
            <h3 className="text-2xl font-bold text-white print:text-black">
              ₹{data.recommendedTaxable.toLocaleString()}
            </h3>
            <p className="text-[10px] text-indigo-300 mt-1 print:text-gray-500">
              FY {data.fiscalYear}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1 print:text-gray-600">
              Recommended
            </p>
            <div
              className={`inline-block px-3 py-1 rounded-lg text-sm font-bold ${data.isNewCheaper ? "bg-emerald-500/20 text-emerald-300" : "bg-amber-500/20 text-amber-300"}`}
            >
              {data.isNewCheaper ? "NEW REGIME" : "OLD REGIME"}
            </div>
            <p className="text-[10px] text-slate-400 mt-1 print:text-gray-500">
              Est. Liability: ₹{data.recommendedTax.toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* AI Consultant Section */}
      <div className="bg-[#0f172a] p-6 rounded-[2rem] border border-white/10 relative overflow-hidden shadow-xl print:hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 blur-[80px] rounded-full pointer-events-none"></div>
        <div className="flex justify-between items-start mb-6 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Bot className="w-5 h-5 text-emerald-400" />
              <h3 className="font-bold text-white text-lg tracking-tight">
                AI Consultant
              </h3>
            </div>
            <p className="text-xs text-slate-400">
              Tailored for {userPersona[0]}
            </p>
          </div>
          <div className="flex gap-2">
            {adviceCards.length > 0 && !loading && (
              <button
                onClick={clearAdvice}
                className="p-2 bg-white/5 hover:bg-white/10 rounded-xl text-slate-400 hover:text-white transition-all border border-white/5"
                title="Clear cache"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={getAdvice}
              disabled={loading || isRateLimited}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-lg flex items-center gap-2 ${
                isRateLimited
                  ? "bg-rose-900/50 text-rose-300 cursor-not-allowed border border-rose-500/30"
                  : "bg-emerald-600 hover:bg-emerald-500 text-white"
              }`}
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Sparkles className="w-4 h-4" />
              )}
              {isRateLimited
                ? "Limit Reached"
                : loading
                  ? "Analyzing..."
                  : adviceCards.length > 0
                    ? "Update Advice"
                    : "Identify Savings"}
            </button>
          </div>
        </div>
        <div className="relative z-10 min-h-[50px]">
          {!loading && adviceCards.length === 0 && (
            <div className="text-center py-6 text-slate-500 text-xs border border-dashed border-slate-700 rounded-xl">
              {isRateLimited
                ? "API rate limit reached. Please wait a minute before retrying."
                : "Tap 'Identify Savings' to generate your report."}
            </div>
          )}
          {adviceCards.length > 0 && (
            <div className="grid gap-3 animate-in slide-in-from-bottom-4">
              {adviceCards.map((card, idx) => (
                <TaxActionCard key={idx} {...card} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Deductions & Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white/5 p-6 rounded-[2rem] border border-white/10 print:border-gray-300 print:bg-white print:text-black break-inside-avoid">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2 print:text-black">
            <Scale className="w-4 h-4" /> 5 Heads of Income
          </h3>
          <div className="space-y-3">
            {[
              { l: "1. Salary", v: data.heads.salary },
              { l: "2. House Property", v: data.heads.houseProperty },
              { l: "3. Business", v: data.heads.business },
              { l: "4. Capital Gains", v: data.heads.capitalGains, star: true },
              { l: "5. Other Sources", v: data.heads.other },
            ].map((item, i) => (
              <div key={i} className="flex justify-between text-sm">
                <span className="text-slate-300 print:text-gray-700">
                  {item.l}
                </span>
                <span className="text-white font-medium print:text-black">
                  ₹{item.v.toLocaleString()}
                  {item.star ? "*" : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-white/5 p-6 rounded-[2rem] border border-white/10 print:border-gray-300 print:bg-white print:text-black break-inside-avoid">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2 print:text-black">
            <Target className="w-4 h-4" /> Deductions (Old Regime)
          </h3>
          <DeductionBar
            label="80C Investments"
            used={data.deductions.c80.used}
            limit={150000}
            color="bg-cyan-500"
          />
          <DeductionBar
            label="80D Health Ins."
            used={data.deductions.d80.used}
            limit={75000}
            color="bg-pink-500"
          />
          <DeductionBar
            label="NPS (80CCD 1B)"
            used={data.deductions.nps.used}
            limit={50000}
            color="bg-purple-500"
          />
        </div>
      </div>

      {/* Integrity Score */}
      <div className="p-4 rounded-[1.5rem] bg-white/5 border border-white/10 flex flex-col gap-3 print:border-gray-300 print:bg-white print:text-black break-inside-avoid">
        <div className="flex justify-between items-start">
          <div className="flex items-start gap-3">
            <ShieldAlert
              className={`w-5 h-5 ${integrityScore < 80 ? "text-amber-500" : "text-emerald-500"} shrink-0 mt-0.5`}
            />
            <div>
              <h4 className="text-sm font-bold text-white mb-1 print:text-black">
                Data Integrity Score
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed print:text-gray-600">
                Based on verified vs. manual entries.
              </p>
            </div>
          </div>
          <div className="text-right">
            <h3
              className={`text-xl font-bold ${integrityColor} print:text-black`}
            >
              {integrityScore}%
            </h3>
            <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">
              {integrityLabel}
            </p>
          </div>
        </div>
        <div className="h-1.5 w-full bg-black/40 rounded-full overflow-hidden flex print:bg-gray-200">
          <div
            className="h-full bg-emerald-500 print:bg-black"
            style={{ width: `${integrityScore}%` }}
          ></div>
        </div>
      </div>

      <div className="text-center pt-8 pb-8 border-t border-white/5 print:border-black mt-8">
        <p className="text-[10px] text-slate-600 print:text-gray-500 uppercase font-bold">
          Disclaimer: Report based on estimated data for educational purposes
          only.
        </p>
      </div>

      <ProfileWizard
        isOpen={showWizard}
        onClose={() => setShowWizard(false)}
        initialData={taxProfile}
        detectedValues={detectedValues}
        onSave={onUpdateProfile}
      />
    </div>
  );
};

export default AuditPage;
