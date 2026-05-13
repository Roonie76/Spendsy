import { useState, useMemo, useEffect } from "react";
import {
  ChevronRight, ChevronLeft, Check, FileText, User, Briefcase, Home as HomeIcon,
  TrendingUp, Globe, PiggyBank, Calculator, ClipboardList, AlertTriangle,
  CheckCircle, Info, ChevronDown, ChevronUp, IndianRupee,
} from "lucide-react";

// ─── Constants ────────────────────────────────────────────────────────────────

const ITR_TYPES = [
  {
    id: "ITR-1",
    label: "ITR-1 (Sahaj)",
    desc: "Salaried / pensioner, one house property, interest income. Total income ≤ ₹50L.",
    icon: User,
    badge: "Most common",
    badgeColor: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    accentColor: "border-emerald-500/50 bg-emerald-500/5",
    sections: ["personal", "salary", "houseProperty", "otherIncome", "deductions", "taxSummary", "review"],
    checklist: [
      "Income from salary or pension",
      "One house property (self-occupied or let-out)",
      "Interest from savings / FD",
      "Total income ≤ ₹50 lakh",
      "No capital gains",
      "No foreign assets",
    ],
  },
  {
    id: "ITR-2",
    label: "ITR-2",
    desc: "Capital gains, multiple properties, or foreign income/assets. No business income.",
    icon: TrendingUp,
    badge: "Investors",
    badgeColor: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
    accentColor: "border-indigo-500/50 bg-indigo-500/5",
    sections: ["personal", "salary", "houseProperty", "capitalGains", "foreignAssets", "otherIncome", "deductions", "taxSummary", "review"],
    checklist: [
      "Sold stocks, MF, or property",
      "2+ house properties",
      "Foreign assets / ESOPs / RSUs",
      "Income > ₹50 lakh",
      "No business/professional income",
    ],
  },
];

const SECTION_META = {
  selectITR:    { label: "Select Form",   icon: FileText },
  personal:     { label: "Personal",      icon: User },
  salary:       { label: "Salary",        icon: Briefcase },
  houseProperty:{ label: "Property",      icon: HomeIcon },
  capitalGains: { label: "Capital Gains", icon: TrendingUp },
  foreignAssets:{ label: "Foreign",       icon: Globe },
  otherIncome:  { label: "Other Income",  icon: IndianRupee },
  deductions:   { label: "Deductions",    icon: PiggyBank },
  taxSummary:   { label: "Tax Summary",   icon: Calculator },
  review:       { label: "Review",        icon: ClipboardList },
};

// ─── Tax Computation ──────────────────────────────────────────────────────────

const num = (v) => (isNaN(parseFloat(v)) ? 0 : parseFloat(v));

function calcNewRegimeTax(income) {
  const slabs = [
    { upto: 400000, rate: 0 },
    { upto: 800000, rate: 0.05 },
    { upto: 1200000, rate: 0.10 },
    { upto: 1600000, rate: 0.15 },
    { upto: 2000000, rate: 0.20 },
    { upto: 2400000, rate: 0.25 },
    { upto: Infinity, rate: 0.30 },
  ];
  let tax = 0, prev = 0;
  for (const s of slabs) {
    if (income <= prev) break;
    tax += (Math.min(income, s.upto) - prev) * s.rate;
    prev = s.upto;
  }
  // Sec 87A rebate: full tax rebate if income ≤ ₹12L
  if (income <= 1200000) tax = 0;
  return Math.round(tax);
}

function calcOldRegimeTax(income) {
  const slabs = [
    { upto: 250000, rate: 0 },
    { upto: 500000, rate: 0.05 },
    { upto: 1000000, rate: 0.20 },
    { upto: Infinity, rate: 0.30 },
  ];
  let tax = 0, prev = 0;
  for (const s of slabs) {
    if (income <= prev) break;
    tax += (Math.min(income, s.upto) - prev) * s.rate;
    prev = s.upto;
  }
  if (income <= 500000) tax = 0;
  return Math.round(tax);
}

const fmt = (n) =>
  n === "" || n === undefined || n === null
    ? "—"
    : "₹" + Number(n).toLocaleString("en-IN");

function useTaxCalc(formData, itrType) {
  return useMemo(() => {
    const d = formData;
    const isNew = (d.personal?.taxRegime || "new") === "new";
    const grossSalary = num(d.salary?.grossSalary);
    const stdDeduction = Math.min(75000, grossSalary);
    const netSalary = Math.max(0, grossSalary - stdDeduction);

    let hpIncome = 0;
    if (d.houseProperty?.propertyType === "letout") {
      const net = num(d.houseProperty?.rentalIncome) - num(d.houseProperty?.municipalTax);
      hpIncome = Math.max(0, net) * 0.7;
    }
    const homeLoanInt = Math.min(200000, num(d.houseProperty?.homeLoanInterest));
    const hpNet = hpIncome - (isNew ? 0 : homeLoanInt);

    const stcgEquity = num(d.capitalGains?.stcgEquity);
    const ltcgEquity = Math.max(0, num(d.capitalGains?.ltcgEquity) - 125000);
    const stcgDebt = num(d.capitalGains?.stcgDebt);
    const ltcgDebt = num(d.capitalGains?.ltcgDebt);

    const otherIncome = [
      d.otherIncome?.fdInterest, d.otherIncome?.dividendIncome,
      d.otherIncome?.otherInterest, d.otherIncome?.freelanceIncome, d.otherIncome?.anyOther,
    ].reduce((a, b) => a + num(b), 0);
    const winnings = num(d.otherIncome?.winnings);
    const savingsInt = num(d.otherIncome?.savingsInterest);
    const savingsDeduction = isNew ? 0 : Math.min(10000, num(d.deductions?.savingsInterest80TTA) || savingsInt);

    let deduc80C = 0, deduc80D = 0, deduc80CCD = 0, otherDeduc = 0;
    if (!isNew && d.deductions) {
      deduc80C = Math.min(150000, [
        d.deductions.epfPpf, d.deductions.elss, d.deductions.liPremium,
        d.deductions.nscFd, d.deductions.homeLoanPrincipal, d.deductions.tuitionFees,
      ].reduce((a, b) => a + num(b), 0));
      deduc80D = num(d.deductions.healthSelf) + num(d.deductions.healthParents);
      deduc80CCD = num(d.deductions.npsExtra);
      otherDeduc = num(d.deductions.educationLoan) + num(d.deductions.donations80G) + savingsDeduction;
    }
    const employerNPS = num(d.deductions?.employerNPS);
    const hraExemption = isNew ? 0 : num(d.deductions?.hraExemption);

    const slabIncome = Math.max(0,
      netSalary + hpNet + otherIncome + savingsInt
      - deduc80C - deduc80D - deduc80CCD - otherDeduc - employerNPS - hraExemption
    );

    let slabTax = isNew ? calcNewRegimeTax(slabIncome) : calcOldRegimeTax(slabIncome);
    const stcgEquityTax = Math.round(stcgEquity * 0.20);
    const ltcgEquityTax = Math.round(ltcgEquity * 0.125);
    const stcgDebtTax = isNew
      ? calcNewRegimeTax(slabIncome + stcgDebt) - slabTax
      : calcOldRegimeTax(slabIncome + stcgDebt) - slabTax;
    const ltcgDebtTax = Math.round(ltcgDebt * 0.125);
    const winningsTax = Math.round(winnings * 0.30);

    const totalTax = slabTax + stcgEquityTax + ltcgEquityTax + stcgDebtTax + ltcgDebtTax + winningsTax;
    const surcharge = totalTax > 5000000 ? Math.round(totalTax * 0.10)
      : totalTax > 1000000 ? Math.round(totalTax * 0.15) : 0;
    const cess = Math.round((totalTax + surcharge) * 0.04);
    const grossTax = totalTax + surcharge + cess;
    const tdsSalary = num(d.salary?.tdsSalary);
    const tdsOther = Math.round(num(d.otherIncome?.fdInterest) * 0.10);
    const totalTDS = tdsSalary + tdsOther;
    const netPayable = grossTax - totalTDS;

    return {
      grossSalary, stdDeduction, netSalary, hpNet, slabIncome,
      stcgEquity, ltcgEquity, stcgDebt, ltcgDebt, otherIncome, winnings,
      deduc80C, deduc80D, deduc80CCD, otherDeduc,
      slabTax, stcgEquityTax, ltcgEquityTax, winningsTax,
      totalTax, surcharge, cess, grossTax, totalTDS, netPayable,
    };
  }, [formData, itrType]);
}

// ─── Shared UI primitives ─────────────────────────────────────────────────────

const Field = ({ label, name, value, onChange, type = "text", hint, required, prefix }) => (
  <div className="space-y-1.5">
    <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wide">
      {label} {required && <span className="text-rose-400">*</span>}
    </label>
    {hint && <p className="text-[10px] text-slate-500">{hint}</p>}
    <div className="flex">
      {prefix && (
        <span className="px-3 py-2.5 bg-white/5 border border-r-0 border-white/10 rounded-l-lg text-slate-400 text-sm">
          {prefix}
        </span>
      )}
      <input
        type={type}
        name={name}
        value={value ?? ""}
        onChange={onChange}
        className={`w-full px-3 py-2.5 bg-black/30 border border-white/10 text-white text-sm placeholder:text-slate-600
          focus:outline-none focus:border-cyan-500/50 focus:bg-black/40 transition-colors
          ${prefix ? "rounded-r-lg" : "rounded-lg"}`}
      />
    </div>
  </div>
);

const SelectField = ({ label, name, value, onChange, options, hint }) => (
  <div className="space-y-1.5">
    <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wide">{label}</label>
    {hint && <p className="text-[10px] text-slate-500">{hint}</p>}
    <select
      name={name}
      value={value ?? ""}
      onChange={onChange}
      className="w-full px-3 py-2.5 bg-black/30 border border-white/10 rounded-lg text-white text-sm
        focus:outline-none focus:border-cyan-500/50 transition-colors cursor-pointer"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value} className="bg-slate-900">{o.label}</option>
      ))}
    </select>
  </div>
);

const SectionCard = ({ title, children, icon: Icon }) => (
  <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-5 mb-5">
    {title && (
      <div className="flex items-center gap-2 mb-4">
        {Icon && <Icon className="w-3.5 h-3.5 text-cyan-400" />}
        <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-widest">{title}</span>
      </div>
    )}
    {children}
  </div>
);

const InfoBox = ({ variant = "info", children }) => {
  const styles = {
    info:    "bg-blue-500/8 border-blue-500/20 text-blue-200",
    warn:    "bg-amber-500/8 border-amber-500/20 text-amber-200",
    danger:  "bg-rose-500/8 border-rose-500/20 text-rose-200",
    success: "bg-emerald-500/8 border-emerald-500/20 text-emerald-200",
  };
  const icons = { info: Info, warn: AlertTriangle, danger: AlertTriangle, success: CheckCircle };
  const Ic = icons[variant] || Info;
  return (
    <div className={`flex gap-2.5 p-3.5 rounded-xl border mb-4 text-xs leading-relaxed ${styles[variant]}`}>
      <Ic className="w-4 h-4 shrink-0 mt-0.5 opacity-80" />
      <div>{children}</div>
    </div>
  );
};

const Grid2 = ({ children }) => (
  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">{children}</div>
);

// ─── Section Steps ────────────────────────────────────────────────────────────

function StepSelectITR({ value, onChange }) {
  const [showHelper, setShowHelper] = useState(false);
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Which ITR form applies to you?</h2>
        <p className="text-sm text-slate-400">Individual filing only · FY 2025-26 (AY 2026-27) · Deadline: <span className="text-cyan-400 font-semibold">31 July 2026</span></p>
      </div>

      <button
        onClick={() => setShowHelper((v) => !v)}
        className="flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 transition-colors font-semibold"
      >
        {showHelper ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        {showHelper ? "Hide decision guide" : "Not sure which to pick?"}
      </button>

      {showHelper && (
        <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-4 grid grid-cols-2 gap-4">
          {[
            { color: "text-emerald-400", label: "Use ITR-1 if you…", items: ["Salaried or pensioner", "Only one house property", "Savings / FD interest only", "Income ≤ ₹50L", "No stocks / MF / property sale"] },
            { color: "text-indigo-400", label: "Use ITR-2 if you…", items: ["Sold stocks, MFs, or property", "2+ house properties", "Foreign assets / ESOPs / RSUs", "Income > ₹50L", "No business income"] },
          ].map((col) => (
            <div key={col.label}>
              <p className={`text-xs font-bold mb-2 ${col.color}`}>{col.label}</p>
              {col.items.map((s) => (
                <p key={s} className="text-xs text-slate-300 mb-1 flex gap-1.5"><span className={col.color}>·</span>{s}</p>
              ))}
            </div>
          ))}
          <div className="col-span-2 mt-1 p-3 rounded-xl bg-amber-500/8 border border-amber-500/20 text-xs text-amber-200">
            <AlertTriangle className="w-3.5 h-3.5 inline mr-1.5 mb-0.5" />
            Business / freelance income requires <strong>ITR-3 or ITR-4</strong> — separate process, not covered here.
          </div>
        </div>
      )}

      <div className="space-y-3">
        {ITR_TYPES.map((t) => {
          const Icon = t.icon;
          const isSelected = value === t.id;
          return (
            <div
              key={t.id}
              onClick={() => onChange(t.id)}
              className={`rounded-2xl border-2 p-5 cursor-pointer transition-all duration-200
                ${isSelected ? t.accentColor : "border-white/8 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]"}`}
            >
              <div className="flex items-center gap-4">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-colors
                  ${isSelected ? "bg-white/10" : "bg-white/5"}`}>
                  <Icon className={`w-5 h-5 ${isSelected ? "text-white" : "text-slate-400"}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className={`font-bold text-sm ${isSelected ? "text-white" : "text-slate-200"}`}>{t.label}</span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${t.badgeColor}`}>{t.badge}</span>
                  </div>
                  <p className="text-xs text-slate-400 leading-snug">{t.desc}</p>
                </div>
                <div className={`w-5 h-5 rounded-full border-2 shrink-0 flex items-center justify-center transition-all
                  ${isSelected ? "border-white bg-white" : "border-slate-600"}`}>
                  {isSelected && <Check className="w-3 h-3 text-slate-900" />}
                </div>
              </div>
              {isSelected && (
                <div className="mt-4 pt-4 border-t border-white/10 grid grid-cols-2 gap-x-4 gap-y-1.5">
                  {t.checklist.map((c) => (
                    <p key={c} className="text-xs text-slate-300 flex gap-1.5">
                      <Check className="w-3 h-3 text-emerald-400 shrink-0 mt-0.5" />{c}
                    </p>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StepPersonal({ data, onChange }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Personal Information</h2>
        <p className="text-sm text-slate-400">Basic details as per your PAN card.</p>
      </div>
      <InfoBox variant="info">
        Assessment Year: <strong>AY 2026-27</strong> — for income earned in FY 2025-26 (Apr 2025 – Mar 2026)
      </InfoBox>
      <SectionCard title="Identity" icon={User}>
        <Grid2>
          <Field label="Full Name" name="name" value={data.name} onChange={onChange} required />
          <Field label="PAN" name="pan" value={data.pan} onChange={onChange} hint="10-character alphanumeric" required />
          <Field label="Date of Birth" name="dob" value={data.dob} onChange={onChange} type="date" required />
          <Field label="Aadhaar Number" name="aadhaar" value={data.aadhaar} onChange={onChange} hint="12-digit" />
          <Field label="Email Address" name="email" value={data.email} onChange={onChange} type="email" required />
          <Field label="Mobile Number" name="mobile" value={data.mobile} onChange={onChange} type="tel" required />
        </Grid2>
      </SectionCard>
      <SectionCard title="Address" icon={HomeIcon}>
        <div className="space-y-4">
          <Field label="Flat / Door No., Street" name="addr1" value={data.addr1} onChange={onChange} />
          <Grid2>
            <Field label="City" name="city" value={data.city} onChange={onChange} />
            <Field label="State" name="state" value={data.state} onChange={onChange} />
            <Field label="PIN Code" name="pin" value={data.pin} onChange={onChange} />
            <Field label="Country" name="country" value={data.country || "India"} onChange={onChange} />
          </Grid2>
        </div>
      </SectionCard>
      <SectionCard title="Tax Regime" icon={Calculator}>
        <InfoBox variant="warn">
          <strong>New Regime</strong> is the default from FY 2023-24. Lower slab rates but no deductions (80C, HRA, etc.).
          Switch to <strong>Old Regime</strong> only if your deductions make it beneficial.
        </InfoBox>
        <SelectField
          label="Choose Tax Regime"
          name="taxRegime"
          value={data.taxRegime || "new"}
          onChange={onChange}
          options={[
            { value: "new", label: "New Regime (Default) — Lower rates, no deductions" },
            { value: "old", label: "Old Regime — Higher rates, deductions allowed (80C, HRA…)" },
          ]}
        />
      </SectionCard>
      <SectionCard title="Bank Account (for Refund)" icon={IndianRupee}>
        <InfoBox variant="info">Pre-validate your bank account on the Income Tax portal. Refunds are credited only to pre-validated accounts.</InfoBox>
        <Grid2>
          <Field label="Bank Name" name="bankName" value={data.bankName} onChange={onChange} required />
          <Field label="Account Number" name="bankAccount" value={data.bankAccount} onChange={onChange} required />
          <Field label="IFSC Code" name="ifsc" value={data.ifsc} onChange={onChange} required />
          <SelectField label="Account Type" name="accountType" value={data.accountType || "savings"} onChange={onChange}
            options={[{ value: "savings", label: "Savings" }, { value: "current", label: "Current" }]} />
        </Grid2>
      </SectionCard>
    </div>
  );
}

function StepSalary({ data, onChange }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Salary Income</h2>
        <p className="text-sm text-slate-400">Enter details from your Form 16 issued by your employer.</p>
      </div>
      <SectionCard title="Employer Details" icon={Briefcase}>
        <Grid2>
          <Field label="Employer Name" name="employerName" value={data.employerName} onChange={onChange} />
          <Field label="Employer TAN" name="employerTan" value={data.employerTan} onChange={onChange} hint="From Form 16" />
        </Grid2>
      </SectionCard>
      <SectionCard title="Income Breakup" icon={Calculator}>
        <Grid2>
          <Field label="Basic Salary" name="basicSalary" value={data.basicSalary} onChange={onChange} type="number" prefix="₹" />
          <Field label="HRA Received" name="hraReceived" value={data.hraReceived} onChange={onChange} type="number" prefix="₹" />
          <Field label="Special Allowance" name="specialAllowance" value={data.specialAllowance} onChange={onChange} type="number" prefix="₹" />
          <Field label="Other Allowances" name="otherAllowance" value={data.otherAllowance} onChange={onChange} type="number" prefix="₹" />
          <Field label="Perquisites / Bonuses" name="perquisites" value={data.perquisites} onChange={onChange} type="number" prefix="₹" />
          <Field label="Gross Salary (Form 16)" name="grossSalary" value={data.grossSalary} onChange={onChange} type="number" prefix="₹" hint="As per Form 16 Part B" />
        </Grid2>
      </SectionCard>
      <SectionCard title="TDS & Standard Deduction" icon={FileText}>
        <Grid2>
          <Field label="TDS Deducted by Employer" name="tdsSalary" value={data.tdsSalary} onChange={onChange} type="number" prefix="₹" hint="Form 16 Part A" />
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wide">Standard Deduction (auto)</label>
            <p className="text-[10px] text-slate-500">₹75,000 standard deduction (FY 2025-26)</p>
            <div className="px-3 py-2.5 bg-emerald-500/8 border border-emerald-500/20 rounded-lg text-emerald-300 text-sm font-semibold">₹75,000</div>
          </div>
        </Grid2>
      </SectionCard>
    </div>
  );
}

function StepHouseProperty({ data, onChange }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">House Property Income</h2>
        <p className="text-sm text-slate-400">Self-occupied or let-out property details.</p>
      </div>
      <SectionCard title="Property Details" icon={HomeIcon}>
        <div className="space-y-4">
          <SelectField
            label="Property Type"
            name="propertyType"
            value={data.propertyType || "self"}
            onChange={onChange}
            options={[
              { value: "self", label: "Self-Occupied" },
              { value: "letout", label: "Let-Out (Rented)" },
              { value: "deemed", label: "Deemed Let-Out" },
            ]}
          />
          {data.propertyType === "letout" && (
            <Grid2>
              <Field label="Annual Rental Income" name="rentalIncome" value={data.rentalIncome} onChange={onChange} type="number" prefix="₹" />
              <Field label="Municipal Taxes Paid" name="municipalTax" value={data.municipalTax} onChange={onChange} type="number" prefix="₹" />
            </Grid2>
          )}
        </div>
      </SectionCard>
      <SectionCard title="Home Loan Interest — Sec 24b" icon={Calculator}>
        <Grid2>
          <Field label="Interest on Home Loan" name="homeLoanInterest" value={data.homeLoanInterest} onChange={onChange} type="number" prefix="₹"
            hint="Max ₹2L deduction for self-occupied (old regime)" />
          <Field label="Pre-construction Interest" name="preConstrInterest" value={data.preConstrInterest} onChange={onChange} type="number" prefix="₹" />
        </Grid2>
      </SectionCard>
    </div>
  );
}

function StepCapitalGains({ data, onChange }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Capital Gains</h2>
        <p className="text-sm text-slate-400">Income from sale of stocks, mutual funds, property, etc.</p>
      </div>
      <InfoBox variant="danger">
        <strong>STCG (Equity/MF &lt;1 yr):</strong> Taxed at 20% · <strong>LTCG (Equity/MF &gt;1 yr):</strong> 12.5% on gains above ₹1.25L exemption (Budget 2024 rates)
      </InfoBox>
      <SectionCard title="Equity & Mutual Funds" icon={TrendingUp}>
        <Grid2>
          <Field label="STCG — Equity / Equity MF" name="stcgEquity" value={data.stcgEquity} onChange={onChange} type="number" prefix="₹" hint="Taxed @ 20%" />
          <Field label="LTCG — Equity / Equity MF" name="ltcgEquity" value={data.ltcgEquity} onChange={onChange} type="number" prefix="₹" hint="12.5% above ₹1.25L" />
          <Field label="STCG — Debt MF / Others" name="stcgDebt" value={data.stcgDebt} onChange={onChange} type="number" prefix="₹" hint="Added to income, taxed at slab" />
          <Field label="LTCG — Debt MF / Others" name="ltcgDebt" value={data.ltcgDebt} onChange={onChange} type="number" prefix="₹" hint="12.5% without indexation" />
        </Grid2>
      </SectionCard>
      <SectionCard title="Immovable Property" icon={HomeIcon}>
        <Grid2>
          <Field label="Sale Consideration" name="propertySale" value={data.propertySale} onChange={onChange} type="number" prefix="₹" />
          <Field label="Indexed Cost of Acquisition" name="propertyIndexedCost" value={data.propertyIndexedCost} onChange={onChange} type="number" prefix="₹" />
          <Field label="Improvement Cost" name="propertyImprovCost" value={data.propertyImprovCost} onChange={onChange} type="number" prefix="₹" />
          <Field label="Transfer Expenses" name="propertyTransferExp" value={data.propertyTransferExp} onChange={onChange} type="number" prefix="₹" />
        </Grid2>
      </SectionCard>
    </div>
  );
}

function StepForeignAssets({ data, onChange }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Foreign Assets & Income</h2>
        <p className="text-sm text-slate-400">Mandatory disclosure for resident taxpayers — Schedule FA.</p>
      </div>
      <InfoBox variant="danger">
        Non-disclosure of foreign assets attracts penalties under the Black Money Act. Disclose all foreign bank accounts, investments, property, and ESOP/RSU holdings.
      </InfoBox>
      <SectionCard title="Foreign Bank Accounts" icon={Globe}>
        <div className="space-y-4">
          <Field label="Foreign Bank Account Details" name="foreignBankDetails" value={data.foreignBankDetails} onChange={onChange}
            hint="Country, bank name, account number, peak balance" />
          <Field label="Peak Balance (INR equivalent)" name="foreignBankBalance" value={data.foreignBankBalance} onChange={onChange} type="number" prefix="₹" />
        </div>
      </SectionCard>
      <SectionCard title="Foreign Investments / ESOPs" icon={TrendingUp}>
        <Grid2>
          <Field label="Value of Foreign Investments" name="foreignInvValue" value={data.foreignInvValue} onChange={onChange} type="number" prefix="₹" />
          <Field label="ESOP / RSU Value (on vesting)" name="esopValue" value={data.esopValue} onChange={onChange} type="number" prefix="₹"
            hint="Taxable as perquisite in year of vesting" />
        </Grid2>
      </SectionCard>
    </div>
  );
}

function StepOtherIncome({ data, onChange }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Other Income</h2>
        <p className="text-sm text-slate-400">Interest, dividends, freelance, and any other sources.</p>
      </div>
      <SectionCard title="Interest & Dividends" icon={IndianRupee}>
        <Grid2>
          <Field label="Savings Account Interest" name="savingsInterest" value={data.savingsInterest} onChange={onChange} type="number" prefix="₹" hint="Sec 80TTA exemption up to ₹10k (old regime)" />
          <Field label="FD / RD Interest" name="fdInterest" value={data.fdInterest} onChange={onChange} type="number" prefix="₹" hint="Fully taxable at slab rate" />
          <Field label="Dividend Income" name="dividendIncome" value={data.dividendIncome} onChange={onChange} type="number" prefix="₹" hint="Taxable as per slab" />
          <Field label="Any Other Interest" name="otherInterest" value={data.otherInterest} onChange={onChange} type="number" prefix="₹" />
        </Grid2>
      </SectionCard>
      <SectionCard title="Other Sources" icon={Briefcase}>
        <Grid2>
          <Field label="Freelance / Consultancy" name="freelanceIncome" value={data.freelanceIncome} onChange={onChange} type="number" prefix="₹" />
          <Field label="Agricultural Income" name="agriIncome" value={data.agriIncome} onChange={onChange} type="number" prefix="₹" hint="Exempt but used for rate calc" />
          <Field label="Gifts / Lottery / Winnings" name="winnings" value={data.winnings} onChange={onChange} type="number" prefix="₹" hint="Flat 30% tax" />
          <Field label="Any Other Income" name="anyOther" value={data.anyOther} onChange={onChange} type="number" prefix="₹" />
        </Grid2>
      </SectionCard>
    </div>
  );
}

function StepDeductions({ data, onChange, taxRegime }) {
  if (taxRegime === "new") {
    return (
      <div className="space-y-5">
        <div>
          <h2 className="text-xl font-bold text-white mb-1">Deductions</h2>
        </div>
        <InfoBox variant="warn">
          You selected the <strong>New Tax Regime</strong>. Most deductions (80C, 80D, HRA) are <strong>not available</strong>.
          Only Standard Deduction (₹75,000), employer NPS (80CCD(2)), and Agniveer corpus remain.
        </InfoBox>
        <SectionCard title="Available Under New Regime" icon={PiggyBank}>
          <Field label="Employer NPS Contribution — Sec 80CCD(2)" name="employerNPS" value={data.employerNPS} onChange={onChange} type="number" prefix="₹" hint="Max 10% of basic salary" />
        </SectionCard>
      </div>
    );
  }
  const total80C = Math.min(150000, [data.epfPpf, data.elss, data.liPremium, data.nscFd, data.homeLoanPrincipal, data.tuitionFees].reduce((a, b) => a + num(b), 0));
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Deductions — Chapter VI-A</h2>
        <p className="text-sm text-slate-400">Old Regime — enter eligible deductions to reduce taxable income.</p>
      </div>
      <SectionCard title="Sec 80C — Investments (Max ₹1,50,000)" icon={PiggyBank}>
        <Grid2>
          <Field label="EPF / PPF" name="epfPpf" value={data.epfPpf} onChange={onChange} type="number" prefix="₹" />
          <Field label="ELSS Mutual Funds" name="elss" value={data.elss} onChange={onChange} type="number" prefix="₹" />
          <Field label="Life Insurance Premium" name="liPremium" value={data.liPremium} onChange={onChange} type="number" prefix="₹" />
          <Field label="NSC / Tax-saving FDs" name="nscFd" value={data.nscFd} onChange={onChange} type="number" prefix="₹" />
          <Field label="Home Loan Principal" name="homeLoanPrincipal" value={data.homeLoanPrincipal} onChange={onChange} type="number" prefix="₹" />
          <Field label="Children Tuition Fees" name="tuitionFees" value={data.tuitionFees} onChange={onChange} type="number" prefix="₹" />
        </Grid2>
        <div className="mt-3 flex items-center justify-between p-3 rounded-xl bg-cyan-500/8 border border-cyan-500/20">
          <span className="text-xs text-slate-300">80C Total</span>
          <span className={`text-sm font-bold ${total80C >= 150000 ? "text-emerald-400" : "text-cyan-400"}`}>
            {fmt(total80C)} {total80C >= 150000 ? "✓ Maxed" : `/ ₹1,50,000`}
          </span>
        </div>
      </SectionCard>
      <SectionCard title="Health & NPS" icon={Calculator}>
        <Grid2>
          <Field label="Health Ins. — Self (Sec 80D)" name="healthSelf" value={data.healthSelf} onChange={onChange} type="number" prefix="₹" hint="Max ₹25k (₹50k if senior citizen)" />
          <Field label="Health Ins. — Parents (Sec 80D)" name="healthParents" value={data.healthParents} onChange={onChange} type="number" prefix="₹" hint="Max ₹25k (₹50k if senior)" />
          <Field label="NPS — Self (Sec 80CCD(1B))" name="npsExtra" value={data.npsExtra} onChange={onChange} type="number" prefix="₹" hint="Additional ₹50k over 80C limit" />
          <Field label="Employer NPS (Sec 80CCD(2))" name="employerNPS" value={data.employerNPS} onChange={onChange} type="number" prefix="₹" hint="Max 10% of basic" />
        </Grid2>
      </SectionCard>
      <SectionCard title="Other Deductions" icon={FileText}>
        <Grid2>
          <Field label="HRA Exemption (Sec 10(13A))" name="hraExemption" value={data.hraExemption} onChange={onChange} type="number" prefix="₹" />
          <Field label="LTA Exemption (Sec 10(5))" name="ltaExemption" value={data.ltaExemption} onChange={onChange} type="number" prefix="₹" />
          <Field label="Education Loan Interest (Sec 80E)" name="educationLoan" value={data.educationLoan} onChange={onChange} type="number" prefix="₹" hint="No upper limit, 8 yrs" />
          <Field label="Donations (Sec 80G)" name="donations80G" value={data.donations80G} onChange={onChange} type="number" prefix="₹" />
          <Field label="Savings Interest (Sec 80TTA)" name="savingsInterest80TTA" value={data.savingsInterest80TTA} onChange={onChange} type="number" prefix="₹" hint="Max ₹10k exemption" />
        </Grid2>
      </SectionCard>
    </div>
  );
}

function StepTaxSummary({ formData }) {
  const t = useTaxCalc(formData);
  const isNew = (formData.personal?.taxRegime || "new") === "new";

  const Row = ({ label, value, bold, color, sep }) => (
    <>
      {sep && <div className="border-t border-white/8 my-2" />}
      <div className="flex justify-between py-1.5">
        <span className={`text-sm ${bold ? "font-semibold text-white" : "text-slate-300"}`}>{label}</span>
        <span className={`text-sm font-semibold ${color || (bold ? "text-white" : "text-slate-200")}`}>{fmt(value)}</span>
      </div>
    </>
  );

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Tax Summary</h2>
        <p className="text-sm text-slate-400">Auto-calculated based on your entries. Review before proceeding.</p>
      </div>
      <InfoBox variant={isNew ? "success" : "warn"}>
        Regime: <strong>{isNew ? "New Regime (FY 2025-26)" : "Old Regime (FY 2025-26)"}</strong>
      </InfoBox>
      <SectionCard title="Income Computation" icon={Calculator}>
        <Row label="Gross Salary" value={t.grossSalary} />
        <Row label="Less: Standard Deduction" value={-t.stdDeduction} color="text-emerald-400" />
        <Row label="Net Salary Income" value={t.netSalary} bold sep />
        {t.hpNet !== 0 && <Row label="House Property Income / (Loss)" value={t.hpNet} />}
        {t.otherIncome > 0 && <Row label="Other Income" value={t.otherIncome} />}
        {!isNew && (t.deduc80C + t.deduc80D + t.deduc80CCD + t.otherDeduc) > 0 && (
          <Row label="Less: Deductions (Ch. VI-A)" value={-(t.deduc80C + t.deduc80D + t.deduc80CCD + t.otherDeduc)} color="text-emerald-400" />
        )}
        <Row label="Taxable Income (Slab)" value={t.slabIncome} bold sep />
      </SectionCard>
      <SectionCard title="Tax Calculation" icon={IndianRupee}>
        <Row label="Tax on Slab Income" value={t.slabTax} />
        {t.stcgEquity > 0 && <Row label={`STCG Tax — Equity (20%)`} value={t.stcgEquityTax} />}
        {t.ltcgEquity > 0 && <Row label={`LTCG Tax — Equity (12.5%)`} value={t.ltcgEquityTax} />}
        {t.winnings > 0 && <Row label={`Tax on Winnings (30%)`} value={t.winningsTax} />}
        <Row label="Total Tax (before surcharge & cess)" value={t.totalTax} bold sep />
        {t.surcharge > 0 && <Row label="Surcharge" value={t.surcharge} />}
        <Row label="Health & Education Cess (4%)" value={t.cess} />
        <Row label="Gross Tax Liability" value={t.grossTax} bold sep />
      </SectionCard>
      <SectionCard title="Tax Already Paid" icon={CheckCircle}>
        <Row label="TDS Deducted (Salary + Others)" value={t.totalTDS} color="text-emerald-400" />
        <Row label="Advance Tax Paid" value={t.advanceTax || 0} color="text-emerald-400" />
      </SectionCard>
      <div className={`rounded-2xl border-2 p-5 ${t.netPayable > 0 ? "border-rose-500/40 bg-rose-500/8" : "border-emerald-500/40 bg-emerald-500/8"}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {t.netPayable > 0 ? <AlertTriangle className="w-5 h-5 text-rose-400" /> : <CheckCircle className="w-5 h-5 text-emerald-400" />}
            <span className={`text-sm font-bold ${t.netPayable > 0 ? "text-rose-300" : "text-emerald-300"}`}>
              {t.netPayable > 0 ? "Tax Payable (Self-Assessment)" : "Refund Due"}
            </span>
          </div>
          <span className={`text-2xl font-black ${t.netPayable > 0 ? "text-rose-400" : "text-emerald-400"}`}>
            {fmt(Math.abs(t.netPayable))}
          </span>
        </div>
        <p className={`text-xs mt-2 ${t.netPayable > 0 ? "text-rose-300/70" : "text-emerald-300/70"}`}>
          {t.netPayable > 0
            ? "Pay via Challan 280 (Self-Assessment Tax) on incometax.gov.in before submitting. Interest under Sec 234B applies if unpaid."
            : "Refund will be credited to your pre-validated bank account after processing."}
        </p>
      </div>
    </div>
  );
}

function StepReview({ formData, itrType, taxCalc }) {
  const t = taxCalc;
  const p = formData.personal || {};
  const Pair = ({ label, value }) => value ? (
    <div className="flex gap-3 py-1.5 border-b border-white/5">
      <span className="text-xs text-slate-400 w-36 shrink-0">{label}</span>
      <span className="text-xs font-semibold text-white">{value}</span>
    </div>
  ) : null;

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-white mb-1">Review & Submit</h2>
        <p className="text-sm text-slate-400">Review all details. E-verify within 30 days after submission.</p>
      </div>
      <InfoBox variant="danger">
        <strong>UI Prototype only.</strong> Do NOT enter real PAN, Aadhaar, or financial data here.
        Actual ITR filing must be done at <strong>incometax.gov.in</strong>.
      </InfoBox>
      <SectionCard title="Filing Details" icon={FileText}>
        <Pair label="ITR Form" value={itrType} />
        <Pair label="Assessment Year" value="AY 2026-27 (FY 2025-26)" />
        <Pair label="Tax Regime" value={p.taxRegime === "new" ? "New Regime" : "Old Regime"} />
        <Pair label="Name" value={p.name} />
        <Pair label="PAN" value={p.pan} />
        <Pair label="Email" value={p.email} />
      </SectionCard>
      <SectionCard title="Income Summary" icon={Calculator}>
        <Pair label="Gross Salary" value={fmt(t?.grossSalary)} />
        <Pair label="Taxable Income" value={fmt(t?.slabIncome)} />
        <Pair label="Gross Tax Liability" value={fmt(t?.grossTax)} />
        <Pair label="TDS Deducted" value={fmt(t?.totalTDS)} />
        <Pair label={t?.netPayable > 0 ? "Tax Payable" : "Refund Due"} value={fmt(Math.abs(t?.netPayable || 0))} />
      </SectionCard>
      <SectionCard title="Next Steps After Submission" icon={ClipboardList}>
        <div className="space-y-2 text-sm text-slate-300">
          <p>1. <span className="text-white font-semibold">E-verify within 30 days</span> — via Aadhaar OTP, Net Banking, or DSC</p>
          {t?.netPayable > 0 && <p>2. <span className="text-white font-semibold">Pay self-assessment tax</span> via Challan 280 before submitting</p>}
          <p>{t?.netPayable > 0 ? "3." : "2."} <span className="text-white font-semibold">Ensure bank account is pre-validated</span> on the portal</p>
          <p>{t?.netPayable > 0 ? "4." : "3."} <span className="text-white font-semibold">Track refund / processing</span> at incometax.gov.in → e-File → ITR Status</p>
        </div>
      </SectionCard>
      <p className="text-xs text-slate-500 text-center border-t border-white/5 pt-4">
        By clicking "Submit Return" you confirm all information is accurate to the best of your knowledge.
      </p>
    </div>
  );
}

// ─── Progress Stepper ─────────────────────────────────────────────────────────

function ProgressStepper({ steps, currentStep, onStepClick }) {
  return (
    <div className="flex items-center overflow-x-auto pb-1 mb-6 no-scrollbar gap-0">
      {steps.map((s, i) => {
        const meta = SECTION_META[s] || { label: s, icon: FileText };
        const Icon = meta.icon;
        const done = i < currentStep;
        const active = i === currentStep;
        return (
          <div key={s} className="flex items-center shrink-0">
            <button
              onClick={() => done && onStepClick(i)}
              disabled={!done}
              className={`flex flex-col items-center gap-1 transition-all ${done ? "cursor-pointer" : "cursor-default"}`}
            >
              <div className={`w-7 h-7 rounded-full flex items-center justify-center transition-all
                ${done ? "bg-cyan-500 text-white" : active ? "bg-white/10 border-2 border-cyan-500 text-cyan-400" : "bg-white/5 border border-white/15 text-slate-500"}`}>
                {done ? <Check className="w-3.5 h-3.5" /> : <Icon className="w-3.5 h-3.5" />}
              </div>
              <span className={`text-[9px] font-semibold whitespace-nowrap transition-colors
                ${active ? "text-cyan-400" : done ? "text-cyan-500/70" : "text-slate-500"}`}>
                {meta.label}
              </span>
            </button>
            {i < steps.length - 1 && (
              <div className={`w-6 h-px mx-1 mb-4 transition-colors ${i < currentStep ? "bg-cyan-500" : "bg-white/10"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Main Wizard ──────────────────────────────────────────────────────────────

export default function ITRFilingWizard({ autofillData, user, showToast, theme }) {
  const [selectedITR, setSelectedITR] = useState("");
  const [sectionStep, setSectionStep] = useState(0);
  const [formData, setFormData] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [ackNo] = useState(() => Math.floor(Math.random() * 9000000000) + 1000000000);

  useEffect(() => {
    if (!autofillData || Object.keys(autofillData).length === 0) return;
    setFormData((prev) => {
      function deepMerge(target, source) {
        const out = { ...target };
        for (const key of Object.keys(source || {})) {
          if (source[key] !== null && source[key] !== undefined && typeof source[key] === "object" && !Array.isArray(source[key])) {
            out[key] = deepMerge(target[key] || {}, source[key]);
          } else if (source[key] !== null && source[key] !== undefined) {
            out[key] = source[key];
          }
        }
        return out;
      }
      return deepMerge(prev, autofillData);
    });
  }, [autofillData]);

  const selectedType = ITR_TYPES.find((t) => t.id === selectedITR);
  const sections = selectedType ? ["selectITR", ...selectedType.sections] : ["selectITR"];
  const taxCalc = useTaxCalc(formData, selectedITR);
  const currentSection = sections[sectionStep];
  const isLastStep = sectionStep === sections.length - 1;
  const canGoNext = currentSection !== "selectITR" || selectedITR !== "";

  const handleFieldChange = (section) => (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [section]: { ...(prev[section] || {}), [name]: value } }));
  };

  const renderSection = () => {
    switch (currentSection) {
      case "selectITR":     return <StepSelectITR value={selectedITR} onChange={(v) => setSelectedITR(v)} />;
      case "personal":      return <StepPersonal data={formData.personal || {}} onChange={handleFieldChange("personal")} />;
      case "salary":        return <StepSalary data={formData.salary || {}} onChange={handleFieldChange("salary")} />;
      case "houseProperty": return <StepHouseProperty data={formData.houseProperty || {}} onChange={handleFieldChange("houseProperty")} />;
      case "capitalGains":  return <StepCapitalGains data={formData.capitalGains || {}} onChange={handleFieldChange("capitalGains")} />;
      case "foreignAssets": return <StepForeignAssets data={formData.foreignAssets || {}} onChange={handleFieldChange("foreignAssets")} />;
      case "otherIncome":   return <StepOtherIncome data={formData.otherIncome || {}} onChange={handleFieldChange("otherIncome")} />;
      case "deductions":    return <StepDeductions data={formData.deductions || {}} onChange={handleFieldChange("deductions")} taxRegime={formData.personal?.taxRegime || "new"} />;
      case "taxSummary":    return <StepTaxSummary formData={formData} itrType={selectedITR} />;
      case "review":        return <StepReview formData={formData} itrType={selectedITR} taxCalc={taxCalc} />;
      default: return null;
    }
  };

  if (submitted) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="max-w-md w-full rounded-3xl border border-white/10 bg-gradient-to-br from-emerald-900/30 to-slate-900/50 p-10 text-center shadow-2xl">
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center mx-auto mb-5">
            <CheckCircle className="w-8 h-8 text-emerald-400" />
          </div>
          <h2 className="text-2xl font-black text-white mb-2">Return Submitted!</h2>
          <p className="text-sm text-slate-300 mb-6 leading-relaxed">
            Your <strong className="text-white">{selectedITR}</strong> for AY 2026-27 has been submitted.<br />
            <span className="text-emerald-400 font-semibold">E-verify within 30 days</span> via Aadhaar OTP.<br />
            Track at incometax.gov.in → e-File → ITR Status.
          </p>
          <div className="bg-emerald-500/8 border border-emerald-500/20 rounded-2xl px-5 py-4 mb-6">
            <p className="text-xs text-emerald-300/70 mb-1 font-semibold uppercase tracking-wider">Acknowledgement No.</p>
            <p className="text-xl font-black text-emerald-400 tracking-widest">{ackNo}</p>
          </div>
          <button
            onClick={() => { setSubmitted(false); setSectionStep(0); setSelectedITR(""); setFormData({}); }}
            className="px-6 py-3 rounded-xl bg-white/10 hover:bg-white/15 text-white text-sm font-semibold transition-all"
          >
            File Another Return
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-0">
      {/* Wizard header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
            <FileText className="w-4.5 h-4.5 text-cyan-400" />
          </div>
          <div>
            <p className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Individual ITR · FY 2025-26</p>
            <p className="text-[10px] text-slate-500">No audit required · Deadline 31 Jul 2026</p>
          </div>
        </div>
        {selectedITR && (
          <span className="px-3 py-1 rounded-full text-xs font-bold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
            {selectedITR}
          </span>
        )}
      </div>

      {/* Main card */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden">
        {/* Progress */}
        {selectedITR && (
          <div className="px-6 pt-5 border-b border-white/5">
            <ProgressStepper steps={sections} currentStep={sectionStep} onStepClick={setSectionStep} />
          </div>
        )}

        {/* Section content */}
        <div className="p-6 min-h-[400px]">
          {renderSection()}
        </div>

        {/* Navigation */}
        <div className="px-6 py-4 border-t border-white/8 flex justify-between items-center">
          <button
            onClick={() => setSectionStep((s) => Math.max(0, s - 1))}
            disabled={sectionStep === 0}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-white/10 text-sm font-semibold transition-all
              disabled:opacity-30 disabled:cursor-not-allowed hover:bg-white/5 text-slate-300"
          >
            <ChevronLeft className="w-4 h-4" /> Back
          </button>

          {!isLastStep ? (
            <button
              onClick={() => { if (canGoNext) setSectionStep((s) => s + 1); }}
              disabled={!canGoNext}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-900 text-sm font-bold shadow-lg shadow-cyan-500/20 transition-all
                disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {sectionStep === 0 && !selectedITR ? "Select a form to continue" : "Continue"} <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={() => setSubmitted(true)}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-white text-sm font-bold shadow-lg shadow-emerald-500/20 transition-all"
            >
              <Check className="w-4 h-4" /> Submit Return
            </button>
          )}
        </div>
      </div>

      <p className="text-[10px] text-slate-600 text-center pt-3">
        UI prototype · Tax calculations indicative only · Actual filing at incometax.gov.in
      </p>
    </div>
  );
}
