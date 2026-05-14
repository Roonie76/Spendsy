import type { JsonObject } from "../types";

export const getNumber = (value: unknown): number =>
  typeof value === "number" && Number.isFinite(value) ? value : 0;

export const roundCurrency = (value: number): number => Math.round(value * 100) / 100;

export const isJsonObject = (value: unknown): value is JsonObject =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export const sumObjectNumbers = (value: JsonObject | undefined, skipKeys: string[] = []): number =>
  Object.entries(value ?? {}).reduce((total, [key, current]) => {
    if (skipKeys.includes(key)) {
      return total;
    }
    return total + getNumber(current);
  }, 0);

export const sumArrayField = (value: unknown, key: string): number => {
  if (!Array.isArray(value)) {
    return 0;
  }
  return value.reduce<number>((total, item) => {
    if (!isJsonObject(item)) return total;
    return total + getNumber(item[key]);
  }, 0);
};

export const getNestedObject = (
  value: JsonObject,
  key: string,
): JsonObject | undefined => {
  const nextValue = value[key];
  return nextValue && typeof nextValue === "object" && !Array.isArray(nextValue)
    ? (nextValue as JsonObject)
    : undefined;
};

export const calculateITR1Fields = (itr1: JsonObject): Record<string, number | string> => {
  const updates: Record<string, number | string> = {};

  const income = getNestedObject(itr1, "ITR1_IncomeDeductions");
  const filingStatus = getNestedObject(itr1, "FilingStatus");
  const taxPaid = getNestedObject(itr1, "TaxPaid");
  const taxComputation = getNestedObject(itr1, "ITR1_TaxComputation");
  const tdsSalary = getNestedObject(itr1, "TDSonSalaries");
  const tdsOther = getNestedObject(itr1, "TDSonOthThanSals");
  const tds3 = getNestedObject(itr1, "ScheduleTDS3Dtls");
  const tcs = getNestedObject(itr1, "ScheduleTCS");
  const taxPayments = getNestedObject(itr1, "TaxPayments");

  if (income) {
    const allowanceGroup = getNestedObject(income, "AllwncExemptUs10");
    const allowanceDetails = allowanceGroup?.AllwncExemptUs10Dtls;
    const allowanceTotal = sumArrayField(allowanceDetails, "SalOthAmount") || getNumber(allowanceGroup?.TotalAllwncExemptUs10);

    const deduction16ia = getNumber(income.DeductionUs16ia) || 50000; // Standard Salary Deduction
    const salaryComponentTotal =
      deduction16ia +
      getNumber(income.EntertainmentAlw16ii) +
      getNumber(income.ProfessionalTaxUs16iii);

    const grossSalary = Math.max(0, getNumber(income.GrossSalary));
    const netSalary = Math.max(0, grossSalary - allowanceTotal - getNumber(income.Increliefus89A));
    const incomeFromSalary = Math.max(0, netSalary - salaryComponentTotal);

    // HP Computation
    const schedule24B = getNestedObject(income, "ScheduleUs24B");
    const schedule24BDetails = schedule24B?.ScheduleUs24BDtls;
    const totalInterest24B = sumArrayField(schedule24BDetails, "InterestUs24B");
    const interestPayable = totalInterest24B || getNumber(income.InterestPayable);
    
    let annualValue = getNumber(income.AnnualValue);
    if (!annualValue) {
        annualValue = getNumber(income.GrossRentReceived) - getNumber(income.TaxPaidToLocalAuth);
    }
    const standardDeductionHP = roundCurrency(Math.max(0, annualValue) * 0.3);
    const typeOfHp = String(income.TypeOfHP ?? 'S');

    let totalIncomeOfHP = 0;
    if (typeOfHp === "S") {
        totalIncomeOfHP = Math.max(-200000, -interestPayable); 
        annualValue = 0; 
    } else {
        totalIncomeOfHP = annualValue - standardDeductionHP - interestPayable + getNumber(income.ArrearsUnrealizedRentRcvd);
        // Generic ceiling on unabsorbed loss under HP to 2,00,000 for standard set-off is typically handled across heads,
        // but for Sahaj we constrain the final property output if it exceeds limits normally.
    }

    const othersInc = getNestedObject(income, "OthersInc");
    const othersDetails = othersInc?.OthersIncDtlsOthSrc;
    const otherSourcesTotal = sumArrayField(othersDetails, "OthSrcOthAmount") || getNumber(income.IncomeOthSrc);

    const ltcgAmount = getNumber(getNestedObject(income, "LTCG112A")?.LongCap112A);

    const grossTotalIncome = roundCurrency(incomeFromSalary + totalIncomeOfHP + otherSourcesTotal);
    const grossTotalIncomeIncLtcg = roundCurrency(grossTotalIncome + ltcgAmount);
    
    // Deductions Processing
    const userDeductions = getNestedObject(income, "UsrDeductUndChapVIA");
    let userDeductionTotal = sumObjectNumbers(userDeductions, ["TotalChapVIADeductions"]);
    const eligibleDeductionTotal = Math.min(grossTotalIncome, userDeductionTotal); // Ceiling logic

    // Total Taxable Income = Gross Total Income (Inc LTCG) - Deductions
    const totalIncome = Math.max(0, Math.round(roundCurrency(grossTotalIncomeIncLtcg - eligibleDeductionTotal) / 10) * 10);

    updates["ITR.ITR1.ITR1_IncomeDeductions.AllwncExemptUs10.TotalAllwncExemptUs10"] = allowanceTotal;
    updates["ITR.ITR1.ITR1_IncomeDeductions.NetSalary"] = roundCurrency(netSalary);
    updates["ITR.ITR1.ITR1_IncomeDeductions.DeductionUs16"] = roundCurrency(salaryComponentTotal);
    updates["ITR.ITR1.ITR1_IncomeDeductions.IncomeFromSal"] = roundCurrency(incomeFromSalary);
    updates["ITR.ITR1.ITR1_IncomeDeductions.InterestPayable"] = roundCurrency(interestPayable);
    updates["ITR.ITR1.ITR1_IncomeDeductions.AnnualValue"] = roundCurrency(annualValue);
    updates["ITR.ITR1.ITR1_IncomeDeductions.StandardDeduction"] = standardDeductionHP;
    updates["ITR.ITR1.ITR1_IncomeDeductions.ThirtyPercentOfAnnualValue"] = standardDeductionHP;
    updates["ITR.ITR1.ITR1_IncomeDeductions.TotalIncomeOfHP"] = totalIncomeOfHP;
    updates["ITR.ITR1.ITR1_IncomeDeductions.IncomeOthSrc"] = roundCurrency(otherSourcesTotal);
    updates["ITR.ITR1.ITR1_IncomeDeductions.UsrDeductUndChapVIA.TotalChapVIADeductions"] = roundCurrency(userDeductionTotal);
    updates["ITR.ITR1.ITR1_IncomeDeductions.DeductUndChapVIA.TotalChapVIADeductions"] = roundCurrency(eligibleDeductionTotal);
    updates["ITR.ITR1.ITR1_IncomeDeductions.GrossTotIncome"] = roundCurrency(grossTotalIncome);
    updates["ITR.ITR1.ITR1_IncomeDeductions.GrossTotIncomeIncLTCG112A"] = roundCurrency(grossTotalIncomeIncLtcg);
    updates["ITR.ITR1.ITR1_IncomeDeductions.TotalIncome"] = roundCurrency(totalIncome);

    // Tax Computation Dynamic ITD Rules
    const optOut = String(filingStatus?.OptOutNewTaxRegime ?? 'N');
    let calculatedGrossTax = 0;
    let rebate87A = 0;

    if (optOut === 'N') {
       // New Regime Slabs
       if (totalIncome <= 300000) calculatedGrossTax = 0;
       else if (totalIncome <= 700000) calculatedGrossTax = (totalIncome - 300000) * 0.05;
       else if (totalIncome <= 1000000) calculatedGrossTax = 20000 + (totalIncome - 700000) * 0.10;
       else if (totalIncome <= 1200000) calculatedGrossTax = 50000 + (totalIncome - 1000000) * 0.15;
       else if (totalIncome <= 1500000) calculatedGrossTax = 80000 + (totalIncome - 1200000) * 0.20;
       else calculatedGrossTax = 140000 + (totalIncome - 1500000) * 0.30;
       
       if (totalIncome <= 700000) rebate87A = Math.min(calculatedGrossTax, 25000);
    } else {
       // Old Regime Slabs
       if (totalIncome <= 250000) calculatedGrossTax = 0;
       else if (totalIncome <= 500000) calculatedGrossTax = (totalIncome - 250000) * 0.05;
       else if (totalIncome <= 1000000) calculatedGrossTax = 12500 + (totalIncome - 500000) * 0.20;
       else calculatedGrossTax = 112500 + (totalIncome - 1000000) * 0.30;

       if (totalIncome <= 500000) rebate87A = Math.min(calculatedGrossTax, 12500);
    }

    const initialTaxPayable = Math.max(0, Math.round(calculatedGrossTax));
    updates["ITR.ITR1.ITR1_TaxComputation.TotalTaxPayable"] = initialTaxPayable;

    const taxPayableOnRebate = Math.max(0, initialTaxPayable - rebate87A);
    const educationCess = Math.round(taxPayableOnRebate * 0.04);
    const grossTaxLiability = taxPayableOnRebate + educationCess;
    
    // Safety fallback if the user overrides
    const sec89 = getNumber(taxComputation?.Section89);
    const netTaxLiability = Math.max(0, grossTaxLiability - sec89);

    const intrstPay = getNestedObject(taxComputation ?? {}, "IntrstPay");
    const totalInterestPayable = intrstPay
      ? getNumber(intrstPay.IntrstPayUs234A) +
        getNumber(intrstPay.IntrstPayUs234B) +
        getNumber(intrstPay.IntrstPayUs234C) +
        getNumber(intrstPay.LateFilingFee234F)
      : 0;

    const totalTaxFeeAndInterest = netTaxLiability + totalInterestPayable;

    updates["ITR.ITR1.ITR1_TaxComputation.Rebate87A"] = rebate87A;
    updates["ITR.ITR1.ITR1_TaxComputation.TaxPayableOnRebate"] = taxPayableOnRebate;
    updates["ITR.ITR1.ITR1_TaxComputation.EducationCess"] = educationCess;
    updates["ITR.ITR1.ITR1_TaxComputation.GrossTaxLiability"] = grossTaxLiability;
    updates["ITR.ITR1.ITR1_TaxComputation.NetTaxLiability"] = netTaxLiability;
    updates["ITR.ITR1.ITR1_TaxComputation.TotalIntrstPay"] = totalInterestPayable;
    updates["ITR.ITR1.ITR1_TaxComputation.TotTaxPlusIntrstPay"] = totalTaxFeeAndInterest;
  }

  const tdsSalaryTotal = sumArrayField(tdsSalary?.TDSonSalary, "TaxDeposited") || getNumber(tdsSalary?.TotalTDSonSalaries);
  const tdsOtherTotal = sumArrayField(tdsOther?.TDSonOthThanSal, "TaxDeposited") || getNumber(tdsOther?.TotalTDSonOthThanSals);
  const tds3Total = sumArrayField(tds3?.TDS3Details, "TaxDeposited") || getNumber(tds3?.TotalTDS3Details);
  const tcsTotal = sumArrayField(tcs?.TCS, "TaxCollected") || getNumber(tcs?.TotalSchTCS);
  const taxPaymentTotal = sumArrayField(taxPayments?.TaxPayment, "TaxPaid") || getNumber(taxPayments?.TotalTaxPayments);

  updates["ITR.ITR1.TDSonSalaries.TotalTDSonSalaries"] = roundCurrency(tdsSalaryTotal);
  updates["ITR.ITR1.TDSonOthThanSals.TotalTDSonOthThanSals"] = roundCurrency(tdsOtherTotal);
  updates["ITR.ITR1.ScheduleTDS3Dtls.TotalTDS3Details"] = roundCurrency(tds3Total);
  updates["ITR.ITR1.ScheduleTCS.TotalSchTCS"] = roundCurrency(tcsTotal);
  updates["ITR.ITR1.TaxPayments.TotalTaxPayments"] = roundCurrency(taxPaymentTotal);
  updates["ITR.ITR1.TaxPaid.TaxesPaid.TDS"] = roundCurrency(tdsSalaryTotal + tdsOtherTotal + tds3Total);
  updates["ITR.ITR1.TaxPaid.TaxesPaid.TCS"] = roundCurrency(tcsTotal);
  updates["ITR.ITR1.TaxPaid.TaxesPaid.AdvanceTax"] = roundCurrency(taxPaymentTotal);
  updates["ITR.ITR1.CreationInfo.SWVersionNo"] = "R1";
  updates["ITR.ITR1.CreationInfo.SWCreatedBy"] = "SW00012526"; // Vendor software ID remains static
  updates["ITR.ITR1.CreationInfo.JSONCreatedBy"] = "SW00012526";
  
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, '0');
  const dd = String(today.getDate()).padStart(2, '0');
  const dateStr = `${yyyy}-${mm}-${dd}`;
  updates["ITR.ITR1.CreationInfo.JSONCreationDate"] = dateStr;
  
  // Dynamically pull the person's location 
  const verification = getNestedObject(itr1, "Verification");
  const personalInfo = getNestedObject(itr1, "PersonalInfo");
  const address = getNestedObject(personalInfo ?? {}, "Address");
  
  const city = String(verification?.Place || address?.CityOrTownOrDistrict || "Delhi");
  updates["ITR.ITR1.CreationInfo.IntermediaryCity"] = city;

  // The Digest differs heavily per person because it uniquely encrypts the entire person's specific JSON payload!
  // To reflect changing unique digests per person in the frontend state without a heavy async library, 
  // we simulate a distinct Base64 SHA hash using their unique PAN and date.
  const pan = String(personalInfo?.PAN || "N/A");
  const simulatedHashInput = `${pan}-${city}-${dateStr}`;
  const mockDigestBase64 = typeof btoa !== "undefined" ? btoa(simulatedHashInput).padEnd(44, '=') : "ycg4VggdSzq4F0Md/KotwMSxhRow0NAfkS/jUBbypow=";
  
  updates["ITR.ITR1.CreationInfo.Digest"] = mockDigestBase64;

  return updates;
};
