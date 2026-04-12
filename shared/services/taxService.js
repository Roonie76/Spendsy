import { TAX_CONSTANTS } from "../config/constants";
import { normalizeDate } from "../utils/helpers";

export const TaxService = {
  calculate: (
    transactions = [],
    profile = {},
    wealthItems = [],
    settings = {},
    itrData = null,
  ) => {
    // --- 1. DEFENSIVE INITIALIZATION ---
    // Ensures code doesn't crash if transactions or wealthItems are undefined/null
    const txList = Array.isArray(transactions) ? transactions : [];
    const wealthList = Array.isArray(wealthItems) ? wealthItems : [];
    const userProfile = profile || {};
    const itr = itrData || {};

    let fyStartYear;
    if (txList.length > 0) {
      const sorted = [...txList].sort(
        (a, b) => normalizeDate(b.date) - normalizeDate(a.date),
      );
      const latestDate = normalizeDate(sorted[0]?.date || new Date());
      fyStartYear =
        latestDate.getMonth() >= 3
          ? latestDate.getFullYear()
          : latestDate.getFullYear() - 1;
    } else {
      const now = new Date();
      fyStartYear =
        now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
    }

    const start = new Date(fyStartYear, 3, 1);
    const end = new Date(fyStartYear + 1, 2, 31);

    let salaryIncome = 0;
    let housePropertyIncome = 0;
    let businessIncome = 0;
    let capitalGainsReceipts = 0;
    let otherSourcesIncome = 0;
    let savingsInterest = 0;
    let detected80C = 0;
    let detected80D = 0;

    // --- 1.5. LOAD ITR INCOME DATA IF PROVIDED ---
    if (itr?.income_data) {
      const income = itr.income_data || {};
      salaryIncome += parseFloat(income.salary) || 0;
      housePropertyIncome += parseFloat(income.houseProperty) || 0;
      businessIncome += parseFloat(income.businessIncome) || 0;
      capitalGainsReceipts += parseFloat(income.capitalGains) || 0;
      otherSourcesIncome += parseFloat(income.otherIncome) || 0;
      savingsInterest += parseFloat(income.interestIncome) || 0;
    }

    // --- 2. SAFE TRANSACTION PROCESSING ---
    txList.forEach((t) => {
      if (!t) return;
      const d = normalizeDate(t.date);
      if (d >= start && d <= end) {
        const val = parseFloat(t.amount) || 0;

        // Safely convert to string before toLowerCase
        const desc = String(t.description || "").toLowerCase();
        const category = String(t.category || "").toLowerCase();

        if (t.type === "income") {
          if (
            desc.includes("salary") ||
            desc.includes("payroll") ||
            category === "salary"
          ) {
            salaryIncome += val;
          } else if (desc.includes("interest")) {
            otherSourcesIncome += val;
            savingsInterest += val;
          } else if (desc.includes("dividend")) {
            otherSourcesIncome += val;
          } else if (desc.includes("rent") && val > 5000) {
            housePropertyIncome += val;
          } else if (
            category === "investment" ||
            desc.includes("redeem") ||
            desc.includes("sold")
          ) {
            capitalGainsReceipts += val;
          } else if (userProfile.isBusiness) {
            businessIncome += val;
          } else {
            otherSourcesIncome += val;
          }
        } else {
          if (
            category === "investment" ||
            desc.includes("ppf") ||
            desc.includes("lic") ||
            desc.includes("elss")
          ) {
            detected80C += val;
          }

          if (
            (category === "utilities" ||
              category === "insurance" ||
              category === "health") &&
            (desc.includes("health") ||
              desc.includes("mediclaim") ||
              desc.includes("insurance"))
          ) {
            detected80D += val;
          }
        }
      }
    });

    // --- 3. SAFE PROFILE & WEALTH INTEGRATION ---
    const manualEPF = parseFloat(userProfile.annualEPF || 0);
    const inv80C = manualEPF + detected80C + (parseFloat(itr?.deductions_data?.section80C) || 0);
    const manualHealth = parseFloat(userProfile.healthInsuranceSelf || 0);
    const inv80D_Self = Math.max(manualHealth, detected80D) + (parseFloat(itr?.deductions_data?.section80D) || 0);

    const inv80D_Parents = parseFloat(userProfile.healthInsuranceParents || 0);
    const invNPS = parseFloat(userProfile.npsContribution || 0) + (parseFloat(itr?.deductions_data?.nps80CCD) || 0);
    const interest24b = parseFloat(userProfile.homeLoanInterest || 0) + (parseFloat(itr?.deductions_data?.homeLoanInterest) || 0);
    const interest80E = parseFloat(userProfile.educationLoanInterest || 0) + (parseFloat(itr?.deductions_data?.section80E) || 0);
    const rentPaid = parseFloat(userProfile.annualRent || 0) + (parseFloat(itr?.deductions_data?.hra) || 0);

    // FIXED: Using optional chaining and fallback for wealthItems names
    const hasHomeLoan = wealthList.some(
      (i) =>
        i?.type === "liability" &&
        String(i?.name || "")
          .toLowerCase()
          .includes("home"),
    );
    const hasHouseAsset = wealthList.some(
      (i) =>
        i?.type === "asset" &&
        String(i?.name || "")
          .toLowerCase()
          .includes("house"),
    );
    const hasInsurance = wealthList.some(
      (i) =>
        i?.type === "asset" &&
        String(i?.name || "")
          .toLowerCase()
          .includes("insurance"),
    );

    const missingInterestClaim = hasHomeLoan && interest24b === 0;
    const missingRentIncome = hasHouseAsset && housePropertyIncome === 0;
    const missing80D = hasInsurance && inv80D_Self === 0;

    let incomeFromHP = housePropertyIncome * 0.7 - interest24b;
    if (incomeFromHP < -200000) incomeFromHP = -200000;

    let taxableBusinessIncome = businessIncome;
    if (userProfile.isBusiness && businessIncome <= 30000000) {
      taxableBusinessIncome = businessIncome * 0.5;
    }
    const stdDedOld = salaryIncome > 0 ? 50000 : 0;
    const stdDedNew = salaryIncome > 0 ? 75000 : 0;

    const grossTotalIncome =
      salaryIncome + incomeFromHP + taxableBusinessIncome + otherSourcesIncome;

    const used80C = Math.min(inv80C, 150000);
    const used80D =
      Math.min(inv80D_Self, 25000) + Math.min(inv80D_Parents, 50000);
    const usedNPS = Math.min(invNPS, 50000);
    const used80TTA = Math.min(savingsInterest, 10000);
    const used80E = interest80E;

    const taxableOld = Math.max(
      0,
      grossTotalIncome -
        (stdDedOld + used80C + used80D + usedNPS + used80E + used80TTA),
    );
    const taxableNew = Math.max(0, grossTotalIncome - stdDedNew);

    const calcTax = (income, regimeType) => {
      let tax = 0;
      if (regimeType === "new") {
        if (income > 400000) tax += Math.min(income - 400000, 400000) * 0.05;
        if (income > 800000) tax += Math.min(income - 800000, 400000) * 0.1;
        if (income > 1200000) tax += Math.min(income - 1200000, 400000) * 0.15;
        if (income > 1600000) tax += Math.min(income - 1600000, 400000) * 0.2;
        if (income > 2000000) tax += Math.min(income - 2000000, 400000) * 0.25;
        if (income > 2400000) tax += (income - 2400000) * 0.3;

        if (income <= 1200000) tax = 0;
        else if (income > 1200000 && income <= 1275000)
          tax = Math.min(tax, income - 1200000);
      } else {
        if (income > 250000) tax += Math.min(income - 250000, 250000) * 0.05;
        if (income > 500000) tax += Math.min(income - 500000, 500000) * 0.2;
        if (income > 1000000) tax += (income - 1000000) * 0.3;
        if (income <= 500000) tax = 0;
      }
      return tax * 1.04;
    };

    const taxOld = calcTax(taxableOld, "old");
    const taxNew = calcTax(taxableNew, "new");

    const totalBankCredits = txList
      .filter((t) => t?.type === "income")
      .reduce((acc, t) => acc + (parseFloat(t?.amount) || 0), 0);

    const incomeMismatch =
      Math.abs(totalBankCredits - grossTotalIncome) > 50000;
    const monthsElapsed =
      new Date().getMonth() >= 3
        ? new Date().getMonth() - 2
        : new Date().getMonth() + 10;
    const monthlyPace80C = inv80C / Math.max(1, monthsElapsed);

    return {
      taxableOld,
      taxableNew,
      taxOld,
      taxNew,
      fiscalYear: `${fyStartYear}-${fyStartYear + 1}`,
      mode: "PLANNING",
      sources: {
        salary: salaryIncome,
        interest: savingsInterest,
        other: otherSourcesIncome,
        total: grossTotalIncome,
      },
      heads: {
        salary: salaryIncome,
        houseProperty: incomeFromHP,
        business: taxableBusinessIncome,
        capitalGains: capitalGainsReceipts,
        other: otherSourcesIncome,
      },
      deductions: {
        c80: { used: used80C, limit: 150000, pace: monthlyPace80C },
        d80: { used: used80D, limit: 75000 },
        nps: { used: usedNPS, limit: 50000 },
        hln: { used: interest24b, potential: missingInterestClaim },
        edu: { used: used80E },
        tta: { used: used80TTA },
        hra: { potential: rentPaid, notComputed: rentPaid > 0 },
      },
      compliance: {
        incomeMismatch,
        totalBankCredits,
        missingRentIncome,
        missing80D,
        missingInterestClaim,
        capitalGainsUnverified: capitalGainsReceipts > 0,
      },
      missedSavings:
        (Math.max(0, 150000 - used80C) + Math.max(0, 50000 - usedNPS)) * 0.3,
    };
  },
};
