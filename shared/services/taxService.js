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

    const grossTotalOld =
      salaryIncome + incomeFromHP + taxableBusinessIncome + otherSourcesIncome;
    const grossTotalNew =
      salaryIncome + Math.max(0, incomeFromHP) + taxableBusinessIncome + otherSourcesIncome;

    // Age-aware deduction limits
    const age = parseInt(userProfile.age || 0);
    const ageCategory = age >= 80 ? "super_senior" : age >= 60 ? "senior" : "general";
    const parentsAreSenior = !!userProfile.parentsAreSenior;
    const limits = TAX_CONSTANTS.LIMITS;

    const limit80D_Self = ageCategory !== "general" ? limits.SECTION_80D_SELF_SENIOR : limits.SECTION_80D_SELF;
    const limit80D_Parents = parentsAreSenior ? limits.SECTION_80D_PARENTS_SENIOR : limits.SECTION_80D_PARENTS;
    const limitTTA = ageCategory !== "general" ? limits.SECTION_80TTB_SENIOR : limits.SECTION_80TTA;

    const used80C = Math.min(inv80C, limits.SECTION_80C);
    const used80D =
      Math.min(inv80D_Self, limit80D_Self) + Math.min(inv80D_Parents, limit80D_Parents);
    const usedNPS = Math.min(invNPS, limits.SEC_80CCD_1B);
    const used80TTA = Math.min(savingsInterest, limitTTA);
    const used80E = interest80E;

    // Additional deductions from ITR data
    const used80G = parseFloat(itr?.deductions_data?.section80G || 0);
    const used80GG = Math.min(parseFloat(itr?.deductions_data?.section80GG || 0), limits.SECTION_80GG_MONTHLY * 12);
    const used80EE = Math.min(parseFloat(itr?.deductions_data?.section80EE || 0), limits.SECTION_80EE);
    const used80EEB = Math.min(parseFloat(itr?.deductions_data?.section80EEB || 0), limits.SECTION_80EEB);

    const totalOldDeductions = stdDedOld + used80C + used80D + usedNPS + used80E + used80TTA + used80G + used80GG + used80EE + used80EEB + (parseFloat(itr?.deductions_data?.employer_nps) || 0);
    const taxableOld = Math.max(0, grossTotalOld - totalOldDeductions);
    const taxableNew = Math.max(0, grossTotalNew - stdDedNew - (parseFloat(itr?.deductions_data?.employer_nps) || 0));

    const slabTax = (income, slabs) => {
      let tax = 0;
      let prev = 0;
      for (const { limit, rate } of slabs) {
        const upper = limit ?? Infinity;
        if (income > prev) {
          tax += Math.min(income - prev, upper - prev) * rate;
        }
        prev = upper;
        if (income <= upper) break;
      }
      return tax;
    };

    const computeSurcharge = (baseTax, income, maxRate) => {
      const brackets = TAX_CONSTANTS.SURCHARGE;
      let surchargeRate = 0;
      for (const { threshold, rate } of brackets) {
        if (income > threshold && rate <= maxRate) surchargeRate = rate;
      }
      if (surchargeRate === 0) return 0;

      const rawSurcharge = baseTax * surchargeRate;

      // Marginal relief: surcharge should not exceed the additional income above threshold
      const applicableThreshold = [...brackets]
        .filter(b => income > b.threshold && b.rate <= maxRate)
        .pop()?.threshold;
      if (applicableThreshold) {
        const taxAtThreshold = slabTax(applicableThreshold, regimeSlabs);
        const surchargeAtThreshold = computeSurchargeSimple(taxAtThreshold, applicableThreshold, maxRate);
        const totalAtThreshold = taxAtThreshold + surchargeAtThreshold;
        const totalWithSurcharge = baseTax + rawSurcharge;
        const marginalExcess = income - applicableThreshold;
        if (totalWithSurcharge - totalAtThreshold > marginalExcess) {
          return Math.max(0, totalAtThreshold + marginalExcess - baseTax);
        }
      }
      return rawSurcharge;
    };

    // Simple surcharge without marginal relief (used inside marginal relief calc to avoid recursion)
    const computeSurchargeSimple = (baseTax, income, maxRate) => {
      let rate = 0;
      for (const b of TAX_CONSTANTS.SURCHARGE) {
        if (income > b.threshold && b.rate <= maxRate) rate = b.rate;
      }
      return baseTax * rate;
    };

    let regimeSlabs; // used by computeSurcharge closure

    const calcTax = (income, regimeType) => {
      const regime = regimeType === "new" ? TAX_CONSTANTS.NEW_REGIME : TAX_CONSTANTS.OLD_REGIME;
      const maxSurchargeRate = regime.MAX_SURCHARGE_RATE;

      // Pick slabs based on regime and age
      if (regimeType === "new") {
        regimeSlabs = regime.SLABS;
      } else {
        regimeSlabs = ageCategory === "super_senior" ? regime.SLABS_SUPER_SENIOR
          : ageCategory === "senior" ? regime.SLABS_SENIOR
          : regime.SLABS;
      }

      let baseTax = slabTax(income, regimeSlabs);

      // Rebate u/s 87A
      if (regimeType === "new") {
        if (income <= regime.REBATE_LIMIT) {
          baseTax = 0;
        } else if (income <= regime.REBATE_LIMIT + regime.REBATE_MAX) {
          // Marginal relief on rebate: tax cannot exceed income above rebate limit
          baseTax = Math.min(baseTax, income - regime.REBATE_LIMIT);
        }
      } else {
        if (income <= regime.REBATE_LIMIT) baseTax = 0;
      }

      // Surcharge
      const surcharge = computeSurcharge(baseTax, income, maxSurchargeRate);

      // Cess 4% on (tax + surcharge)
      const cess = (baseTax + surcharge) * regime.CESS;

      return baseTax + surcharge + cess;
    };

    // Capital gains tax (computed separately at special rates, not through slabs)
    const calcCapitalGainsTax = () => {
      const cg = TAX_CONSTANTS.CAPITAL_GAINS;
      const cgData = itr?.income_data || {};
      let cgTax = 0;

      const stcg = parseFloat(cgData.stcg_111a || 0);
      const ltcg = parseFloat(cgData.ltcg_112a || 0);
      const crypto = parseFloat(cgData.crypto_vda || 0);

      // New: Detailed assets from ITR data
      const otherLtcg = parseFloat(cgData.property_ltcg || 0) + 
                       parseFloat(cgData.gold_ltcg || 0) + 
                       parseFloat(cgData.debt_mf_ltcg || 0) +
                       parseFloat(cgData.unlisted_ltcg || 0);

      if (stcg > 0) cgTax += stcg * cg.STCG_111A;
      if (ltcg > cg.LTCG_112A_EXEMPT) cgTax += (ltcg - cg.LTCG_112A_EXEMPT) * cg.LTCG_112A;
      if (crypto > 0) cgTax += crypto * cg.CRYPTO_VDA;
      if (otherLtcg > 0) cgTax += otherLtcg * cg.LTCG_112; // 12.5% flat

      return cgTax * (1 + TAX_CONSTANTS.NEW_REGIME.CESS); // cess applies to CG tax too
    };

    const taxOld = calcTax(taxableOld, "old");
    const taxNew = calcTax(taxableNew, "new");
    const capitalGainsTax = calcCapitalGainsTax();

    const totalBankCredits = txList
      .filter((t) => t?.type === "income")
      .reduce((acc, t) => acc + (parseFloat(t?.amount) || 0), 0);

    const incomeMismatch =
      Math.abs(totalBankCredits - grossTotalOld) > 50000;
    const monthsElapsed =
      new Date().getMonth() >= 3
        ? new Date().getMonth() - 2
        : new Date().getMonth() + 10;
    const monthlyPace80C = inv80C / Math.max(1, monthsElapsed);

    const recommendedRegime = taxNew <= taxOld ? "new" : "old";

    return {
      taxableOld,
      taxableNew,
      taxOld,
      taxNew,
      capitalGainsTax,
      totalTaxOld: taxOld + capitalGainsTax,
      totalTaxNew: taxNew + capitalGainsTax,
      recommendedRegime,
      ageCategory,
      fiscalYear: `${fyStartYear}-${fyStartYear + 1}`,
      mode: "PLANNING",
      sources: {
        salary: salaryIncome,
        interest: savingsInterest,
        other: otherSourcesIncome,
        total: grossTotalOld,
      },
      heads: {
        salary: salaryIncome,
        houseProperty: incomeFromHP,
        business: taxableBusinessIncome,
        capitalGains: capitalGainsReceipts,
        other: otherSourcesIncome,
      },
      deductions: {
        c80: { used: used80C, limit: limits.SECTION_80C, pace: monthlyPace80C },
        d80: { used: used80D, limit: limit80D_Self + limit80D_Parents },
        nps: { used: usedNPS, limit: limits.SEC_80CCD_1B },
        hln: { used: interest24b, limit: limits.SECTION_24B_SOP, potential: missingInterestClaim },
        edu: { used: used80E },
        tta: { used: used80TTA, limit: limitTTA },
        hra: { potential: rentPaid, notComputed: rentPaid > 0 },
        g80: { used: used80G },
        gg80: { used: used80GG, limit: limits.SECTION_80GG_MONTHLY * 12 },
        ee80: { used: used80EE, limit: limits.SECTION_80EE },
        eeb80: { used: used80EEB, limit: limits.SECTION_80EEB },
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
        (Math.max(0, limits.SECTION_80C - used80C) + Math.max(0, limits.SEC_80CCD_1B - usedNPS)) * 0.3,
    };
  },
};
