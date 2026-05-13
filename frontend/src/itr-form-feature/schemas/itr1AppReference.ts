export const itr1AppExtractedEnums = {
  EmployerCategory: {
    source: "ITD desktop app cache",
    values: {
      CGOV: "Central Government",
      SGOV: "State Government",
      PSU: "Public Sector Undertaking",
      PE: "CG-Pensioners",
      PESG: "SG-Pensioners",
      PEPS: "PSU-Pensioners",
      PEO: "Other Pensioners",
      OTH: "Others",
      OTHNO: "Not Applicable (e.g. Family pension etc.)",
    },
  },
  AccountType: {
    source: "ITD desktop app cache",
    values: {
      SB: "Savings Account",
      CA: "Current Account",
      NRO: "NRO",
      NRE: "NRE",
    },
  },
  Capacity: {
    source: "ITD desktop app cache",
    values: {
      SLF: "Self",
      KRT: "Karta",
      REP: "Representative",
      PRT: "Partner",
      DIR: "Managing Director",
      PRO: "Principal Officer",
      ATS: "Authorised Signatory",
      CEO: "Chief Executive Officer",
      OTH: "Others",
      RPA: "Representative assessee",
      MNP: "Managing Partner",
      OFA: "Official liquidator/Resolution Professional under NCLT",
      DEP: "Designated partner",
      MND: "Member",
      RSP: "Resolution professional",
      TRS: "Trustee",
      EXC: "Executor",
      EX: "Official Assignee",
      LQ: "Liquidator",
      LGH: "Legal Heir",
      MNG: "Manager",
      GRD: "Guardian",
      OFL: "Other",
    },
  },
  TypeOfHP: {
    source: "ITD desktop app cache",
    values: {
      S: "Self Occupied",
      L: "Let Out",
      D: "Deemed Let Out",
    },
  },
  ReturnFileSec: {
    source: "ITD desktop app screenshots + cache labels",
    values: {
      "139(1)": "Return filed on or before due date",
      "139(4)": "Belated return filed after due date",
      "139(5)": "Revised return filed after original return",
      "119(2)(b)": "After condonation of delay",
      "139(8A)": "Updated return",
      "139(9)": "Return filed in response to notice u/s 139(9)",
      "142(1)": "Return filed against notice u/s 142(1)",
      "148": "Return filed against notice u/s 148",
      "153C": "Return filed against notice u/s 153C",
    },
  },
  YesNo: {
    source: "ITD desktop app cache",
    values: {
      Y: "Yes",
      N: "No",
    },
  },
  UseForRefund: {
    source: "ITD desktop app cache",
    values: {
      true: "Yes",
      false: "No",
    },
  },
} as const;

export const itr1AppFieldNames = {
  Section24BItem: [
    "LoanTknFrom",
    "BankOrInstnName",
    "LoanAccNoOfBankOrInstnRefNo",
    "DateofLoan",
    "TotalLoanAmt",
    "LoanOutstndngAmt",
    "InterestUs24B",
  ],
  OtherSourcesItem: [
    "OthSrcNatureDesc",
    "OthSrcOthNatOfInc",
    "OthSrcOthAmount",
    "NOT89A",
  ],
  ExemptIncomeItem: [
    "NatureDesc",
    "OthNatOfInc",
    "OthAmount",
  ],
  LTCG112A: [
    "TotSaleCnsdrn",
    "TotCstAcqisn",
    "LongCap112A",
  ],
} as const;

export const itr1AppLogicNotes = [
  "TypeOfHP uses S|L|D in the desktop app cache for Self Occupied, Let Out, and Deemed Let Out.",
  "OptOutNewTaxRegime and SeventhProvisio139 use Y|N in the desktop app cache.",
  "UseForRefund uses true|false strings in the current form sample and is rendered as a fixed-choice field in the app.",
  "The app warns that 80CCH is not allowed for employment category other than Central Government.",
  "The app warns that for Self Occupied property under new tax regime, interest payable on borrowed capital is not allowed.",
] as const;
