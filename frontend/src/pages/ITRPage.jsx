import React, { useState, useEffect, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Wallet, ShieldCheck, Scale, FileText, Send, ChevronRight, ChevronLeft,
  CheckCircle2, Info, AlertCircle, TrendingUp, Save, BarChart3, Calculator,
  Building2, Briefcase, Landmark, PiggyBank, Receipt, Search, Lightbulb,
  Calendar, AlertTriangle, ArrowRight, ArrowDown, ArrowUp, Eye, EyeOff,
  ChevronDown, ChevronUp, Shield, Target, Zap, HelpCircle, X,
  IndianRupee, Home, CircleDollarSign, Banknote, Percent, Clock,
  BadgeCheck, TriangleAlert, Star, Sparkles, BookOpen, FileWarning, Plus,
} from "lucide-react";
import { TAX_CONSTANTS } from "@shared/config/constants";
import { TaxService, getITRFormType } from "@shared/services/taxService";
import { apiFetch } from "../api";

// ─── CONSTANTS ────────────────────────────────────────────────────────────────

const getDynamicYears = () => {
  const now = new Date();
  let currentYear = now.getFullYear();
  if (now.getMonth() < 3) {
    currentYear -= 1;
  }
  return {
    FY: `${currentYear}-${String(currentYear + 1).slice(-2)}`,
    AY: `${currentYear + 1}-${String(currentYear + 2).slice(-2)}`,
    ADV_YR: currentYear
  };
};

const { FY, AY, ADV_YR } = getDynamicYears();

const DEDUCTION_CATALOG = [
  { section: "80C", label: "PPF / ELSS / LIC / Tuition / EPF / NSC / SCSS / 5yr FD / Home Loan Principal / Stamp Duty", limit: 150000, key: "section80C", regimes: ["old"], icon: PiggyBank },
  { section: "80CCD(1B)", label: "NPS Additional Contribution", limit: 50000, key: "nps80CCD", regimes: ["old"], icon: Landmark },
  { section: "80CCD(2)", label: "Employer NPS Contribution", limit: null, key: "employer_nps", regimes: ["old", "new"], icon: Building2, note: "10% of salary (14% for govt)" },
  { section: "80D", label: "Health Insurance Premium (Self + Family)", limit: 25000, key: "section80D", regimes: ["old"], icon: Shield, note: "₹50K if senior citizen" },
  { section: "80D Parents", label: "Health Insurance Premium (Parents)", limit: 25000, key: "section80D_parents", regimes: ["old"], icon: Shield, note: "₹50K if senior citizen" },
  { section: "80E", label: "Education Loan Interest", limit: null, key: "section80E", regimes: ["old"], icon: BookOpen, note: "No limit, max 8 years" },
  { section: "80EE", label: "Home Loan Interest (First-time, FY16-17)", limit: 50000, key: "section80EE", regimes: ["old"], icon: Home },
  { section: "80EEB", label: "Electric Vehicle Loan Interest", limit: 150000, key: "section80EEB", regimes: ["old"], icon: Zap },
  { section: "80G", label: "Donations to Charitable Orgs", limit: null, key: "section80G", regimes: ["old"], icon: Star, note: "50% or 100% deduction" },
  { section: "80GG", label: "Rent Paid (No HRA received)", limit: 60000, key: "section80GG", regimes: ["old"], icon: Home, note: "Max ₹5K/month" },
  { section: "80TTA", label: "Savings Account Interest", limit: 10000, key: "section80TTA", regimes: ["old"], icon: Banknote, note: "₹50K for seniors (80TTB)" },
  { section: "80U", label: "Person with Disability", limit: 75000, key: "section80U", regimes: ["old"], icon: Shield, note: "₹1.25L for severe disability" },
  { section: "24(b)", label: "Home Loan Interest (Self-Occupied)", limit: 200000, key: "homeLoanInterest", regimes: ["old"], icon: Home },
  { section: "HRA", label: "House Rent Allowance", limit: null, key: "hra", regimes: ["old"], icon: Home, note: "Least of actual HRA, 50%/40% salary, rent - 10% salary" },
];

const CAPITAL_GAIN_TYPES = [
  { key: "listed_equity_stcg", label: "Listed Equity (STCG ≤12m)", rate: "20%", period: "≤ 12 months", section: "111A" },
  { key: "listed_equity_ltcg", label: "Listed Equity (LTCG >12m)", rate: "12.5%", period: "> 12 months", section: "112A", exempt: 125000 },
  { key: "equity_mf_stcg", label: "Equity Mutual Funds (STCG)", rate: "20%", period: "≤ 12 months", section: "111A" },
  { key: "equity_mf_ltcg", label: "Equity Mutual Funds (LTCG)", rate: "12.5%", period: "> 12 months", section: "112A", exempt: 125000 },
  { key: "debt_mf_stcg", label: "Debt Mutual Funds (STCG)", rate: "Slab", period: "≤ 24 months" },
  { key: "debt_mf_ltcg", label: "Debt Mutual Funds (LTCG)", rate: "12.5%", period: "> 24 months" },
  { key: "property_stcg", label: "Real Estate (STCG)", rate: "Slab", period: "≤ 24 months" },
  { key: "property_ltcg", label: "Real Estate (LTCG)", rate: "12.5%", period: "> 24 months", note: "Transitional relief for pre-23-Jul-2024" },
  { key: "gold_stcg", label: "Gold / Jewellery (STCG)", rate: "Slab", period: "≤ 24 months" },
  { key: "gold_ltcg", label: "Gold / Jewellery (LTCG)", rate: "12.5%", period: "> 24 months" },
  { key: "crypto_vda", label: "Crypto / VDA", rate: "30%", period: "Any", section: "115BBH", note: "No set-off, no carry forward" },
  { key: "unlisted_stcg", label: "Unlisted Shares (STCG)", rate: "Slab", period: "≤ 24 months" },
  { key: "unlisted_ltcg", label: "Unlisted Shares (LTCG)", rate: "12.5%", period: "> 24 months" },
];

const SALARY_COMPONENTS = [
  { key: "basic", label: "Basic Salary", taxable: true, help: "Fully taxable" },
  { key: "da", label: "Dearness Allowance", taxable: true, help: "Fully taxable, part of salary for PF/gratuity" },
  { key: "hra_received", label: "HRA Received", taxable: false, help: "Exempt under Section 10(13A) with conditions" },
  { key: "lta", label: "Leave Travel Allowance", taxable: false, help: "Exempt for 2 journeys in block of 4 years" },
  { key: "special_allowance", label: "Special Allowance", taxable: true, help: "Fully taxable" },
  { key: "bonus", label: "Bonus / Ex-gratia", taxable: true, help: "Fully taxable" },
  { key: "commission", label: "Commission", taxable: true, help: "Fully taxable" },
  { key: "epf_employer", label: "Employer EPF Contribution", taxable: false, help: "Exempt up to 12% of salary" },
  { key: "nps_employer", label: "Employer NPS (80CCD(2))", taxable: false, help: "Exempt up to 10%/14% of salary" },
  { key: "professional_tax", label: "Professional Tax Paid", taxable: false, help: "Deductible, max ₹2,500" },
  { key: "perquisites", label: "Perquisites (Section 17(2))", taxable: true, help: "Rent-free accommodation, car, ESOP, gifts etc." },
  { key: "gratuity", label: "Gratuity", taxable: false, help: "Govt: fully exempt. Others: up to ₹20L" },
  { key: "leave_encashment", label: "Leave Encashment", taxable: false, help: "Govt: fully exempt. Others: up to ₹25L" },
];

const HOUSE_PROPERTY_FIELDS = [
  { key: "property_type", label: "Property Type", type: "select", options: ["self_occupied", "let_out", "deemed_let_out"] },
  { key: "annual_rent", label: "Annual Rent Received", type: "currency", condition: (d) => d.property_type !== "self_occupied" },
  { key: "municipal_tax", label: "Municipal Tax Paid", type: "currency", condition: (d) => d.property_type !== "self_occupied" },
  { key: "vacancy_months", label: "Vacancy Period (Months)", type: "number", condition: (d) => d.property_type === "let_out" },
  { key: "loan_interest", label: "Home Loan Interest (Annual)", type: "currency" },
  { key: "loan_principal", label: "Home Loan Principal Repaid", type: "currency" },
  { key: "loan_sanction_date", label: "Loan Sanction Date", type: "date" },
  { key: "construction_complete_date", label: "Construction Completion Date", type: "date", condition: (d) => d.property_type === "self_occupied" },
  { key: "co_owner_pct", label: "Co-ownership %", type: "number" },
  { key: "is_metro", label: "Metro City (for HRA)", type: "toggle" },
];

const ADVANCE_TAX_SCHEDULE = [
  { installment: "1st", due: `June 15`, cumPct: 15 },
  { installment: "2nd", due: `September 15`, cumPct: 45 },
  { installment: "3rd", due: `December 15`, cumPct: 75 },
  { installment: "4th", due: `March 15`, cumPct: 100 },
];

const TAX_CALENDAR = [
  { month: "Apr", action: "Set up investment plan for the year", icon: Target },
  { month: "Jun 15", action: "Advance Tax — 1st Installment (15%)", icon: Calendar, type: "deadline" },
  { month: "Jul 31", action: "ITR Filing Deadline (non-audit)", icon: FileText, type: "critical" },
  { month: "Sep 15", action: "Advance Tax — 2nd Installment (45%)", icon: Calendar, type: "deadline" },
  { month: "Sep 30", action: "Tax Audit Report Due", icon: Shield, type: "deadline" },
  { month: "Oct 31", action: "ITR Due (audit cases)", icon: FileText, type: "deadline" },
  { month: "Dec 15", action: "Advance Tax — 3rd Installment (75%)", icon: Calendar, type: "deadline" },
  { month: "Jan", action: "Review AIS — catch mismatches early", icon: Search },
  { month: "Feb", action: "Tax-loss harvesting window", icon: TrendingUp },
  { month: "Mar 15", action: "Advance Tax — Final Installment", icon: Calendar, type: "critical" },
  { month: "Mar 31", action: "Last date for 80C/80D investments", icon: Clock, type: "critical" },
  { month: "Dec 31", action: "Belated/Revised return deadline", icon: FileWarning, type: "deadline" },
];

// ─── HELPERS ──────────────────────────────────────────────────────────────────

const fmt = (amount) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount || 0);
const fmtNum = (n) => new Intl.NumberFormat("en-IN").format(n || 0);
const pct = (a, b) => b > 0 ? ((a / b) * 100).toFixed(1) : "0.0";

const InfoTooltip = ({ text }) => (
  <div className="group relative inline-block ml-1.5 align-middle">
    <HelpCircle className="w-3.5 h-3.5 text-slate-500 cursor-help hover:text-blue-400 transition-colors" />
    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 p-2.5 bg-slate-800 text-[10px] text-slate-200 rounded-xl opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity shadow-xl border border-white/10 z-50 leading-relaxed">
      {text}
      <div className="absolute top-full left-1/2 -translate-x-1/2 border-6 border-transparent border-t-slate-800" />
    </div>
  </div>
);

const CurrencyInput = ({ value, onChange, placeholder = "Enter amount...", label, help, compact, disabled }) => (
  <div className={`group transition-all ${compact ? "" : "space-y-1.5"}`}>
    {label && (
      <div className="flex items-center gap-1 text-[10px] text-slate-500 font-bold uppercase tracking-wider ml-1 group-focus-within:text-blue-400">
        {label} {help && <InfoTooltip text={help} />}
      </div>
    )}
    <div className="relative">
      <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500 font-medium text-sm">₹</span>
      <input
        type="text" inputMode="decimal" 
        value={(!value || Number(value) === 0) ? "" : value} 
        disabled={disabled}
        onChange={(e) => {
          const val = e.target.value;
          if (val === "" || /^\d+(\.\d{0,2})?$/.test(val)) onChange(val);
        }}
        className={`w-full bg-black/20 border border-white/10 rounded-xl ${compact ? "py-2.5 pl-8 pr-3 text-sm" : "py-3.5 pl-9 pr-4"} text-white focus:border-blue-500/50 outline-none transition-all shadow-inner disabled:opacity-40`}
        placeholder={placeholder}
      />
    </div>
  </div>
);

const StatCard = ({ label, value, subtitle, icon: Icon, color = "blue", trend, className = "" }) => (
  <motion.div
    whileHover={{ y: -2, scale: 1.01 }}
    className={`relative overflow-hidden rounded-2xl p-5 border border-white/10 bg-white/[0.04] backdrop-blur-xl ${className}`}
  >
    <div className="flex items-start justify-between mb-3">
      <div className={`p-2 rounded-xl bg-${color}-500/15`}>
        {Icon && <Icon className={`w-4 h-4 text-${color}-400`} />}
      </div>
      {trend && (
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${trend > 0 ? "bg-emerald-500/15 text-emerald-400" : "bg-rose-500/15 text-rose-400"}`}>
          {trend > 0 ? "↑" : "↓"} {Math.abs(trend)}%
        </span>
      )}
    </div>
    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">{label}</p>
    <p className="text-xl font-black text-white tracking-tight">{value}</p>
    {subtitle && <p className="text-[10px] text-slate-500 mt-1">{subtitle}</p>}
  </motion.div>
);

const SectionHeader = ({ icon: Icon, title, subtitle, badge }) => (
  <div className="flex items-center justify-between mb-6">
    <div className="flex items-center gap-3">
      {Icon && <div className="p-2 rounded-xl bg-blue-500/10"><Icon className="w-4 h-4 text-blue-400" /></div>}
      <div>
        <h3 className="text-sm font-bold text-white uppercase tracking-wider">{title}</h3>
        {subtitle && <p className="text-[10px] text-slate-500">{subtitle}</p>}
      </div>
    </div>
    {badge && <span className="text-[9px] font-black px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 uppercase tracking-wider">{badge}</span>}
  </div>
);

const AlertBox = ({ type = "info", children }) => {
  const styles = {
    info: "bg-blue-500/10 border-blue-500/20 text-blue-200",
    warning: "bg-amber-500/10 border-amber-500/20 text-amber-200",
    error: "bg-rose-500/10 border-rose-500/20 text-rose-200",
    success: "bg-emerald-500/10 border-emerald-500/20 text-emerald-200",
  };
  const icons = { info: Info, warning: AlertTriangle, error: AlertCircle, success: CheckCircle2 };
  const Icon = icons[type];
  return (
    <div className={`flex gap-3 items-start p-4 rounded-2xl border ${styles[type]}`}>
      <Icon className="w-4 h-4 shrink-0 mt-0.5" />
      <div className="text-[11px] leading-relaxed font-medium">{children}</div>
    </div>
  );
};

const ProgressBar = ({ value, max, color = "blue" }) => (
  <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
    <motion.div
      initial={{ width: 0 }}
      animate={{ width: `${Math.min(100, (value / max) * 100)}%` }}
      className={`h-full bg-${color}-500 rounded-full`}
      transition={{ duration: 0.8, ease: "easeOut" }}
    />
  </div>
);

// ─── TAX COMPUTATION ENGINE (Enhanced) ────────────────────────────────────────

function computeFullTax(incomeData, deductionsData, regime = "new") {
  const salary = parseFloat(incomeData.salary || 0);
  const hp = parseFloat(incomeData.houseProperty || 0);
  const business = parseFloat(incomeData.businessIncome || 0);
  const capitalGains = parseFloat(incomeData.capitalGains || 0);
  const other = parseFloat(incomeData.otherIncome || 0) + parseFloat(incomeData.interestIncome || 0);

  // Sync capital gains from details if available
  const cgDetail = incomeData.capital_gains_detail || {};
  const cgSum = Object.values(cgDetail).reduce((sum, v) => sum + (parseFloat(v) || 0), 0);
  const actualCG = cgSum > 0 ? cgSum : capitalGains;

  // Salary components
  const salaryComponents = incomeData.salary_components || {};
  let totalGrossSalary = salary; // Total for display (GTI)
  let taxableSalary = salary;     // Total for tax base

  if (Object.keys(salaryComponents).length > 0) {
    const componentEntries = Object.entries(salaryComponents);
    
    totalGrossSalary = componentEntries.reduce((sum, [_, val]) => sum + (parseFloat(val) || 0), 0);
    
    taxableSalary = componentEntries.reduce((sum, [key, val]) => {
      const comp = SALARY_COMPONENTS.find(c => c.key === key);
      if (comp && comp.taxable) return sum + (parseFloat(val) || 0);
      return sum;
    }, 0);

    if (totalGrossSalary === 0) totalGrossSalary = salary;
    if (taxableSalary === 0) taxableSalary = salary;
  }

  // House property income computation
  const properties = incomeData.properties || [];
  let totalHP = hp;
  if (properties.length > 0) {
    totalHP = properties.reduce((sum, p) => {
      if (p.property_type === "self_occupied") {
        const interest = Math.min(parseFloat(p.loan_interest || 0), 200000);
        return sum - interest;
      } else {
        const rent = parseFloat(p.annual_rent || 0);
        const municipal = parseFloat(p.municipal_tax || 0);
        const nav = rent - municipal;
        const stdDeduction = nav * 0.3;
        const interest = parseFloat(p.loan_interest || 0);
        return sum + nav - stdDeduction - interest;
      }
    }, 0);
    totalHP = Math.max(totalHP, -200000); // Loss capped at ₹2L
  }

  const displayGrossTotalIncome = totalGrossSalary + totalHP + business + other;
  
  // New regime: Loss from house property cannot be set off against other heads
  const taxableGrossTotalIncome = regime === "new" 
    ? taxableSalary + Math.max(0, totalHP) + business + other
    : taxableSalary + totalHP + business + other;

  const stdDeduction = regime === "new" ? 75000 : 50000;

  let totalDeductions = stdDeduction;
  if (regime === "new") {
    // New regime allows 80CCD(2) employer contribution
    totalDeductions += parseFloat(deductionsData.employer_nps || 0);
  }

  if (regime === "old") {
    const limits = TAX_CONSTANTS.LIMITS;
    totalDeductions += Math.min(parseFloat(deductionsData.section80C || 0), limits.SECTION_80C);
    totalDeductions += Math.min(parseFloat(deductionsData.nps80CCD || 0), limits.SEC_80CCD_1B);
    totalDeductions += Math.min(parseFloat(deductionsData.section80D || 0), limits.SECTION_80D_SELF);
    totalDeductions += Math.min(parseFloat(deductionsData.section80D_parents || 0), limits.SECTION_80D_PARENTS);
    totalDeductions += parseFloat(deductionsData.section80E || 0);
    totalDeductions += Math.min(parseFloat(deductionsData.section80EE || 0), limits.SECTION_80EE);
    totalDeductions += Math.min(parseFloat(deductionsData.section80EEB || 0), limits.SECTION_80EEB);
    totalDeductions += parseFloat(deductionsData.section80G || 0);
    totalDeductions += Math.min(parseFloat(deductionsData.section80GG || 0), limits.SECTION_80GG_MONTHLY * 12);
    totalDeductions += Math.min(parseFloat(deductionsData.section80TTA || 0), limits.SECTION_80TTA);
    totalDeductions += Math.min(parseFloat(deductionsData.section80U || 0), 75000);
    totalDeductions += Math.min(parseFloat(deductionsData.homeLoanInterest || 0), limits.SECTION_24B_SOP);
    totalDeductions += parseFloat(deductionsData.hra || 0);
  }

  const taxableIncome = Math.max(0, taxableGrossTotalIncome - totalDeductions);

  // Slab computation
  const slabs = regime === "new" ? TAX_CONSTANTS.NEW_REGIME.SLABS : TAX_CONSTANTS.OLD_REGIME.SLABS;
  const regimeConst = regime === "new" ? TAX_CONSTANTS.NEW_REGIME : TAX_CONSTANTS.OLD_REGIME;

  let baseTax = 0, prev = 0;
  for (const { limit, rate } of slabs) {
    const upper = limit ?? Infinity;
    if (taxableIncome > prev) baseTax += Math.min(taxableIncome - prev, upper - prev) * rate;
    prev = upper;
    if (taxableIncome <= upper) break;
  }

  // Rebate u/s 87A
  if (regime === "new") {
    if (taxableIncome <= regimeConst.REBATE_LIMIT) baseTax = 0;
    else if (taxableIncome <= regimeConst.REBATE_LIMIT + regimeConst.REBATE_MAX) {
      baseTax = Math.min(baseTax, taxableIncome - regimeConst.REBATE_LIMIT);
    }
  } else {
    if (taxableIncome <= regimeConst.REBATE_LIMIT) baseTax = 0;
  }

  // Surcharge
  let surchargeRate = 0;
  const maxSurchargeRate = regimeConst.MAX_SURCHARGE_RATE;
  for (const { threshold, rate } of TAX_CONSTANTS.SURCHARGE) {
    if (taxableIncome > threshold && rate <= maxSurchargeRate) surchargeRate = rate;
  }
  const surcharge = baseTax * surchargeRate;

  // Marginal relief
  let effectiveSurcharge = surcharge;
  if (surchargeRate > 0) {
    const applicableThreshold = [...TAX_CONSTANTS.SURCHARGE]
      .filter(b => taxableIncome > b.threshold && b.rate <= maxSurchargeRate)
      .pop()?.threshold;
    if (applicableThreshold) {
      let taxAtThreshold = 0, p2 = 0;
      for (const { limit, rate } of slabs) {
        const upper = limit ?? Infinity;
        if (applicableThreshold > p2) taxAtThreshold += Math.min(applicableThreshold - p2, upper - p2) * rate;
        p2 = upper;
        if (applicableThreshold <= upper) break;
      }
      const marginalExcess = taxableIncome - applicableThreshold;
      if ((baseTax + surcharge) - taxAtThreshold > marginalExcess) {
        effectiveSurcharge = Math.max(0, taxAtThreshold + marginalExcess - baseTax);
      }
    }
  }

  const cess = (baseTax + effectiveSurcharge) * regimeConst.CESS;

  // Capital gains tax (separate computation at special rates)
  let cgTax = 0;
  const cg = incomeData.capital_gains_detail || {};
  const listed_stcg = parseFloat(cg.listed_equity_stcg || 0) + parseFloat(cg.equity_mf_stcg || 0);
  const listed_ltcg = parseFloat(cg.listed_equity_ltcg || 0) + parseFloat(cg.equity_mf_ltcg || 0);
  const crypto = parseFloat(cg.crypto_vda || 0);

  if (listed_stcg > 0) cgTax += listed_stcg * TAX_CONSTANTS.CAPITAL_GAINS.STCG_111A;
  if (listed_ltcg > TAX_CONSTANTS.CAPITAL_GAINS.LTCG_112A_EXEMPT) {
    cgTax += (listed_ltcg - TAX_CONSTANTS.CAPITAL_GAINS.LTCG_112A_EXEMPT) * TAX_CONSTANTS.CAPITAL_GAINS.LTCG_112A;
  }
  if (crypto > 0) cgTax += crypto * TAX_CONSTANTS.CAPITAL_GAINS.CRYPTO_VDA;

  // Slab-rate CG (debt MF, property, gold, unlisted)
  const slabCG = parseFloat(cg.debt_mf_stcg || 0) + parseFloat(cg.property_stcg || 0) + parseFloat(cg.gold_stcg || 0) + parseFloat(cg.unlisted_stcg || 0);
  // LTCG at 12.5% for non-equity
  const flatLTCG = parseFloat(cg.debt_mf_ltcg || 0) + parseFloat(cg.property_ltcg || 0) + parseFloat(cg.gold_ltcg || 0) + parseFloat(cg.unlisted_ltcg || 0);
  if (flatLTCG > 0) cgTax += flatLTCG * 0.125;

  const cgCess = cgTax * TAX_CONSTANTS.NEW_REGIME.CESS;
  const totalCGTax = cgTax + cgCess;

  const totalTax = baseTax + effectiveSurcharge + cess + totalCGTax;

  return {
    grossSalary: totalGrossSalary,
    grossTotalIncome: displayGrossTotalIncome + actualCG,
    totalDeductions,
    taxableIncome,
    baseTax,
    surcharge: effectiveSurcharge,
    surchargeRate,
    cess,
    capitalGainsTax: totalCGTax,
    slabCGIncome: slabCG,
    totalTax,
    regime,
  };
}

// ─── ITR FORM SELECTOR (Enhanced Decision Tree) ──────────────────────────────

function determineITRForm(income, profile = {}) {
  const salary = parseFloat(income.salary || 0);
  const hp = parseFloat(income.houseProperty || 0);
  const business = parseFloat(income.businessIncome || 0);
  const cg = parseFloat(income.capitalGains || 0);
  const other = parseFloat(income.otherIncome || 0) + parseFloat(income.interestIncome || 0);
  const total = salary + Math.abs(hp) + business + cg + other;
  const properties = income.properties || [];
  const cgDetail = income.capital_gains_detail || {};

  if (profile.entityType === "company") return { form: "ITR-6", name: "Company", reason: "Companies must file ITR-6" };
  if (profile.entityType === "trust") return { form: "ITR-7", name: "Trust/Institution", reason: "Trusts file ITR-7" };
  if (profile.entityType === "firm" || profile.entityType === "llp") return { form: "ITR-5", name: "Firm/LLP", reason: "Firms and LLPs file ITR-5" };

  const hasBusiness = business > 0;
  const hasCapitalGains = cg > 0 || Object.values(cgDetail).some(v => parseFloat(v) > 0);
  const hasCrypto = parseFloat(cgDetail.crypto_vda || 0) > 0;
  const hasForeignAssets = !!profile.foreignAssets;
  const isDirector = !!profile.isDirector;
  const hasMultipleHP = properties.length > 1;
  const hasUnlistedEquity = !!profile.hasUnlistedEquity;
  const agriIncome = parseFloat(income.agriculturalIncome || 0);

  if (hasBusiness) {
    if (profile.isPresumptive && total <= 5000000 && !hasCapitalGains && !hasForeignAssets) {
      return { form: "ITR-4", name: "Sugam", reason: "Presumptive business/profession u/s 44AD/44ADA, total income ≤ ₹50L" };
    }
    return { form: "ITR-3", name: "Business & Profession", reason: "Non-presumptive business income or income exceeds ₹50L" };
  }

  if (hasCapitalGains || hasCrypto) return { form: "ITR-2", name: "Capital Gains", reason: hasCapitalGains ? "Capital gains income present" : "Crypto/VDA income present (Section 115BBH)" };
  if (total > 5000000) return { form: "ITR-2", name: "Income > ₹50L", reason: "Total income exceeds ₹50 Lakh threshold for ITR-1" };
  if (hasForeignAssets) return { form: "ITR-2", name: "Foreign Assets", reason: "Foreign assets/income require ITR-2 (Schedule FA)" };
  if (isDirector) return { form: "ITR-2", name: "Director", reason: "Director of a company must file ITR-2" };
  if (hasMultipleHP) return { form: "ITR-2", name: "Multiple Properties", reason: "Income from more than 1 house property" };
  if (hasUnlistedEquity) return { form: "ITR-2", name: "Unlisted Equity", reason: "Unlisted equity investments require ITR-2" };
  if (agriIncome > 5000) return { form: "ITR-2", name: "Agricultural Income", reason: "Agricultural income > ₹5,000" };

  return { form: "ITR-1", name: "Sahaj", reason: "Salaried individual with income ≤ ₹50L, single house property" };
}

// ─── AUDIT CHECKS ENGINE ─────────────────────────────────────────────────────

function runAuditChecks(incomeData, deductionsData, filingDetails) {
  const errors = [];
  const warnings = [];

  // PAN validation
  const pan = filingDetails.panNumber || "";
  if (pan && !/^[A-Z]{5}[0-9]{4}[A-Z]$/.test(pan)) {
    errors.push({ id: "pan", msg: "Invalid PAN format (must be ABCDE1234F)", section: "Filing" });
  }

  // 80C limit
  const total80C = parseFloat(deductionsData.section80C || 0);
  if (total80C > 150000) {
    errors.push({ id: "80c_limit", msg: `80C deductions exceed ₹1,50,000 limit (claimed: ${fmt(total80C)})`, section: "Deductions" });
  }

  // HRA + 80GG conflict
  if (parseFloat(deductionsData.hra || 0) > 0 && parseFloat(deductionsData.section80GG || 0) > 0) {
    errors.push({ id: "hra_80gg", msg: "Cannot claim both HRA exemption and 80GG deduction simultaneously", section: "Deductions" });
  }

  // Crypto loss warning
  const cgDetail = incomeData.capital_gains_detail || {};
  const cgSum = Object.values(cgDetail).reduce((sum, v) => sum + (parseFloat(v) || 0), 0);
  
  if (parseFloat(cgDetail.crypto_vda || 0) < 0) {
    warnings.push({ id: "crypto_loss", msg: "Crypto losses cannot be set off against any other income or carried forward", section: "Capital Gains" });
  }

  // Missing bank details
  if (!filingDetails.bankAccount && !filingDetails.ifscCode) {
    warnings.push({ id: "bank_missing", msg: "Bank account details needed for refund processing", section: "Filing" });
  }

  // Advance tax check
  const grossIncome = parseFloat(incomeData.salary || 0) + parseFloat(incomeData.businessIncome || 0) + parseFloat(incomeData.otherIncome || 0);
  if (grossIncome > 1000000 && !filingDetails.advanceTaxPaid) {
    warnings.push({ id: "advance_tax", msg: "With income above ₹10L, advance tax may be applicable. Check Section 234B/234C interest.", section: "Compliance" });
  }

  // Capital Gains consistency check
  const declaredCG = parseFloat(incomeData.capitalGains || 0);
  if (cgSum > 0 && Math.abs(cgSum - declaredCG) > 10) {
    errors.push({ 
      id: "cg_mismatch", 
      msg: `Capital Gains mismatch: Schedule shows ${fmt(cgSum)} but Income head shows ${fmt(declaredCG)}. Please sync them.`, 
      section: "Capital Gains" 
    });
  }

  // Missing income declaration
  if (parseFloat(incomeData.interestIncome || 0) === 0) {
    warnings.push({ id: "interest_missing", msg: "No savings/FD interest declared. Verify with bank statements — even small amounts should be reported.", section: "Income" });
  }

  // Due date warning
  const today = new Date();
  const julyDeadline = new Date(today.getFullYear(), 6, 31);
  if (today > julyDeadline) {
    warnings.push({ id: "late_filing", msg: `Filing after July 31 — late fee u/s 234F applies (₹5,000 or ₹1,000 if income ≤ ₹5L)`, section: "Compliance" });
  }

  return { errors, warnings };
}

// ─── RECOMMENDATION ENGINE ───────────────────────────────────────────────────

function generateRecommendations(incomeData, deductionsData, taxResults) {
  const tips = [];
  const limits = TAX_CONSTANTS.LIMITS;

  const used80C = parseFloat(deductionsData.section80C || 0);
  const remaining80C = Math.max(0, limits.SECTION_80C - used80C);
  if (remaining80C > 0) {
    const saving = remaining80C * 0.3;
    tips.push({
      priority: "high",
      title: `Invest ₹${fmtNum(remaining80C)} more under 80C`,
      desc: `You have room for ${fmt(remaining80C)} more in PPF/ELSS/LIC → potential savings of ${fmt(saving)}`,
      saving,
      icon: PiggyBank,
    });
  }

  const usedNPS = parseFloat(deductionsData.nps80CCD || 0);
  const remainingNPS = Math.max(0, limits.SEC_80CCD_1B - usedNPS);
  if (remainingNPS > 0) {
    const saving = remainingNPS * 0.3;
    tips.push({
      priority: "high",
      title: `Add ₹${fmtNum(remainingNPS)} to NPS (80CCD(1B))`,
      desc: `Additional NPS contribution beyond 80C limit → save ${fmt(saving)} in taxes`,
      saving,
      icon: Landmark,
    });
  }

  const used80D = parseFloat(deductionsData.section80D || 0);
  if (used80D === 0) {
    tips.push({
      priority: "critical",
      title: "Get Health Insurance → Save up to ₹25,000 under 80D",
      desc: "No health insurance premium claimed. Self + family: ₹25K. Add parents: ₹25K more (₹50K if senior).",
      saving: 25000 * 0.3,
      icon: Shield,
    });
  }

  const parentIns = parseFloat(deductionsData.section80D_parents || 0);
  if (parentIns === 0 && used80D > 0) {
    tips.push({
      priority: "medium",
      title: "Parents' Health Insurance → Extra ₹25K-₹50K deduction",
      desc: "If your parents are senior citizens (60+), you can claim up to ₹50,000 for their premium.",
      saving: 25000 * 0.3,
      icon: Shield,
    });
  }

  if (taxResults) {
    const saving = Math.abs((taxResults.oldTax || 0) - (taxResults.newTax || 0));
    if (saving > 1000) {
      const better = (taxResults.oldTax || 0) < (taxResults.newTax || 0) ? "Old" : "New";
      tips.push({
        priority: "high",
        title: `Switch to ${better} Regime → Save ${fmt(saving)}`,
        desc: `The ${better} regime saves you ${fmt(saving)} based on your current deductions.`,
        saving,
        icon: Scale,
      });
    }
  }

  // Tax-loss harvesting
  const cgDetail = incomeData.capital_gains_detail || {};
  const hasGains = Object.values(cgDetail).some(v => parseFloat(v) > 0);
  if (hasGains) {
    tips.push({
      priority: "medium",
      title: "Consider Tax-Loss Harvesting",
      desc: "Review portfolio for loss positions before March 31. Losses from equity can offset capital gains.",
      saving: 0,
      icon: TrendingUp,
    });
  }

  return tips.sort((a, b) => {
    const order = { critical: 0, high: 1, medium: 2, low: 3 };
    return (order[a.priority] || 3) - (order[b.priority] || 3);
  });
}

// ─── TABS ─────────────────────────────────────────────────────────────────────

const SECTIONS = [
  { id: "dashboard", label: "Dashboard", icon: BarChart3 },
  { id: "income", label: "Income", icon: Wallet },
  { id: "deductions", label: "Deductions", icon: ShieldCheck },
  { id: "capital_gains", label: "Capital Gains", icon: TrendingUp },
  { id: "regime", label: "Regime", icon: Scale },
  { id: "audit", label: "Audit", icon: Search },
  { id: "planning", label: "Planning", icon: Lightbulb },
  { id: "filing", label: "Filing", icon: Send },
];

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export const ITRPage = ({ user, authToken, apiBaseUrl, refreshProfile, transactions = [], showToast }) => {
  const [activeSection, setActiveSection] = useState("dashboard");
  const [taxRegime, setTaxRegime] = useState("new");
  const [isSaving, setIsSaving] = useState(false);
  const [dbStatus, setDbStatus] = useState("checking");

  const [income, setIncome] = useState({
    salary: "", houseProperty: "", businessIncome: "", capitalGains: "",
    otherIncome: "", interestIncome: "",
    salary_components: {}, properties: [], capital_gains_detail: {},
    agriculturalIncome: "",
  });

  const [deductions, setDeductions] = useState({
    section80C: "", section80D: "", section80D_parents: "", section80E: "",
    section80EE: "", section80EEB: "", section80G: "", section80GG: "",
    section80TTA: "", section80U: "", hra: "", homeLoanInterest: "",
    nps80CCD: "", employer_nps: "",
  });

  const [filingDetails, setFilingDetails] = useState({
    panNumber: "", aadharNumber: "", bankAccount: "", ifscCode: "",
    email: "", mobile: "", advanceTaxPaid: "",
  });

  const [profile, setProfile] = useState({
    isPresumptive: false, foreignAssets: false, isDirector: false,
    hasUnlistedEquity: false, entityType: "individual", isNRI: false,
    isMetro: false,
  });

  const [expandedSections, setExpandedSections] = useState({});
  const toggleSection = (id) => setExpandedSections(prev => ({ ...prev, [id]: !prev[id] }));

  const [isDirty, setIsDirty] = useState(false);

  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [isDirty]);

  // ── FETCH ───────────────────────────────────────────────────────────────────
  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const data = await apiFetch(`${apiBaseUrl}/itr-data/${user.id}`);
        const payload = data?.data || data;
        if (payload) {
          setIncome(prev => ({ ...prev, ...(payload.income_data || {}) }));
          setDeductions(prev => ({ ...prev, ...(payload.deductions_data || {}) }));
          setFilingDetails(prev => ({ ...prev, ...(payload.filing_details || {}) }));
          setTaxRegime(payload.tax_regime || "new");
          setDbStatus("online");
        }
      } catch (error) {
        if (error.status === 404) setDbStatus("new_profile");
        else setDbStatus("offline");
      }
    };
    fetchUserData();
  }, [user.id, apiBaseUrl]);

  const [isValidating, setIsValidating] = useState(false);
  const [backendResult, setBackendResult] = useState(null);

  const validateWithBackend = async () => {
    setIsValidating(true);
    try {
      const response = await apiFetch(`${apiBaseUrl}/tax/compute`, {
        method: "POST",
        body: JSON.stringify({
          income_data: income,
          deductions_data: deductions,
          filing_details: filingDetails,
          profile: profile,
        }),
      });
      if (response && response.data) {
        setBackendResult(response.data);
        showToast("Tax validated with server engine", "success");
      }
    } catch (error) {
      console.error("Backend validation failed:", error);
      showToast("Server validation failed", "error");
    } finally {
      setIsValidating(false);
    }
  };

  // ── SAVE ────────────────────────────────────────────────────────────────────
  const saveProgress = useCallback(async () => {
    setIsSaving(true);
    try {
      await apiFetch(`${apiBaseUrl}/itr-data/${user.id}`, {
        method: "POST",
        body: JSON.stringify({
          income_data: income,
          deductions_data: deductions,
          filing_details: filingDetails,
          tax_regime: taxRegime,
        }),
      });
      setDbStatus("online");
      setIsDirty(false);
      if (refreshProfile) refreshProfile();
      
      // Auto-validate silently on save for better data
      const response = await apiFetch(`${apiBaseUrl}/tax/compute`, {
        method: "POST",
        body: JSON.stringify({
          income_data: income,
          deductions_data: deductions,
          filing_details: filingDetails,
          profile: profile,
        }),
      });
      if (response && response.data) setBackendResult(response.data);

    } catch (error) {
      setDbStatus(error.status >= 400 && error.status < 500 ? "error" : "offline");
    } finally {
      setIsSaving(false);
    }
  }, [apiBaseUrl, user.id, income, deductions, filingDetails, taxRegime, profile, refreshProfile]);

  // ── COMPUTED ────────────────────────────────────────────────────────────────
  const oldResult = useMemo(() => computeFullTax(income, deductions, "old"), [income, deductions]);
  const newResult = useMemo(() => computeFullTax(income, deductions, "new"), [income, deductions]);
  const selectedResult = taxRegime === "old" ? oldResult : newResult;
  const itrForm = useMemo(() => determineITRForm(income, profile), [income, profile]);
  const auditResult = useMemo(() => runAuditChecks(income, deductions, filingDetails), [income, deductions, filingDetails]);
  const recommendations = useMemo(() => generateRecommendations(income, deductions, { oldTax: oldResult.totalTax, newTax: newResult.totalTax }), [income, deductions, oldResult.totalTax, newResult.totalTax]);
  const recommendedRegime = oldResult.totalTax < newResult.totalTax ? "old" : "new";
  const regimeSavings = Math.abs(oldResult.totalTax - newResult.totalTax);
  const completionPct = useMemo(() => {
    let done = 0, total = 5;
    if (parseFloat(income.salary || 0) > 0 || parseFloat(income.businessIncome || 0) > 0) done++;
    if (Object.values(deductions).some(v => parseFloat(v) > 0)) done++;
    if (filingDetails.panNumber) done++;
    if (filingDetails.bankAccount) done++;
    if (filingDetails.email) done++;
    return Math.round((done / total) * 100);
  }, [income, deductions, filingDetails]);

  // ── HANDLERS ────────────────────────────────────────────────────────────────
  const updateIncome = (key, val) => {
    setIncome(prev => ({ ...prev, [key]: val }));
    setIsDirty(true);
  };
  const updateSalaryComponent = (key, val) => {
    setIncome(prev => ({
      ...prev,
      salary_components: { ...prev.salary_components, [key]: val },
    }));
    setIsDirty(true);
  };

  const updatePropertyDetail = (index, key, val) => {
    setIncome(prev => {
      const props = [...(prev.properties || [])];
      if (!props[index]) props[index] = { property_type: "self_occupied" };
      props[index] = { ...props[index], [key]: val };
      return { ...prev, properties: props };
    });
    setIsDirty(true);
  };

  const addProperty = () => {
    setIncome(prev => ({
      ...prev,
      properties: [...(prev.properties || []), { property_type: "self_occupied" }]
    }));
    setIsDirty(true);
  };

  const removeProperty = (index) => {
    setIncome(prev => ({
      ...prev,
      properties: prev.properties.filter((_, i) => i !== index)
    }));
    setIsDirty(true);
  };

  const updateCapitalGainDetail = (key, val) => {
    setIncome(prev => ({
      ...prev,
      capital_gains_detail: { ...prev.capital_gains_detail, [key]: val },
    }));
    setIsDirty(true);
  };
  const updateDeduction = (key, val) => {
    setDeductions(prev => ({ ...prev, [key]: val }));
    setIsDirty(true);
  };
  const updateFiling = (key, val) => {
    setFilingDetails(prev => ({ ...prev, [key]: val }));
    setIsDirty(true);
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════════════════

  return (
    <div className="min-h-screen bg-transparent text-slate-200 pb-20 overflow-x-hidden">
      <div className="max-w-5xl mx-auto space-y-6 px-2">

        {/* ── HEADER ──────────────────────────────────────────────────────── */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between bg-white/5 p-5 rounded-[2rem] border border-white/10 backdrop-blur-xl shadow-2xl">
          <div className="flex items-center gap-4">
            <div className="bg-gradient-to-br from-blue-500 to-cyan-400 p-3 rounded-2xl shadow-lg shadow-blue-500/20">
              <Calculator className="text-slate-900 w-6 h-6" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-tight">DIY Tax Engine</h1>
              <div className="flex items-center gap-3">
                <div className={`w-1.5 h-1.5 rounded-full ${dbStatus === 'online' ? 'bg-emerald-500' : dbStatus === 'new_profile' ? 'bg-amber-500' : 'bg-red-500'}`} />
                <p className="text-[9px] text-slate-400 uppercase font-bold tracking-[0.2em]">FY {FY} • AY {AY}</p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-[9px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${recommendedRegime === taxRegime ? "bg-emerald-500/15 text-emerald-400" : "bg-amber-500/15 text-amber-400"}`}>
              {taxRegime} regime
            </span>
            <button 
              onClick={validateWithBackend} 
              disabled={isValidating}
              className="flex items-center gap-2 px-4 py-2.5 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 rounded-xl transition-all"
            >
              {isValidating ? <div className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" /> : <ShieldCheck size={14} className="text-blue-400" />}
              <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400">{isValidating ? "Validating..." : "Validate"}</span>
            </button>
            <button onClick={saveProgress} className="flex items-center gap-2 px-4 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-all">
              {isSaving ? <div className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" /> : <Save size={14} className="text-blue-400" />}
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-300">{isSaving ? "Saving..." : "Save"}</span>
            </button>
          </div>
        </motion.div>

        {/* ── TAB NAVIGATION ──────────────────────────────────────────────── */}
        <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-hide">
          {SECTIONS.map((s) => (
            <button key={s.id} onClick={() => { setActiveSection(s.id); }}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-[10px] font-bold uppercase tracking-wider whitespace-nowrap transition-all ${
                activeSection === s.id
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20"
                  : "bg-white/5 text-slate-400 hover:bg-white/10 hover:text-slate-200 border border-white/5"
              }`}>
              <s.icon size={13} />
              {s.label}
              {s.id === "audit" && (auditResult.errors.length + auditResult.warnings.length) > 0 && (
                <span className="ml-1 w-4 h-4 rounded-full bg-rose-500 text-[9px] font-black flex items-center justify-center text-white">
                  {auditResult.errors.length + auditResult.warnings.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* ── CONTENT ─────────────────────────────────────────────────────── */}
        <AnimatePresence mode="wait">
          <motion.div key={activeSection} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }} transition={{ duration: 0.2 }}>

            {/* ════════════ DASHBOARD ════════════ */}
            {activeSection === "dashboard" && (
              <div className="space-y-6">
                {/* Top stat cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <StatCard label="Gross Income" value={fmt(selectedResult.grossTotalIncome)} icon={Wallet} color="blue" />
                  <StatCard label="Total Tax" value={fmt(selectedResult.totalTax)} subtitle={`${taxRegime} regime`} icon={Receipt} color="rose" />
                  <StatCard label="Deductions" value={fmt(selectedResult.totalDeductions)} icon={ShieldCheck} color="emerald" />
                  <StatCard label="Regime Savings" value={fmt(regimeSavings)} subtitle={`${recommendedRegime} regime better`} icon={Sparkles} color="amber" />
                </div>

                {/* Regime comparison card */}
                <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5 backdrop-blur-xl">
                  <SectionHeader icon={Scale} title="Regime Comparison" badge={`${recommendedRegime} recommended`} />
                  <div className="grid grid-cols-2 gap-4">
                    {["old", "new"].map((r) => {
                      const result = r === "old" ? oldResult : newResult;
                      const isSelected = taxRegime === r;
                      const isRecommended = recommendedRegime === r;
                      return (
                        <button key={r} onClick={() => setTaxRegime(r)}
                          className={`p-5 rounded-2xl border-2 text-left transition-all relative overflow-hidden ${isSelected ? "border-blue-500 bg-blue-500/10" : "border-white/5 bg-white/5 hover:border-white/10"}`}>
                          {isRecommended && <div className="absolute top-0 right-0 bg-emerald-500 text-[7px] font-black px-3 py-1 rounded-bl-xl uppercase tracking-widest text-slate-900">Best</div>}
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-black text-white uppercase text-[10px] tracking-[0.15em]">{r} Regime</span>
                            {isSelected && <CheckCircle2 className="text-blue-400" size={18} />}
                          </div>
                          <div className="text-2xl font-black text-white tracking-tighter mb-2">{fmt(result.totalTax)}</div>
                          <div className="space-y-1 text-[10px] text-slate-500">
                            <div className="flex justify-between"><span>Base Tax</span><span>{fmt(result.baseTax)}</span></div>
                            {result.surcharge > 0 && <div className="flex justify-between"><span>Surcharge</span><span>{fmt(result.surcharge)}</span></div>}
                            <div className="flex justify-between"><span>Cess (4%)</span><span>{fmt(result.cess)}</span></div>
                            {result.capitalGainsTax > 0 && <div className="flex justify-between"><span>CG Tax</span><span>{fmt(result.capitalGainsTax)}</span></div>}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* ITR Form + Filing Checklist */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
                    <SectionHeader icon={FileText} title="ITR Form" />
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-3xl font-black text-blue-400">{itrForm.form}</span>
                      <span className="text-sm text-slate-400 font-medium">({itrForm.name})</span>
                    </div>
                    <p className="text-[11px] text-slate-500 leading-relaxed">{itrForm.reason}</p>
                  </div>

                  <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
                    <SectionHeader icon={CheckCircle2} title="Filing Progress" badge={`${completionPct}%`} />
                    <ProgressBar value={completionPct} max={100} />
                    <div className="mt-3 space-y-2">
                      {[
                        { label: "Income declared", done: parseFloat(income.salary || 0) > 0 || parseFloat(income.businessIncome || 0) > 0 },
                        { label: "Deductions entered", done: Object.values(deductions).some(v => parseFloat(v) > 0) },
                        { label: "PAN verified", done: !!filingDetails.panNumber },
                        { label: "Bank account linked", done: !!filingDetails.bankAccount },
                        { label: "Contact details", done: !!filingDetails.email },
                      ].map((item, i) => (
                        <div key={i} className="flex items-center gap-2 text-[10px]">
                          {item.done ? <CheckCircle2 size={12} className="text-emerald-400" /> : <div className="w-3 h-3 rounded-full border border-white/20" />}
                          <span className={item.done ? "text-slate-300" : "text-slate-600"}>{item.label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Tax Saving Tips */}
                {recommendations.length > 0 && (
                  <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
                    <SectionHeader icon={Lightbulb} title="Tax Saving Tips" badge={`${recommendations.length} tips`} />
                    <div className="space-y-3">
                      {recommendations.slice(0, 4).map((tip, i) => (
                        <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-white/[0.03] border border-white/5">
                          <div className={`p-1.5 rounded-lg ${tip.priority === "critical" ? "bg-rose-500/15" : tip.priority === "high" ? "bg-amber-500/15" : "bg-blue-500/15"}`}>
                            <tip.icon size={14} className={tip.priority === "critical" ? "text-rose-400" : tip.priority === "high" ? "text-amber-400" : "text-blue-400"} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-bold text-white">{tip.title}</p>
                            <p className="text-[10px] text-slate-500 mt-0.5 leading-relaxed">{tip.desc}</p>
                          </div>
                          {tip.saving > 0 && <span className="text-[10px] font-bold text-emerald-400 whitespace-nowrap">Save {fmt(tip.saving)}</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Alerts */}
                {(auditResult.errors.length > 0 || auditResult.warnings.length > 0) && (
                  <div className="space-y-2">
                    {auditResult.errors.map((e, i) => <AlertBox key={`e${i}`} type="error">{e.msg}</AlertBox>)}
                    {auditResult.warnings.slice(0, 3).map((w, i) => <AlertBox key={`w${i}`} type="warning">{w.msg}</AlertBox>)}
                  </div>
                )}
              </div>
            )}

            {/* ════════════ INCOME ════════════ */}
            {activeSection === "income" && (
              <div className="space-y-6">
                {/* Basic Income Fields */}
                <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6 backdrop-blur-xl">
                  <SectionHeader icon={Wallet} title="Five Heads of Income" subtitle="Sections 14–59 of the Income Tax Act" badge={`FY ${FY}`} />
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <CurrencyInput label="Salary Income (Head 1)" value={income.salary} onChange={(v) => updateIncome("salary", v)} help="Sum of Basic, HRA, DA, Special Allowance from Form 16 Part B" />
                    <CurrencyInput label="House Property (Head 2)" value={income.houseProperty} onChange={(v) => updateIncome("houseProperty", v)} help="Net income after 30% standard deduction and loan interest" />
                    <CurrencyInput label="Business / Profession (Head 3)" value={income.businessIncome} onChange={(v) => updateIncome("businessIncome", v)} help="Profits & gains from business or profession (Sec 28-44)" />
                    <CurrencyInput label="Capital Gains (Head 4)" value={income.capitalGains} onChange={(v) => updateIncome("capitalGains", v)} help="Net gains from sale of property, shares, MFs, crypto" />
                    <CurrencyInput label="Other Sources (Head 5)" value={income.otherIncome} onChange={(v) => updateIncome("otherIncome", v)} help="Freelance, gifts, lottery, dividend, family pension etc." />
                    <CurrencyInput label="Interest Income" value={income.interestIncome} onChange={(v) => updateIncome("interestIncome", v)} help="Savings + FD interest. FD interest is fully taxable." />
                    <CurrencyInput label="Agricultural Income" value={income.agriculturalIncome} onChange={(v) => updateIncome("agriculturalIncome", v)} help="Exempt u/s 10(1), but used for rate purposes if > ₹5,000" />
                  </div>
                </div>

                {/* Detailed Salary Breakup */}
                <div className="bg-white/[0.04] border border-white/10 rounded-2xl overflow-hidden">
                  <button onClick={() => toggleSection("salary_detail")} className="w-full flex items-center justify-between p-5 hover:bg-white/[0.02] transition-colors">
                    <div className="flex items-center gap-3">
                      <Briefcase size={16} className="text-blue-400" />
                      <span className="text-sm font-bold text-white">Detailed Salary Breakup (Form 16)</span>
                    </div>
                    {expandedSections.salary_detail ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
                  </button>
                  <AnimatePresence>
                    {expandedSections.salary_detail && (
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                        <div className="p-5 pt-0 grid grid-cols-1 md:grid-cols-2 gap-3">
                          {SALARY_COMPONENTS.map((comp) => (
                            <CurrencyInput
                              key={comp.key} compact
                              label={`${comp.label} ${comp.taxable ? "" : "(exempt)"}`}
                              value={income.salary_components?.[comp.key] || ""}
                              onChange={(v) => updateSalaryComponent(comp.key, v)}
                              help={comp.help}
                            />
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* House Property Details */}
                <div className="bg-white/[0.04] border border-white/10 rounded-2xl overflow-hidden">
                  <button onClick={() => toggleSection("hp_detail")} className="w-full flex items-center justify-between p-5 hover:bg-white/[0.02] transition-colors">
                    <div className="flex items-center gap-3">
                      <Home size={16} className="text-emerald-400" />
                      <span className="text-sm font-bold text-white">Detailed House Property Info</span>
                    </div>
                    {expandedSections.hp_detail ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
                  </button>
                  <AnimatePresence>
                    {expandedSections.hp_detail && (
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                        <div className="p-5 pt-0 space-y-6">
                          {(income.properties || []).map((prop, idx) => (
                            <div key={idx} className="p-5 bg-white/[0.02] border border-white/5 rounded-2xl relative group">
                              <button onClick={() => removeProperty(idx)} className="absolute top-4 right-4 text-slate-600 hover:text-rose-400 transition-colors opacity-0 group-hover:opacity-100">
                                <X size={14} />
                              </button>
                              <p className="text-[9px] font-black text-slate-600 uppercase tracking-widest mb-4">Property #{idx + 1}</p>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {HOUSE_PROPERTY_FIELDS.map((field) => {
                                  if (field.condition && !field.condition(prop)) return null;
                                  
                                  if (field.type === "select") {
                                    return (
                                      <div key={field.key} className="space-y-1.5">
                                        <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider ml-1">{field.label}</label>
                                        <select
                                          value={prop[field.key] || ""}
                                          onChange={(e) => updatePropertyDetail(idx, field.key, e.target.value)}
                                          className="w-full bg-black/20 border border-white/10 rounded-xl py-3 px-3 text-xs text-white focus:border-blue-500/50 outline-none transition-all"
                                        >
                                          <option value="">Select Type</option>
                                          {field.options.map(opt => <option key={opt} value={opt}>{opt.replace(/_/g, " ").toUpperCase()}</option>)}
                                        </select>
                                      </div>
                                    );
                                  }
                                  
                                  if (field.type === "currency") {
                                    return (
                                      <CurrencyInput
                                        key={field.key} compact
                                        label={field.label}
                                        value={prop[field.key] || ""}
                                        onChange={(v) => updatePropertyDetail(idx, field.key, v)}
                                      />
                                    );
                                  }

                                  return (
                                    <div key={field.key} className="space-y-1.5">
                                      <label className="text-[10px] text-slate-500 font-bold uppercase tracking-wider ml-1">{field.label}</label>
                                      <input
                                        type={field.type === "number" ? "number" : field.type === "date" ? "date" : "text"}
                                        value={
                                          (field.type === "number" && (!prop[field.key] || Number(prop[field.key]) === 0))
                                            ? ""
                                            : prop[field.key] || ""
                                        }
                                        onChange={(e) => updatePropertyDetail(idx, field.key, e.target.value)}
                                        className="w-full bg-black/20 border border-white/10 rounded-xl py-2.5 px-3 text-xs text-white focus:border-blue-500/50 outline-none transition-all"
                                      />
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          ))}
                          <button onClick={addProperty} className="w-full py-3 border border-dashed border-white/10 rounded-xl text-[10px] font-bold text-slate-500 hover:border-blue-500/30 hover:text-blue-400 transition-all uppercase tracking-widest flex items-center justify-center gap-2">
                            <Plus size={14} className="text-blue-400" /> Add Property
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Business Profile */}
                {parseFloat(income.businessIncome || 0) > 0 && (
                  <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
                    <SectionHeader icon={Building2} title="Business Profile" subtitle="Section 44AD / 44ADA / 44AB" />
                    <div className="space-y-4">
                      <div className="flex items-center gap-3">
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input type="checkbox" checked={profile.isPresumptive} onChange={(e) => setProfile(prev => ({ ...prev, isPresumptive: e.target.checked }))} className="rounded" />
                          <span className="text-xs text-slate-300">Opting for Presumptive Taxation (44AD/44ADA)</span>
                        </label>
                        <InfoTooltip text="44AD: Deemed profit 8% (6% digital). Turnover ≤ ₹3Cr. 44ADA: 50% for professionals, receipts ≤ ₹75L." />
                      </div>
                      <AlertBox type="info">If your actual profit is lower than the presumptive rate, you must maintain books of account and get a tax audit.</AlertBox>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ════════════ DEDUCTIONS ════════════ */}
            {activeSection === "deductions" && (
              <div className="space-y-6">
                <AlertBox type="info">
                  Deductions under Chapter VI-A primarily benefit the <strong>Old Tax Regime</strong>. The New Regime only allows Standard Deduction (₹75,000) and 80CCD(2) employer NPS.
                </AlertBox>

                <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6">
                  <SectionHeader icon={ShieldCheck} title="Chapter VI-A Deductions" subtitle="Complete catalog of available deductions" badge={taxRegime === "new" ? "Limited in New Regime" : "All Available"} />
                  <div className="space-y-4">
                    {DEDUCTION_CATALOG.map((ded) => {
                      const isDisabled = taxRegime === "new" && !ded.regimes.includes("new");
                      return (
                        <div key={ded.key} className={`p-4 rounded-xl border transition-all ${isDisabled ? "border-white/5 opacity-40" : "border-white/10 bg-white/[0.02]"}`}>
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex items-start gap-3 flex-1">
                              <div className={`p-1.5 rounded-lg ${isDisabled ? "bg-white/5" : "bg-blue-500/10"}`}>
                                <ded.icon size={14} className={isDisabled ? "text-slate-600" : "text-blue-400"} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="text-[10px] font-black text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">{ded.section}</span>
                                  <span className="text-xs font-medium text-white">{ded.label}</span>
                                  {isDisabled && <span className="text-[8px] font-bold text-slate-600 uppercase">Old regime only</span>}
                                </div>
                                {ded.note && <p className="text-[10px] text-slate-500 mt-1">{ded.note}</p>}
                                {ded.limit && <p className="text-[10px] text-slate-600 mt-0.5">Limit: {fmt(ded.limit)}</p>}
                              </div>
                            </div>
                            <div className="w-36">
                              <CurrencyInput
                                compact
                                value={deductions[ded.key] || ""}
                                onChange={(v) => updateDeduction(ded.key, v)}
                                disabled={isDisabled}
                              />
                            </div>
                          </div>
                          {ded.limit && !isDisabled && parseFloat(deductions[ded.key] || 0) > 0 && (
                            <div className="mt-2 ml-10">
                              <ProgressBar value={Math.min(parseFloat(deductions[ded.key] || 0), ded.limit)} max={ded.limit} color={parseFloat(deductions[ded.key] || 0) > ded.limit ? "rose" : "blue"} />
                              <p className="text-[9px] text-slate-600 mt-0.5">{pct(parseFloat(deductions[ded.key] || 0), ded.limit)}% utilized</p>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Deduction Summary */}
                <div className="bg-gradient-to-br from-blue-600/20 to-indigo-600/20 border border-blue-500/20 rounded-2xl p-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-bold text-blue-300 uppercase tracking-wider">Total Deductions Claimed</span>
                    <span className="text-2xl font-black text-white">{fmt(selectedResult.totalDeductions)}</span>
                  </div>
                  <div className="text-[10px] text-blue-200/60">Includes standard deduction of {fmt(taxRegime === "new" ? 75000 : 50000)}</div>
                </div>
              </div>
            )}

            {/* ════════════ CAPITAL GAINS ════════════ */}
            {activeSection === "capital_gains" && (
              <div className="space-y-6">
                <AlertBox type="warning">
                  Budget 2024 removed indexation benefit. LTCG at 12.5% (no indexation). Transitional relief for property acquired before 23-Jul-2024. F&O trading is <strong>business income</strong>, not capital gains!
                </AlertBox>

                <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6">
                  <SectionHeader icon={TrendingUp} title="Capital Gains Schedule" subtitle="Post-Budget 2024 rates (FY 2024-25)" />
                  <div className="space-y-3">
                    {CAPITAL_GAIN_TYPES.map((cg) => (
                      <div key={cg.key} className="flex items-center gap-4 p-3 rounded-xl bg-white/[0.02] border border-white/5">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-medium text-white">{cg.label}</span>
                            <span className="text-[9px] font-bold px-2 py-0.5 rounded bg-white/5 text-slate-400">{cg.rate}</span>
                            {cg.section && <span className="text-[9px] font-bold text-blue-400">§{cg.section}</span>}
                          </div>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-[10px] text-slate-600">Holding: {cg.period}</span>
                            {cg.exempt && <span className="text-[10px] text-emerald-500">Exempt up to {fmt(cg.exempt)}</span>}
                          </div>
                          {cg.note && <p className="text-[10px] text-amber-500/70 mt-0.5">{cg.note}</p>}
                        </div>
                        <div className="w-32">
                          <CurrencyInput
                            compact
                            value={income.capital_gains_detail?.[cg.key] || ""}
                            onChange={(v) => updateCapitalGainDetail(cg.key, v)}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* CG Tax Summary */}
                {selectedResult.capitalGainsTax > 0 && (
                  <div className="bg-gradient-to-br from-amber-600/20 to-orange-600/20 border border-amber-500/20 rounded-2xl p-5">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] font-bold text-amber-300 uppercase tracking-wider">Total Capital Gains Tax</span>
                      <span className="text-2xl font-black text-white">{fmt(selectedResult.capitalGainsTax)}</span>
                    </div>
                    <p className="text-[10px] text-amber-200/50 mt-1">Includes 4% cess. CG tax is computed separately at special rates.</p>
                  </div>
                )}

                <AlertBox type="info">
                  <strong>Set-Off Rules:</strong> STCL → against any CG (STCG + LTCG). LTCL → only against LTCG. Crypto losses cannot be set off against any income. Carry forward: 8 AYs.
                </AlertBox>
              </div>
            )}

            {/* ════════════ REGIME COMPARISON ════════════ */}
            {activeSection === "regime" && (
              <div className="space-y-6">
                <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6">
                  <SectionHeader icon={Scale} title="Regime Optimizer" subtitle="Side-by-side comparison with full breakdown" />

                  <div className="grid grid-cols-2 gap-4 mb-6">
                    {[
                      { key: "old", result: oldResult, slabInfo: "₹2.5L / ₹5L / ₹10L" },
                      { key: "new", result: newResult, slabInfo: "₹4L / ₹8L / ₹12L / ₹16L / ₹20L / ₹24L" },
                    ].map(({ key, result, slabInfo }) => {
                      const isSelected = taxRegime === key;
                      const isBetter = recommendedRegime === key;
                      return (
                        <button key={key} onClick={() => setTaxRegime(key)}
                          className={`p-5 rounded-2xl border-2 text-left transition-all relative overflow-hidden ${isSelected ? "border-blue-500 bg-blue-500/10" : "border-white/5 bg-white/5 hover:border-white/10"}`}>
                          {isBetter && <div className="absolute top-0 right-0 bg-emerald-500 text-[7px] font-black px-3 py-1 rounded-bl-xl uppercase tracking-widest text-slate-900">Saves {fmt(regimeSavings)}</div>}
                          <div className="flex items-center gap-2 mb-3">
                            <span className="font-black text-white uppercase text-xs tracking-wider">{key} Regime</span>
                            {isSelected && <CheckCircle2 className="text-blue-400" size={16} />}
                          </div>
                          <div className="text-3xl font-black text-white tracking-tighter mb-4">{fmt(result.totalTax)}</div>
                          <div className="space-y-1.5 text-[10px] text-slate-500">
                            <div className="flex justify-between"><span>Taxable Income</span><span className="text-slate-300">{fmt(result.taxableIncome)}</span></div>
                            <div className="flex justify-between"><span>Deductions</span><span className="text-slate-300">{fmt(result.totalDeductions)}</span></div>
                            <div className="flex justify-between"><span>Standard Deduction</span><span className="text-slate-300">{fmt(key === "new" ? 75000 : 50000)}</span></div>
                            <div className="flex justify-between border-t border-white/5 pt-1.5 mt-1.5"><span>Base Tax</span><span className="text-white font-bold">{fmt(result.baseTax)}</span></div>
                            {result.surcharge > 0 && <div className="flex justify-between"><span>Surcharge ({(result.surchargeRate * 100).toFixed(0)}%)</span><span>{fmt(result.surcharge)}</span></div>}
                            <div className="flex justify-between"><span>Cess (4%)</span><span>{fmt(result.cess)}</span></div>
                            {result.capitalGainsTax > 0 && <div className="flex justify-between"><span>CG Tax</span><span>{fmt(result.capitalGainsTax)}</span></div>}
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  {/* Breakeven analysis */}
                  <div className="bg-white/[0.03] border border-white/5 rounded-xl p-4">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Breakeven Analysis</p>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      {recommendedRegime === "new"
                        ? `Your current deductions (${fmt(oldResult.totalDeductions)}) are not enough to offset the wider slabs of the New Regime. You would need approximately ${fmt(Math.max(0, (newResult.taxableIncome - oldResult.taxableIncome) + regimeSavings / 0.3))} more in deductions to make Old Regime worthwhile.`
                        : `Your deductions of ${fmt(oldResult.totalDeductions)} make the Old Regime ${fmt(regimeSavings)} cheaper. Consider maximizing 80C and NPS to widen the gap.`
                      }
                    </p>
                  </div>
                </div>

                {/* Slab visualization */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[
                    { title: "Old Regime Slabs", slabs: [{ range: "Up to ₹2.5L", rate: "Nil" }, { range: "₹2.5L – ₹5L", rate: "5%" }, { range: "₹5L – ₹10L", rate: "20%" }, { range: "Above ₹10L", rate: "30%" }], rebate: "Rebate u/s 87A up to ₹12,500 if income ≤ ₹5L" },
                    { title: "New Regime Slabs (Default)", slabs: [{ range: "Up to ₹4L", rate: "Nil" }, { range: "₹4L – ₹8L", rate: "5%" }, { range: "₹8L – ₹12L", rate: "10%" }, { range: "₹12L – ₹16L", rate: "15%" }, { range: "₹16L – ₹20L", rate: "20%" }, { range: "₹20L – ₹24L", rate: "25%" }, { range: "Above ₹24L", rate: "30%" }], rebate: "Rebate: Zero tax up to ₹12L, marginal relief up to ₹12.60L" },
                  ].map((block, i) => (
                    <div key={i} className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
                      <p className="text-xs font-bold text-white mb-3">{block.title}</p>
                      <div className="space-y-1.5">
                        {block.slabs.map((s, j) => (
                          <div key={j} className="flex justify-between text-[11px]">
                            <span className="text-slate-400">{s.range}</span>
                            <span className="font-bold text-white">{s.rate}</span>
                          </div>
                        ))}
                      </div>
                      <p className="text-[9px] text-blue-400/60 mt-3 border-t border-white/5 pt-2">{block.rebate}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ════════════ AUDIT ════════════ */}
            {activeSection === "audit" && (
              <div className="space-y-6">
                <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6">
                  <SectionHeader 
                    icon={Search} 
                    title="Pre-Filing Audit" 
                    subtitle={backendResult ? "Server-Verified Compliance Check" : "Local Automated compliance checks"} 
                    badge={backendResult ? `${backendResult.audit.errors.length} errors • ${backendResult.audit.warnings.length} warnings` : `${auditResult.errors.length} errors • ${auditResult.warnings.length} warnings`} 
                  />

                  {((backendResult ? backendResult.audit.errors : auditResult.errors).length === 0 && (backendResult ? backendResult.audit.warnings : auditResult.warnings).length === 0) ? (
                    <div className="text-center py-10">
                      <CheckCircle2 size={48} className="text-emerald-400 mx-auto mb-3" />
                      <p className="text-lg font-bold text-white">All Clear!</p>
                      <p className="text-xs text-slate-500">{backendResult ? "Server" : "Local"} engine confirms no issues detected in your filing data.</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {(backendResult ? backendResult.audit.errors : auditResult.errors).map((e, i) => (
                        <div key={`e${i}`} className="flex items-start gap-3 p-4 rounded-xl border border-rose-500/20 bg-rose-500/5">
                          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-rose-500/15 text-rose-400 uppercase">{e.section}</span>
                              <span className="text-[9px] font-bold text-rose-400 uppercase">Error</span>
                            </div>
                            <p className="text-xs text-rose-200 mt-1">{e.msg}</p>
                          </div>
                        </div>
                      ))}
                      {(backendResult ? backendResult.audit.warnings : auditResult.warnings).map((w, i) => (
                        <div key={`w${i}`} className="flex items-start gap-3 p-4 rounded-xl border border-amber-500/20 bg-amber-500/5">
                          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 uppercase">{w.section}</span>
                              <span className="text-[9px] font-bold text-amber-400 uppercase">Warning</span>
                            </div>
                            <p className="text-xs text-amber-200 mt-1">{w.msg}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {backendResult && (
                    <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-center gap-2">
                      <BadgeCheck size={14} className="text-emerald-400" />
                      <span className="text-[10px] font-bold text-emerald-400/80 uppercase tracking-widest">Verified by Spendsy Tax Engine v2.0</span>
                    </div>
                  )}
                </div>

                {/* Common Filing Mistakes */}
                <div className="bg-white/[0.04] border border-white/10 rounded-2xl overflow-hidden">
                  <button onClick={() => toggleSection("mistakes")} className="w-full flex items-center justify-between p-5 hover:bg-white/[0.02]">
                    <div className="flex items-center gap-3">
                      <TriangleAlert size={16} className="text-amber-400" />
                      <span className="text-sm font-bold text-white">Common Filing Mistakes to Avoid</span>
                    </div>
                    {expandedSections.mistakes ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
                  </button>
                  <AnimatePresence>
                    {expandedSections.mistakes && (
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                        <div className="p-5 pt-0 space-y-2">
                          {[
                            "Not reporting exempt income (LTCG < ₹1.25L still goes in ITR)",
                            "Wrong AY: FY 2024-25 = AY 2025-26",
                            "Missing bank account details — ALL accounts must be listed",
                            "F&O income is business income, NOT capital gains",
                            "Forgetting 4% cess on total tax + surcharge",
                            "Claiming Old Regime deductions in New Regime (only 80CCD(2) allowed)",
                            "Not computing marginal relief at surcharge thresholds",
                            "Filing wrong ITR form = defective return",
                            "Losses cannot be carried forward in belated returns (except HP loss)",
                          ].map((mistake, i) => (
                            <div key={i} className="flex items-start gap-2 text-[11px] text-slate-400">
                              <span className="text-rose-500 font-bold shrink-0">{i + 1}.</span>
                              <span>{mistake}</span>
                            </div>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            )}

            {/* ════════════ PLANNING ════════════ */}
            {activeSection === "planning" && (
              <div className="space-y-6">
                {/* Advance Tax */}
                <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6">
                  <SectionHeader icon={Calendar} title="Advance Tax Schedule" subtitle="Section 208-211 • Tax > ₹10,000 after TDS" />
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {(backendResult ? backendResult.advance_tax_schedule : ADVANCE_TAX_SCHEDULE).map((inst, i) => {
                      const amount = Math.round(selectedResult.totalTax * (inst.cumulative_pct || inst.cumPct) / 100);
                      const isPast = new Date() > new Date(ADV_YR, [5, 8, 11, 2][i], 15);
                      return (
                        <div key={i} className={`p-4 rounded-xl border text-center ${isPast ? "border-emerald-500/20 bg-emerald-500/5" : "border-white/10 bg-white/[0.02]"}`}>
                          <p className="text-[9px] font-bold text-slate-500 uppercase">{inst.installment}</p>
                          <p className="text-xs font-bold text-blue-400 mt-1">{inst.due_date || inst.due}</p>
                          <p className="text-lg font-black text-white mt-1">{fmt(amount)}</p>
                          <p className="text-[9px] text-slate-600">{(inst.cumulative_pct || inst.cumPct)}% cumulative</p>
                        </div>
                      );
                    })}
                  </div>
                  {selectedResult.totalTax > 10000 && (
                    <AlertBox type="warning">Your tax liability exceeds ₹10,000. Advance tax is mandatory. Non-payment attracts interest u/s 234B (1%/month on shortfall) and 234C (1%/month per installment).</AlertBox>
                  )}
                </div>

                {/* Tax Saving Tips */}
                <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6">
                  <SectionHeader icon={Lightbulb} title="Personalized Recommendations" badge={`${(backendResult ? backendResult.recommendations : recommendations).length} actions`} />
                  <div className="space-y-3">
                    {(backendResult ? backendResult.recommendations : recommendations).map((tip, i) => (
                      <div key={i} className="flex items-start gap-3 p-4 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors">
                        <div className={`p-2 rounded-xl ${
                          tip.priority === "critical" ? "bg-rose-500/10" :
                          tip.priority === "high" ? "bg-amber-500/10" : "bg-blue-500/10"
                        }`}>
                          {(tip.icon || Lightbulb) && (() => {
                            const Icon = tip.icon || Lightbulb;
                            return <Icon size={16} className={
                              tip.priority === "critical" ? "text-rose-400" :
                              tip.priority === "high" ? "text-amber-400" : "text-blue-400"
                            } />;
                          })()}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-[8px] font-black uppercase px-1.5 py-0.5 rounded ${
                              tip.priority === "critical" ? "bg-rose-500/15 text-rose-400" :
                              tip.priority === "high" ? "bg-amber-500/15 text-amber-400" :
                              "bg-blue-500/15 text-blue-400"
                            }`}>{tip.priority}</span>
                          </div>
                          <p className="text-sm font-bold text-white">{tip.title}</p>
                          <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">{tip.desc}</p>
                        </div>
                        {(tip.saving || tip.potential_saving) > 0 && (
                          <div className="text-right">
                            <p className="text-xs font-bold text-emerald-400">{fmt(tip.saving || tip.potential_saving)}</p>
                            <p className="text-[9px] text-slate-600">potential savings</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Tax Calendar */}
                <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6">
                  <SectionHeader icon={Calendar} title="Tax Calendar" subtitle={`FY ${FY}`} />
                  <div className="space-y-2">
                    {TAX_CALENDAR.map((item, i) => (
                      <div key={i} className={`flex items-center gap-3 p-3 rounded-xl border ${
                        item.type === "critical" ? "border-rose-500/20 bg-rose-500/5" :
                        item.type === "deadline" ? "border-amber-500/10 bg-amber-500/5" :
                        "border-white/5 bg-white/[0.02]"
                      }`}>
                        <div className={`p-1.5 rounded-lg ${
                          item.type === "critical" ? "bg-rose-500/15" :
                          item.type === "deadline" ? "bg-amber-500/15" : "bg-blue-500/10"
                        }`}>
                          <item.icon size={14} className={
                            item.type === "critical" ? "text-rose-400" :
                            item.type === "deadline" ? "text-amber-400" : "text-blue-400"
                          } />
                        </div>
                        <span className="text-[10px] font-bold text-slate-400 w-16 shrink-0">{item.month}</span>
                        <span className="text-xs text-slate-300 flex-1">{item.action}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* ════════════ FILING ════════════ */}
            {activeSection === "filing" && (
              <div className="space-y-6">
                {/* Filing Details Form */}
                <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6">
                  <SectionHeader icon={Send} title="Filing Details" subtitle="Required information for ITR submission" />
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[
                      { key: "panNumber", label: "PAN Number", placeholder: "ABCDE1234F", help: "10-digit Permanent Account Number", transform: (v) => v.toUpperCase() },
                      { key: "aadharNumber", label: "Aadhaar Number", placeholder: "1234 5678 9012", help: "12-digit Unique ID (masked in filing)" },
                      { key: "bankAccount", label: "Bank Account Number", placeholder: "Account number for refund", help: "Primary bank account for tax refund" },
                      { key: "ifscCode", label: "IFSC Code", placeholder: "SBIN0001234", help: "11-digit bank branch code", transform: (v) => v.toUpperCase() },
                      { key: "email", label: "Email", placeholder: "you@example.com", help: "For IT Dept communication" },
                      { key: "mobile", label: "Mobile", placeholder: "9876543210", help: "Linked to Aadhaar/PAN" },
                    ].map((field) => (
                      <div key={field.key} className="space-y-1.5">
                        <div className="flex items-center gap-1 text-[10px] text-slate-500 font-bold uppercase tracking-wider ml-1">
                          {field.label} {field.help && <InfoTooltip text={field.help} />}
                        </div>
                        <input
                          type="text"
                          value={filingDetails[field.key] || ""}
                          onChange={(e) => {
                            const val = field.transform ? field.transform(e.target.value) : e.target.value;
                            updateFiling(field.key, val);
                          }}
                          className="w-full bg-black/20 border border-white/10 rounded-xl py-3.5 px-4 text-white focus:border-blue-500/50 outline-none transition-all"
                          placeholder={field.placeholder}
                        />
                      </div>
                    ))}
                    <CurrencyInput label="Advance Tax Already Paid" value={filingDetails.advanceTaxPaid} onChange={(v) => updateFiling("advanceTaxPaid", v)} help="Total advance tax + self-assessment tax paid this FY" />
                  </div>
                </div>

                {/* Tax Summary Final */}
                <div className="bg-gradient-to-br from-blue-600 to-indigo-800 rounded-2xl p-5 sm:p-8 shadow-2xl text-center">
                  <p className="text-blue-100 text-[10px] uppercase font-black tracking-[0.3em] mb-3">Final Tax Liability</p>
                  <h2 className="text-3xl sm:text-4xl md:text-5xl font-black text-white tracking-tighter mb-4 break-all">{fmt(selectedResult.totalTax)}</h2>
                  <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-black/20 rounded-full border border-white/10 mb-4">
                    <span className="text-[9px] font-bold text-white uppercase">{taxRegime} Regime • {itrForm.form}</span>
                  </div>

                  {parseFloat(filingDetails.advanceTaxPaid || 0) > 0 && (
                    <div className="mt-4 space-y-2">
                      <div className="flex justify-center gap-8 text-sm">
                        <div>
                          <p className="text-blue-200/60 text-[10px] uppercase">Tax Paid</p>
                          <p className="text-white font-bold">{fmt(parseFloat(filingDetails.advanceTaxPaid || 0))}</p>
                        </div>
                        <div>
                          <p className="text-blue-200/60 text-[10px] uppercase">{parseFloat(filingDetails.advanceTaxPaid || 0) >= selectedResult.totalTax ? "Refund Due" : "Balance Due"}</p>
                          <p className={`font-bold ${parseFloat(filingDetails.advanceTaxPaid || 0) >= selectedResult.totalTax ? "text-emerald-300" : "text-rose-300"}`}>
                            {fmt(Math.abs(selectedResult.totalTax - parseFloat(filingDetails.advanceTaxPaid || 0)))}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* ITR Form + Disclaimer */}
                <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Recommended ITR Form</span>
                    <span className="px-3 py-1 bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm font-black rounded-full">{itrForm.form}</span>
                  </div>
                  <p className="text-xs text-slate-400 mb-4">{itrForm.reason}</p>
                  <AlertBox type="info">This tool assists in tax computation. For complex situations, consult a qualified Chartered Accountant. Verify all calculations before filing on the Income Tax Portal.</AlertBox>
                </div>

                {/* Actions */}
                <div className="flex gap-3">
                  <button onClick={saveProgress}
                    className="flex-1 bg-blue-600 hover:bg-blue-500 text-white py-4 rounded-2xl font-black text-xs uppercase flex items-center justify-center gap-2 shadow-2xl transition-all">
                    <Save size={16} /> Save All Data
                  </button>
                </div>
              </div>
            )}

          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};

export default ITRPage;
