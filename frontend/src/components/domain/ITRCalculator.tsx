// Database needed 
import { useState, useMemo } from "react";
import { cn } from "@shared/utils/cn";

// Types for ITR Calculator
interface IncomeDetails {
  salary: number;
  housePropertyIncome: number;
  businessIncome: number;
  capitalGains: number;
  otherIncome: number;
  interestIncome: number;
}

interface Deductions {
  section80C: number; // Max 1.5L - PPF, ELSS, LIC, etc.
  section80D: number; // Max 25K/50K - Medical Insurance
  section80E: number; // Education Loan Interest
  section80G: number; // Donations
  hra: number;
  standardDeduction: number;
  homeLoanInterest: number; // Max 2L
  nps80CCD: number; // Max 50K additional
}

interface TaxResult {
  grossIncome: number;
  totalDeductions: number;
  taxableIncome: number;
  taxBeforeCess: number;
  cess: number;
  totalTax: number;
  effectiveRate: number;
}

type Step = "income" | "deductions" | "regime" | "summary" | "filing";
type TaxRegime = "old" | "new";

// Tax calculation utilities
const calculateOldRegimeTax = (taxableIncome: number): number => {
  if (taxableIncome <= 250000) return 0;
  if (taxableIncome <= 500000) return (taxableIncome - 250000) * 0.05;
  if (taxableIncome <= 1000000) return 12500 + (taxableIncome - 500000) * 0.2;
  return 112500 + (taxableIncome - 1000000) * 0.3;
};

const calculateNewRegimeTax = (taxableIncome: number): number => {
  // NEW SLABS for FY 2025-26
  // 0-4L: Nil | 4-8L: 5% | 8-12L: 10% | 12-15L: 15% | Above 15L: 30% (simplified for the logic)
  if (taxableIncome <= 400000) return 0;
  if (taxableIncome <= 800000) return (taxableIncome - 400000) * 0.05;
  if (taxableIncome <= 1200000) return 20000 + (taxableIncome - 800000) * 0.1;
  if (taxableIncome <= 1500000) return 20000 + 40000 + (taxableIncome - 1200000) * 0.15;
  return 20000 + 40000 + 45000 + (taxableIncome - 1500000) * 0.3;
};

// Format currency
const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
};

// Input Component
const CurrencyInput = ({
  label,
  value,
  onChange,
  placeholder = "0",
  helpText,
  maxLimit,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  placeholder?: string;
  helpText?: string;
  maxLimit?: number;
}) => {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-gray-700">
        {label}
        {maxLimit && (
          <span className="ml-2 text-xs text-gray-400">
            (Max: {formatCurrency(maxLimit)})
          </span>
        )}
      </label>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">
          ₹
        </span>
        <input
          type="number"
          value={value || ""}
          onChange={(e) => {
            let val = parseFloat(e.target.value) || 0;
            if (maxLimit && val > maxLimit) val = maxLimit;
            onChange(val);
          }}
          placeholder={placeholder}
          className="w-full rounded-lg border border-gray-300 py-2.5 pl-8 pr-4 text-gray-900 placeholder-gray-400 transition-colors focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
        />
      </div>
      {helpText && <p className="text-xs text-gray-500">{helpText}</p>}
    </div>
  );
};

// Step Indicator
const StepIndicator = ({
  currentStep,
  steps,
}: {
  currentStep: Step;
  steps: { key: Step; label: string }[];
}) => {
  const currentIndex = steps.findIndex((s) => s.key === currentStep);

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between">
        {steps.map((step, index) => (
          <div key={step.key} className="flex items-center">
            <div
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold transition-all",
                index <= currentIndex
                  ? "bg-emerald-600 text-white shadow-lg shadow-emerald-200"
                  : "bg-gray-200 text-gray-500"
              )}
            >
              {index < currentIndex ? (
                <svg
                  className="h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              ) : (
                index + 1
              )}
            </div>
            {index < steps.length - 1 && (
              <div
                className={cn(
                  "mx-2 h-1 w-12 rounded-full transition-all sm:w-16 md:w-24",
                  index < currentIndex ? "bg-emerald-500" : "bg-gray-200"
                )}
              />
            )}
          </div>
        ))}
      </div>
      <div className="mt-3 flex justify-between">
        {steps.map((step) => (
          <span
            key={step.key}
            className={cn(
              "text-xs font-medium sm:text-sm",
              step.key === currentStep ? "text-emerald-700" : "text-gray-500"
            )}
          >
            {step.label}
          </span>
        ))}
      </div>
    </div>
  );
};

// Main Component
export function ITRCalculator() {
  const [currentStep, setCurrentStep] = useState<Step>("income");
  const [taxRegime, setTaxRegime] = useState<TaxRegime>("new");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const [income, setIncome] = useState<IncomeDetails>({
    salary: 0,
    housePropertyIncome: 0,
    businessIncome: 0,
    capitalGains: 0,
    otherIncome: 0,
    interestIncome: 0,
  });

  const [deductions, setDeductions] = useState<Deductions>({
    section80C: 0,
    section80D: 0,
    section80E: 0,
    section80G: 0,
    hra: 0,
    standardDeduction: 75000, // Updated standard deduction for FY 2024-25
    homeLoanInterest: 0,
    nps80CCD: 0,
  });

  const steps: { key: Step; label: string }[] = [
    { key: "income", label: "Income" },
    { key: "deductions", label: "Deductions" },
    { key: "regime", label: "Regime" },
    { key: "summary", label: "Summary" },
    { key: "filing", label: "File ITR" },
  ];

  // Calculate tax based on regime
  const taxResult = useMemo((): TaxResult => {
    const grossIncome = Object.values(income).reduce((a, b) => a + b, 0);
    const currentSD = 75000;

 let totalDeductions = 0;
    if (taxRegime === "old") {
      totalDeductions =
        Math.min(deductions.section80C, 150000) +
        Math.min(deductions.section80D, 75000) +
        deductions.section80E + deductions.section80G +
        deductions.hra + 50000 + // Old regime SD is 50k
        Math.min(deductions.homeLoanInterest, 200000) +
        Math.min(deductions.nps80CCD, 50000);
    } else {
      totalDeductions = currentSD;
    }

const taxableIncome = Math.max(0, grossIncome - totalDeductions);

    const taxBeforeCess =
      taxRegime === "old"
        ? calculateOldRegimeTax(taxableIncome)
        : calculateNewRegimeTax(taxableIncome);

// REBATE Section 87A Updated for FY 2025-26
    // New Regime: No tax if taxable income <= 12,00,000
    // Old Regime: No tax if taxable income <= 5,00,000    
    let finalTaxBeforeCess = taxBeforeCess;
    if (taxRegime === "new" && taxableIncome <= 1200000) {
      finalTaxBeforeCess = 0;
    } else if (taxRegime === "old" && taxableIncome <= 500000) {
      finalTaxBeforeCess = 0;
    }

 const cess = taxBeforeCess * 0.04;
    return {
      grossIncome,
      totalDeductions,
      taxableIncome,
      taxBeforeCess,
      cess,
      totalTax: taxBeforeCess + cess,
      effectiveRate: grossIncome > 0 ? ((taxBeforeCess + cess) / grossIncome) * 100 : 0,
    };
  }, [income, deductions, taxRegime]);

  const handleNext = () => {
    const stepOrder: Step[] = [
      "income",
      "deductions",
      "regime",
      "summary",
      "filing",
    ];
    const currentIndex = stepOrder.indexOf(currentStep);
    if (currentIndex < stepOrder.length - 1) {
      setCurrentStep(stepOrder[currentIndex + 1]);
    }
  };

  const handleBack = () => {
    const stepOrder: Step[] = [
      "income",
      "deductions",
      "regime",
      "summary",
      "filing",
    ];
    const currentIndex = stepOrder.indexOf(currentStep);
    if (currentIndex > 0) {
      setCurrentStep(stepOrder[currentIndex - 1]);
    }
  };

  const handleSubmitITR = async () => {
    setIsSubmitting(true);
    // Simulate filing process
    await new Promise((resolve) => setTimeout(resolve, 2500));
    setIsSubmitting(false);
    setIsSubmitted(true);
  };

  const handleReset = () => {
    setCurrentStep("income");
    setTaxRegime("new");
    setIsSubmitted(false);
    setIncome({
      salary: 0,
      housePropertyIncome: 0,
      businessIncome: 0,
      capitalGains: 0,
      otherIncome: 0,
      interestIncome: 0,
    });
    setDeductions({
      section80C: 0,
      section80D: 0,
      section80E: 0,
      section80G: 0,
      hra: 0,
      standardDeduction: 75000,
      homeLoanInterest: 0,
      nps80CCD: 0,
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-teal-50 py-8 px-4">
      <div className="mx-auto max-w-3xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 shadow-lg shadow-emerald-200 mb-4">
            <svg
              className="h-8 w-8 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"
              />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-gray-900">
            ITR Calculator & Filing
          </h1>
          <p className="mt-2 text-gray-600">
Calculate your income tax for FY 2025-26 (AY 2026-27)          </p>
        </div>

        {/* Main Card */}
        <div className="rounded-2xl bg-white p-6 shadow-xl shadow-gray-200/50 sm:p-8">
          <StepIndicator currentStep={currentStep} steps={steps} />

          {/* Income Step */}
          {currentStep === "income" && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 text-sm font-bold">
                  1
                </span>
                Enter Your Income Details
              </h2>
              <div className="grid gap-5 sm:grid-cols-2">
                <CurrencyInput
                  label="Gross Salary (Annual)"
                  value={income.salary}
                  onChange={(val) => setIncome({ ...income, salary: val })}
                  helpText="Total salary before any deductions"
                />
                <CurrencyInput
                  label="Income from House Property"
                  value={income.housePropertyIncome}
                  onChange={(val) =>
                    setIncome({ ...income, housePropertyIncome: val })
                  }
                  helpText="Rental income after standard deduction"
                />
                <CurrencyInput
                  label="Business/Professional Income"
                  value={income.businessIncome}
                  onChange={(val) =>
                    setIncome({ ...income, businessIncome: val })
                  }
                  helpText="Net profit from business"
                />
                <CurrencyInput
                  label="Capital Gains"
                  value={income.capitalGains}
                  onChange={(val) =>
                    setIncome({ ...income, capitalGains: val })
                  }
                  helpText="From sale of shares, property, etc."
                />
                <CurrencyInput
                  label="Interest Income"
                  value={income.interestIncome}
                  onChange={(val) =>
                    setIncome({ ...income, interestIncome: val })
                  }
                  helpText="From FD, savings account, etc."
                />
                <CurrencyInput
                  label="Other Income"
                  value={income.otherIncome}
                  onChange={(val) => setIncome({ ...income, otherIncome: val })}
                  helpText="Lottery, gifts, etc."
                />
              </div>

              {/* Quick Summary */}
              <div className="rounded-xl bg-emerald-50 p-4 border border-emerald-100">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-emerald-800">
                    Total Gross Income
                  </span>
                  <span className="text-xl font-bold text-emerald-700">
                    {formatCurrency(taxResult.grossIncome)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Deductions Step */}
          {currentStep === "deductions" && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 text-sm font-bold">
                  2
                </span>
                Claim Your Deductions
              </h2>
              <p className="text-sm text-gray-500 bg-amber-50 border border-amber-200 rounded-lg p-3">
                ⚠️ Note: Most deductions are only available under the Old Tax
                Regime. New regime only allows ₹75,000 standard deduction.
              </p>
              <div className="grid gap-5 sm:grid-cols-2">
                <CurrencyInput
                  label="Section 80C"
                  value={deductions.section80C}
                  onChange={(val) =>
                    setDeductions({ ...deductions, section80C: val })
                  }
                  helpText="PPF, ELSS, LIC Premium, EPF, etc."
                  maxLimit={150000}
                />
                <CurrencyInput
                  label="Section 80D (Medical Insurance)"
                  value={deductions.section80D}
                  onChange={(val) =>
                    setDeductions({ ...deductions, section80D: val })
                  }
                  helpText="Self, family & parents insurance"
                  maxLimit={75000}
                />
                <CurrencyInput
                  label="HRA Exemption"
                  value={deductions.hra}
                  onChange={(val) => setDeductions({ ...deductions, hra: val })}
                  helpText="House Rent Allowance exemption"
                />
                <CurrencyInput
                  label="Home Loan Interest (Sec 24)"
                  value={deductions.homeLoanInterest}
                  onChange={(val) =>
                    setDeductions({ ...deductions, homeLoanInterest: val })
                  }
                  helpText="Interest on home loan"
                  maxLimit={200000}
                />
                <CurrencyInput
                  label="Section 80E (Education Loan)"
                  value={deductions.section80E}
                  onChange={(val) =>
                    setDeductions({ ...deductions, section80E: val })
                  }
                  helpText="Interest on education loan"
                />
                <CurrencyInput
                  label="Section 80G (Donations)"
                  value={deductions.section80G}
                  onChange={(val) =>
                    setDeductions({ ...deductions, section80G: val })
                  }
                  helpText="Donations to approved funds"
                />
                <CurrencyInput
                  label="NPS (80CCD 1B)"
                  value={deductions.nps80CCD}
                  onChange={(val) =>
                    setDeductions({ ...deductions, nps80CCD: val })
                  }
                  helpText="Additional NPS contribution"
                  maxLimit={50000}
                />
              </div>

              {/* Deductions Summary */}
              <div className="rounded-xl bg-blue-50 p-4 border border-blue-100">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-blue-800">
                    Total Deductions (Old Regime)
                  </span>
                  <span className="text-xl font-bold text-blue-700">
                    {formatCurrency(
                      Math.min(deductions.section80C, 150000) +
                        Math.min(deductions.section80D, 75000) +
                        deductions.section80E +
                        deductions.section80G +
                        deductions.hra +
                        deductions.standardDeduction +
                        Math.min(deductions.homeLoanInterest, 200000) +
                        Math.min(deductions.nps80CCD, 50000)
                    )}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Regime Selection */}
          {currentStep === "regime" && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 text-sm font-bold">
                  3
                </span>
                Choose Your Tax Regime
              </h2>

              <div className="grid gap-4 sm:grid-cols-2">
                {/* Old Regime Card */}
                <button
                  onClick={() => setTaxRegime("old")}
                  className={cn(
                    "rounded-xl border-2 p-5 text-left transition-all",
                    taxRegime === "old"
                      ? "border-emerald-500 bg-emerald-50 shadow-lg shadow-emerald-100"
                      : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                  )}
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-semibold text-gray-900">
                      Old Regime
                    </span>
                    <div
                      className={cn(
                        "h-5 w-5 rounded-full border-2 flex items-center justify-center",
                        taxRegime === "old"
                          ? "border-emerald-500 bg-emerald-500"
                          : "border-gray-300"
                      )}
                    >
                      {taxRegime === "old" && (
                        <svg
                          className="h-3 w-3 text-white"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                      )}
                    </div>
                  </div>
                  <p className="text-sm text-gray-600 mb-3">
                    With all deductions & exemptions
                  </p>
                  <div className="space-y-1 text-xs text-gray-500">
                    <p>• Up to ₹5L: 5%</p>
                    <p>• ₹5L - ₹10L: 20%</p>
                    <p>• Above ₹10L: 30%</p>
                  </div>
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <p className="text-sm font-medium text-gray-700">
                      Estimated Tax:
                    </p>
                    <p className="text-2xl font-bold text-gray-900">
                      {formatCurrency(
                        (() => {
                          const oldDeductions =
                            Math.min(deductions.section80C, 150000) +
                            Math.min(deductions.section80D, 75000) +
                            deductions.section80E +
                            deductions.section80G +
                            deductions.hra +
                            deductions.standardDeduction +
                            Math.min(deductions.homeLoanInterest, 200000) +
                            Math.min(deductions.nps80CCD, 50000);
                          const taxable = Math.max(
                            0,
                            taxResult.grossIncome - oldDeductions
                          );
                          let tax = calculateOldRegimeTax(taxable);
                          if (taxable <= 500000) tax = 0;
                          return tax * 1.04;
                        })()
                      )}
                    </p>
                  </div>
                </button>

                {/* New Regime Card */}
                <button
                  onClick={() => setTaxRegime("new")}
                  className={cn(
                    "rounded-xl border-2 p-5 text-left transition-all",
                    taxRegime === "new"
                      ? "border-emerald-500 bg-emerald-50 shadow-lg shadow-emerald-100"
                      : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                  )}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-900">
                        New Regime
                      </span>
                      <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">
                        Default
                      </span>
                    </div>
                    <div
                      className={cn(
                        "h-5 w-5 rounded-full border-2 flex items-center justify-center",
                        taxRegime === "new"
                          ? "border-emerald-500 bg-emerald-500"
                          : "border-gray-300"
                      )}
                    >
                      {taxRegime === "new" && (
                        <svg
                          className="h-3 w-3 text-white"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                      )}
                    </div>
                  </div>
                  <p className="text-sm text-gray-600 mb-3">
                    Lower rates, minimal deductions
                  </p>
                  <div className="space-y-1 text-xs text-gray-500">
<p>• Up to ₹4L: Nil</p>
        <p>• ₹4L - ₹8L: 5%</p>
        <p>• ₹8L - ₹12L: 10%</p>
        <p>• ₹12L - ₹16L: 15%</p> {/* Add this */}
        <p>• Rebate up to ₹12L</p>
                  </div>
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <p className="text-sm font-medium text-gray-700">
                      Estimated Tax:
                    </p>
                    <p className="text-2xl font-bold text-gray-900">
                      {formatCurrency(
                        (() => {
                          const taxable = Math.max(
                            0,
                            taxResult.grossIncome - 75000
                          );
                          let tax = calculateNewRegimeTax(taxable);
                          if (taxable <= 700000) tax = 0;
                          return tax * 1.04;
                        })()
                      )}
                    </p>
                  </div>
                </button>
              </div>

              {/* Recommendation */}
              {taxResult.grossIncome > 0 && (
                <div className="rounded-xl bg-gradient-to-r from-purple-50 to-indigo-50 p-4 border border-purple-100">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0">
                      <svg
                        className="h-6 w-6 text-purple-600"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                        />
                      </svg>
                    </div>
                    <div>
                      <p className="font-medium text-purple-900">
                        💡 Our Recommendation
                      </p>
                      <p className="text-sm text-purple-700 mt-1">
                        Based on your income and deductions, the{" "}
                        <strong>
                          {(() => {
                            const oldDeductions =
                              Math.min(deductions.section80C, 150000) +
                              Math.min(deductions.section80D, 75000) +
                              deductions.section80E +
                              deductions.section80G +
                              deductions.hra +
                              deductions.standardDeduction +
                              Math.min(deductions.homeLoanInterest, 200000) +
                              Math.min(deductions.nps80CCD, 50000);
                            const oldTaxable = Math.max(
                              0,
                              taxResult.grossIncome - oldDeductions
                            );
                            let oldTax = calculateOldRegimeTax(oldTaxable);
                            if (oldTaxable <= 500000) oldTax = 0;

                            const newTaxable = Math.max(
                              0,
                              taxResult.grossIncome - 75000
                            );
                            let newTax = calculateNewRegimeTax(newTaxable);
                            if (newTaxable <= 700000) newTax = 0;

                            return oldTax <= newTax
                              ? "Old Regime"
                              : "New Regime";
                          })()}
                        </strong>{" "}
                        may save you more tax.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Summary Step */}
          {currentStep === "summary" && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 text-sm font-bold">
                  4
                </span>
                Tax Calculation Summary
              </h2>

              <div className="rounded-xl border border-gray-200 overflow-hidden">
                <div className="bg-gray-50 px-5 py-3 border-b border-gray-200">
                  <h3 className="font-medium text-gray-900">
                    {taxRegime === "old" ? "Old Tax Regime" : "New Tax Regime"}{" "}
                    - FY 2024-25
                  </h3>
                </div>
                <div className="p-5 space-y-4">
                  <div className="flex justify-between py-2">
                    <span className="text-gray-600">Gross Total Income</span>
                    <span className="font-medium text-gray-900">
                      {formatCurrency(taxResult.grossIncome)}
                    </span>
                  </div>
                  <div className="flex justify-between py-2 border-t border-gray-100">
                    <span className="text-gray-600">
                      Less: Total Deductions
                    </span>
                    <span className="font-medium text-green-600">
                      - {formatCurrency(taxResult.totalDeductions)}
                    </span>
                  </div>
                  <div className="flex justify-between py-2 border-t border-gray-200">
                    <span className="font-medium text-gray-900">
                      Taxable Income
                    </span>
                    <span className="font-bold text-gray-900">
                      {formatCurrency(taxResult.taxableIncome)}
                    </span>
                  </div>
                  <div className="flex justify-between py-2 border-t border-gray-100">
                    <span className="text-gray-600">Tax on Above</span>
                    <span className="font-medium text-gray-900">
                      {formatCurrency(taxResult.taxBeforeCess)}
                    </span>
                  </div>
                  <div className="flex justify-between py-2">
                    <span className="text-gray-600">
                      Add: Health & Education Cess (4%)
                    </span>
                    <span className="font-medium text-gray-900">
                      {formatCurrency(taxResult.cess)}
                    </span>
                  </div>
                  <div className="flex justify-between py-3 border-t-2 border-gray-200 bg-emerald-50 -mx-5 px-5 -mb-5 rounded-b-xl">
                    <span className="font-bold text-gray-900 text-lg">
                      Total Tax Liability
                    </span>
                    <span className="font-bold text-emerald-700 text-xl">
                      {formatCurrency(taxResult.totalTax)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Effective Rate */}
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-xl bg-blue-50 p-4 text-center">
                  <p className="text-sm text-blue-600 mb-1">
                    Effective Tax Rate
                  </p>
                  <p className="text-2xl font-bold text-blue-700">
                    {taxResult.effectiveRate.toFixed(2)}%
                  </p>
                </div>
                <div className="rounded-xl bg-purple-50 p-4 text-center">
                  <p className="text-sm text-purple-600 mb-1">Monthly Tax</p>
                  <p className="text-2xl font-bold text-purple-700">
                    {formatCurrency(taxResult.totalTax / 12)}
                  </p>
                </div>
              </div>

              {/* Tax Breakdown Visual */}
              {taxResult.grossIncome > 0 && (
                <div className="rounded-xl border border-gray-200 p-5">
                  <h4 className="font-medium text-gray-900 mb-4">
                    Income Breakdown
                  </h4>
                  <div className="h-4 rounded-full bg-gray-100 overflow-hidden flex">
                    <div
                      className="bg-emerald-500 transition-all"
                      style={{
                        width: `${
                          ((taxResult.grossIncome - taxResult.totalTax) /
                            taxResult.grossIncome) *
                          100
                        }%`,
                      }}
                    />
                    <div
                      className="bg-red-400 transition-all"
                      style={{
                        width: `${
                          (taxResult.totalTax / taxResult.grossIncome) * 100
                        }%`,
                      }}
                    />
                  </div>
                  <div className="flex justify-between mt-2 text-sm">
                    <span className="text-emerald-600">
                      Take Home:{" "}
                      {formatCurrency(
                        taxResult.grossIncome - taxResult.totalTax
                      )}
                    </span>
                    <span className="text-red-500">
                      Tax: {formatCurrency(taxResult.totalTax)}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Filing Step */}
          {currentStep === "filing" && !isSubmitted && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 text-sm font-bold">
                  5
                </span>
                File Your ITR
              </h2>

              {/* Form Selection */}
              <div className="rounded-xl border border-gray-200 p-5">
                <h3 className="font-medium text-gray-900 mb-3">
                  Recommended ITR Form
                </h3>
                <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-lg border border-blue-100">
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-100">
                    <svg
                      className="h-6 w-6 text-blue-600"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                  </div>
                  <div>
                    <p className="font-semibold text-blue-900">
                      {income.businessIncome > 0
                        ? "ITR-3"
                        : income.capitalGains > 0
                        ? "ITR-2"
                        : "ITR-1 (Sahaj)"}
                    </p>
                    <p className="text-sm text-blue-700">
                      {income.businessIncome > 0
                        ? "For individuals with business income"
                        : income.capitalGains > 0
                        ? "For individuals with capital gains"
                        : "For salaried individuals with income up to ₹50L"}
                    </p>
                  </div>
                </div>
              </div>

              {/* Checklist */}
              <div className="rounded-xl border border-gray-200 p-5">
                <h3 className="font-medium text-gray-900 mb-3">
                  Pre-filing Checklist
                </h3>
                <div className="space-y-3">
                  {[
                    "Form 16 from employer",
                    "Bank statements for interest income",
                    "Investment proofs for Section 80C",
                    "Rent receipts for HRA claims",
                    "PAN & Aadhaar linked",
                  ].map((item, index) => (
                    <label
                      key={index}
                      className="flex items-center gap-3 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        className="h-5 w-5 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                      />
                      <span className="text-gray-700">{item}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Summary Card */}
              <div className="rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 p-5 text-white">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-emerald-100">Total Tax Payable</p>
                    <p className="text-3xl font-bold mt-1">
                      {formatCurrency(taxResult.totalTax)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-emerald-100">Assessment Year</p>
                    <p className="text-xl font-semibold mt-1">2025-26</p>
                  </div>
                </div>
              </div>

              {/* Disclaimer */}
              <div className="rounded-lg bg-amber-50 border border-amber-200 p-4">
                <p className="text-sm text-amber-800">
                  <strong>⚠️ Disclaimer:</strong> This is a simulation for
                  demonstration purposes. For actual ITR filing, please visit
                  the official Income Tax e-Filing portal (incometax.gov.in) or
                  consult a tax professional.
                </p>
              </div>
            </div>
          )}

          {/* Success State */}
          {currentStep === "filing" && isSubmitted && (
            <div className="text-center py-8">
              <div className="inline-flex h-20 w-20 items-center justify-center rounded-full bg-emerald-100 mb-6">
                <svg
                  className="h-10 w-10 text-emerald-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                ITR Filing Simulated!
              </h2>
              <p className="text-gray-600 mb-6">
                Your ITR calculation has been completed. Reference No: ITR2025
                {Date.now().toString().slice(-8)}
              </p>
              <div className="rounded-xl bg-gray-50 p-5 mb-6 inline-block">
                <p className="text-sm text-gray-600">
                  Tax Liability Calculated
                </p>
                <p className="text-3xl font-bold text-emerald-600">
                  {formatCurrency(taxResult.totalTax)}
                </p>
              </div>
              <div className="space-y-3">
                <button
                  onClick={handleReset}
                  className="w-full sm:w-auto px-8 py-3 rounded-xl bg-emerald-600 text-white font-medium hover:bg-emerald-700 transition-colors"
                >
                  Calculate Another ITR
                </button>
              </div>
            </div>
          )}

          {/* Navigation Buttons */}
          {!(currentStep === "filing" && isSubmitted) && (
            <div className="mt-8 flex justify-between">
              <button
                onClick={handleBack}
                disabled={currentStep === "income"}
                className={cn(
                  "flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium transition-colors",
                  currentStep === "income"
                    ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                )}
              >
                <svg
                  className="h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 19l-7-7 7-7"
                  />
                </svg>
                Back
              </button>

              {currentStep !== "filing" ? (
                <button
                  onClick={handleNext}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-emerald-600 text-white font-medium hover:bg-emerald-700 transition-colors shadow-lg shadow-emerald-200"
                >
                  Continue
                  <svg
                    className="h-5 w-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </button>
              ) : (
                <button
                  onClick={handleSubmitITR}
                  disabled={isSubmitting}
                  className="flex items-center gap-2 px-8 py-2.5 rounded-xl bg-emerald-600 text-white font-medium hover:bg-emerald-700 transition-colors shadow-lg shadow-emerald-200 disabled:opacity-70 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <>
                      <svg
                        className="animate-spin h-5 w-5"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        />
                      </svg>
                      Processing...
                    </>
                  ) : (
                    <>
                      <svg
                        className="h-5 w-5"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      Submit ITR (Simulation)
                    </>
                  )}
                </button>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-sm text-gray-500">
          Easy Finance • ITR Calculator • FY 2024-25 (AY 2025-26)
        </p>
      </div>
    </div>
  );
}

export default ITRCalculator;
