import { Fragment, useState } from "react";
import { useFieldArray, useFormContext } from "react-hook-form";

import type { FormFieldSchema, JsonObject } from "../types";

// ── Field guide map ───────────────────────────────────────────────────────────
// Key = last segment(s) of the field path. Each entry has:
//   what  - plain English description of what this field is
//   where - where to find the value
//   tip   - optional extra advice
const FIELD_GUIDES: Record<string, { what: string; where: string; tip?: string }> = {
  // ── Personal Info ──────────────────────────────────────────────────────────
  PAN: {
    what: "Your 10-character Permanent Account Number.",
    where: "Found on your PAN card or Form 16 (Part A, top section).",
    tip: "Must be uppercase. Example: ABCDE1234F",
  },
  DOB: {
    what: "Your date of birth as per PAN records.",
    where: "Found on your PAN card.",
  },
  AadhaarCardNo: {
    what: "Your 12-digit Aadhaar number.",
    where: "Found on your Aadhaar card or DigiLocker.",
    tip: "Linking Aadhaar with PAN is mandatory for filing.",
  },
  MobileNo: {
    what: "Mobile number linked to your PAN/Aadhaar.",
    where: "The number registered with NSDL/UIDAI.",
  },
  EmailAddress: {
    what: "Email address for ITD communications and OTP.",
    where: "The email registered with your employer or bank.",
  },
  SurNameOrOrgName: {
    what: "Your last name / surname.",
    where: "As printed on your PAN card.",
  },
  FirstName: {
    what: "Your first name.",
    where: "As printed on your PAN card.",
  },
  MiddleName: {
    what: "Your middle name (if any).",
    where: "As printed on your PAN card. Leave blank if none.",
  },
  FatherName: {
    what: "Your father's full name.",
    where: "As printed on your PAN card.",
  },

  // ── Address ────────────────────────────────────────────────────────────────
  ResidenceNo: {
    what: "House / flat / door number.",
    where: "Your current residential address.",
  },
  ResidenceName: {
    what: "Building / society / apartment name.",
    where: "Your current residential address.",
  },
  RoadOrStreet: {
    what: "Street name or road.",
    where: "Your current residential address.",
  },
  LocalityOrArea: {
    what: "Locality, area or colony name.",
    where: "Your current residential address.",
  },
  CityOrTownOrDistrict: {
    what: "City, town or district name.",
    where: "Your current residential address.",
  },
  PinCode: {
    what: "6-digit postal PIN code.",
    where: "Your current residential address.",
  },
  StateCode: {
    what: "2-digit state code as per ITD.",
    where: "E.g. 07 = Delhi, 27 = Maharashtra. Check ITD state code list.",
  },

  // ── Filing Status ──────────────────────────────────────────────────────────
  ReturnFileSec: {
    what: "Section under which you are filing the return.",
    where: "Most salaried employees file under Section 139(1) — use code 11 (original) or 12 (revised).",
  },
  ItrFilingDueDate: {
    what: "Due date for filing without penalty.",
    where: "Usually 31st July for salaried individuals. Pre-filled automatically.",
  },
  OptOutNewTaxRegime: {
    what: "Whether you want to opt out of the New Tax Regime and use the Old Regime.",
    where: "Choose 'Y' to use old regime (deductions apply). Choose 'N' for new regime (lower rates, no deductions).",
    tip: "If you have significant deductions (80C, HRA, home loan), old regime is usually better.",
  },
  SeventhProvisio139: {
    what: "Tick 'Y' if you are filing mandatorily under 7th proviso to Section 139(1).",
    where: "Required if you deposited >₹1Cr in bank, spent >₹2L on foreign travel, or paid >₹1L in electricity bills.",
  },
  EmployerCategory: {
    what: "Type of your employer.",
    where: "Found on Form 16 Part A. 'OTH' = private company, 'PSU' = public sector, 'CG/SG' = government.",
  },

  // ── Income from Salary ─────────────────────────────────────────────────────
  GrossSalary: {
    what: "Total salary before any exemptions or deductions.",
    where: "Form 16 Part B — 'Gross Salary' (sum of all salary components including perquisites).",
    tip: "Auto-filled from Form 16 upload.",
  },
  TotalAllwncExemptUs10: {
    what: "HRA exemption + other exempt allowances (LTA, uniform, etc.).",
    where: "Form 16 Part B — 'Allowances exempt u/s 10'. Also auto-calculated if HRA details provided.",
    tip: "Auto-filled from Form 16 upload.",
  },
  Increliefus89A: {
    what: "Relief under Section 89A for income from foreign retirement funds.",
    where: "Leave 0 if you don't have foreign retirement accounts (e.g. 401k, pension plans abroad).",
  },
  NetSalary: {
    what: "Gross salary minus exempt allowances.",
    where: "Auto-calculated: Gross Salary − AllwncExemptUs10. Do not edit manually.",
  },
  DeductionUs16: {
    what: "Standard deduction of ₹50,000 for salaried employees.",
    where: "Auto-applied. Enter 50000 (or 75000 for FY 2024-25 onwards under new regime).",
  },
  DeductionUs16ia: {
    what: "Entertainment allowance deduction (only for government employees).",
    where: "Form 16 — applicable only if you are a central/state govt employee.",
  },
  EntertainmentAlw16ii: {
    what: "Entertainment allowance received (before deduction).",
    where: "Form 16 — applicable only for government employees.",
  },
  ProfessionalTaxUs16iii: {
    what: "Professional tax deducted from your salary by your employer.",
    where: "Form 16 Part B or your payslips. Usually ₹200/month = ₹2,400/year.",
  },
  IncomeFromSal: {
    what: "Net taxable income from salary after all deductions under Section 16.",
    where: "Auto-calculated. Do not edit.",
  },

  // ── House Property ─────────────────────────────────────────────────────────
  AnnualValue: {
    what: "Annual rental value of your house property.",
    where: "For self-occupied property, this is NIL (enter 0). For let-out, enter actual rent received.",
  },
  StandardDeduction: {
    what: "30% standard deduction on annual value of rented property.",
    where: "Auto-calculated as 30% of Annual Value. Applicable only for let-out property.",
  },
  InterestPayable: {
    what: "Interest paid on home loan during the financial year.",
    where: "Your home loan statement from the bank — look for 'Interest paid in FY'. Auto-filled if loan is in Spendsy.",
    tip: "For self-occupied: deduction capped at ₹2,00,000. For let-out: full interest is deductible.",
  },
  ArrearsUnrealizedRentRcvd: {
    what: "Arrears of rent or unrealised rent received this year.",
    where: "Enter 0 unless you received pending rent from a previous year.",
  },
  TotalIncomeOfHP: {
    what: "Net income/loss from house property.",
    where: "Auto-calculated: Annual Value − Standard Deduction − Interest. Usually negative for home loan holders.",
  },
  ScheduleUs24B: {
    what: "Home loan interest claimed under Section 24(b).",
    where: "Same as Interest Payable above — your bank's loan interest certificate for the financial year.",
    tip: "Auto-filled from Spendsy wealth data or enter from your bank's loan statement.",
  },

  // ── Other Sources ──────────────────────────────────────────────────────────
  IncomeOthSrc: {
    what: "Income from sources other than salary and property — savings interest, FD interest, dividends, etc.",
    where: "Bank passbook/statement for savings account interest. FD interest certificate from bank. Form 26AS.",
    tip: "Auto-filled from bank statement upload.",
  },
  OthersInc: {
    what: "Other miscellaneous income not covered elsewhere.",
    where: "Any income from winnings, gifts above ₹50,000, or other sources not in standard categories.",
  },
  LTCG112A: {
    what: "Long-term capital gains on listed equity shares / equity mutual funds (held > 1 year), taxable at 10% above ₹1 lakh.",
    where: "Broker statement / Zerodha Tax P&L / Groww Capital Gains report. Auto-filled from broker upload.",
    tip: "Only include gains from equity. Gains up to ₹1,00,000 are exempt.",
  },
  ExemptIncAgriOthUs10Total: {
    what: "Agricultural income or other fully exempt income under Section 10.",
    where: "Enter only if you have agricultural income or specific exempt incomes. Most salaried employees enter 0.",
  },

  // ── Deductions Chapter VI-A ────────────────────────────────────────────────
  Section80C: {
    what: "Investments qualifying for 80C deduction — EPF, PPF, ELSS, LIC premium, home loan principal, tuition fees, etc.",
    where: "Form 16 Part B shows total 80C. Or sum up: EPF from payslip + PPF passbook + ELSS statement + LIC receipts.",
    tip: "Maximum deduction: ₹1,50,000. Auto-filled from Form 16 upload.",
  },
  Section80CCC: {
    what: "Contribution to pension fund of LIC or other insurers.",
    where: "Premium receipts from LIC Jeevan Nidhi or similar pension plans.",
    tip: "Combined 80C + 80CCC + 80CCD(1) limit is ₹1,50,000.",
  },
  Section80CCDEmployeeOrSE: {
    what: "Your own NPS contribution (employee's share).",
    where: "NPS statement or Form 16 — 'Employee contribution to NPS'.",
    tip: "Part of the ₹1,50,000 combined 80C limit.",
  },
  Section80CCD1B: {
    what: "Additional NPS contribution over and above the ₹1.5L limit.",
    where: "NPS statement — contributions made directly to Tier-1 NPS account.",
    tip: "Extra deduction up to ₹50,000. Auto-filled from Form 16 upload.",
  },
  Section80CCDEmployer: {
    what: "Employer's contribution to your NPS account.",
    where: "Form 16 Part B or salary slip — 'Employer NPS contribution'.",
    tip: "Deductible up to 10% of basic salary. Auto-filled from Form 16 upload.",
  },
  AnyOthSec80CCH: {
    what: "Contribution to Agnipath Scheme (Agniveer Corpus Fund).",
    where: "Applicable only for Agniveers. Enter 0 if not applicable.",
  },
  Section80D: {
    what: "Health insurance premium paid for self, spouse, children and parents.",
    where: "Insurance policy premium receipts. Form 16 may show this.",
    tip: "Self/family: up to ₹25,000 (₹50,000 if senior citizen). Parents: up to ₹25,000 (₹50,000 if senior citizen). Auto-filled from Form 16.",
  },
  Section80DD: {
    what: "Medical expenditure or insurance for a dependent with disability.",
    where: "Medical bills and disability certificate (Form 10-IA). ₹75,000 for 40-80% disability, ₹1,25,000 for severe.",
  },
  Section80DDB: {
    what: "Medical treatment expenses for specified diseases (cancer, neurological conditions, etc.).",
    where: "Medical bills and doctor's certificate (Form 10-I). Up to ₹40,000 (₹1,00,000 for senior citizens).",
  },
  Section80E: {
    what: "Interest paid on education loan for higher studies.",
    where: "Loan interest certificate from your bank. Auto-filled if education loan is in Spendsy.",
    tip: "No upper limit on deduction. Available for 8 years from start of repayment.",
  },
  Section80EE: {
    what: "Additional interest deduction on home loan for first-time buyers (loans sanctioned between Apr 2016–Mar 2017).",
    where: "Home loan sanction letter and interest certificate. Up to ₹50,000.",
  },
  Section80EEA: {
    what: "Additional interest deduction for affordable housing loans (stamped value ≤ ₹45L, sanctioned Apr 2019–Mar 2022).",
    where: "Home loan documents — sanction letter, stamp duty value of property. Up to ₹1,50,000.",
  },
  Section80EEB: {
    what: "Interest deduction on loan for electric vehicle purchase.",
    where: "Loan interest certificate from bank/NBFC. Up to ₹1,50,000.",
  },
  Section80G: {
    what: "Donations to approved charitable funds/institutions.",
    where: "Donation receipts with the trust's 80G registration number.",
    tip: "50% or 100% deductible depending on the organisation. Keep receipts.",
  },
  Section80GG: {
    what: "Rent paid if you don't receive HRA from employer.",
    where: "Rent receipts and rental agreement. Deduction = least of: actual rent − 10% income / 25% of income / ₹5,000/month.",
  },
  Section80GGA: {
    what: "Donations for scientific research or rural development.",
    where: "Donation receipts from approved research associations/institutions.",
  },
  Section80GGC: {
    what: "Donations to political parties.",
    where: "Receipt from the political party. No cash donations allowed.",
  },
  Section80TTA: {
    what: "Interest income from savings bank account (not FDs).",
    where: "Bank passbook or statement — look for 'Savings Account Interest'. Up to ₹10,000.",
    tip: "For FD interest use 80TTB (only for senior citizens).",
  },
  Section80TTB: {
    what: "Interest income from deposits for senior citizens (age ≥ 60).",
    where: "Bank/post office interest certificates. Up to ₹50,000.",
  },
  Section80U: {
    what: "Deduction for individual with disability.",
    where: "Disability certificate. ₹75,000 for 40-80% disability, ₹1,25,000 for severe.",
  },

  // ── TDS on Salaries ────────────────────────────────────────────────────────
  TAN: {
    what: "Tax Deduction Account Number of your employer.",
    where: "Form 16 Part A — top section. Format: 4 letters, 5 digits, 1 letter. E.g. AAAA12345A.",
    tip: "Auto-filled from Form 16 upload.",
  },
  NameOfDeductor: {
    what: "Your employer's registered name.",
    where: "Form 16 Part A — 'Name and address of employer'.",
    tip: "Auto-filled from Form 16 upload.",
  },
  TotalTDSSal: {
    what: "Total TDS deducted on salary during the year.",
    where: "Form 16 Part A — 'Total amount of tax deducted'. Also in Form 26AS.",
    tip: "Auto-filled from Form 16 upload.",
  },
  TDSDeducted: {
    what: "TDS amount actually deposited by employer with the government.",
    where: "Form 16 Part A or Form 26AS.",
    tip: "Auto-filled from Form 16 upload.",
  },

  // ── TDS on Other Income ────────────────────────────────────────────────────
  TotalTDSonOthThanSals: {
    what: "TDS deducted on non-salary income — FD interest, rent, professional fees, etc.",
    where: "Form 26AS Part A or AIS. Bank FD TDS certificates.",
  },
  TotalTDS3Details: {
    what: "TDS on income other than salary where no TAN was deducted (e.g. property sale).",
    where: "Form 26AS Part A1.",
  },
  TotalSchTCS: {
    what: "Tax Collected at Source — on purchases like foreign remittance, cars > ₹10L, overseas tour packages.",
    where: "Form 26AS Part C or TCS certificate from seller.",
  },

  // ── Tax Payments ───────────────────────────────────────────────────────────
  AdvanceTax: {
    what: "Advance tax paid by you in installments during the year.",
    where: "Challan 280 receipts from bank. Also visible in Form 26AS Part C.",
    tip: "Required if tax liability > ₹10,000 after TDS.",
  },
  SelfAssessmentTax: {
    what: "Tax paid by you while filing the return to cover any remaining liability.",
    where: "Challan 280 receipt paid just before/during filing.",
  },
  TCS: {
    what: "Tax collected at source (same as TotalSchTCS above).",
    where: "Form 26AS Part C.",
  },

  // ── Refund ─────────────────────────────────────────────────────────────────
  RefundDue: {
    what: "Amount of tax refund you are eligible to receive.",
    where: "Auto-calculated: Taxes Paid − Net Tax Liability.",
  },
  IFSCCode: {
    what: "IFSC code of your bank account for receiving refund.",
    where: "Bank passbook, cheque book, or bank's website. Format: 4 letters + 0 + 6 alphanumeric.",
    tip: "Auto-filled from bank statement upload.",
  },
  BankAccountNo: {
    what: "Bank account number for receiving refund.",
    where: "Bank passbook or account statement.",
    tip: "Auto-filled from bank statement upload.",
  },
  BankName: {
    what: "Name of your bank.",
    where: "As per your bank account.",
    tip: "Auto-filled from bank statement upload.",
  },
  AccountType: {
    what: "Type of bank account — Savings (SB), Current (CA), or Cash Credit (CC).",
    where: "Your bank passbook or net banking. Most individuals have Savings (SB).",
    tip: "Auto-filled from bank statement upload.",
  },
  UseForRefund: {
    what: "Mark this account to receive your ITR refund.",
    where: "Check this box for the account where you want the refund credited.",
  },

  // ── Verification ───────────────────────────────────────────────────────────
  AssesseeVerName: {
    what: "Full name of the person verifying/signing the return.",
    where: "Your name — same as AssesseeName above.",
  },
  AssesseeVerPAN: {
    what: "PAN of the person verifying the return.",
    where: "Same as your PAN above.",
  },
  Capacity: {
    what: "Capacity in which you are signing — 'S' for Self.",
    where: "Use 'S' if you are filing your own return.",
  },
  Place: {
    what: "City/place from where you are filing the return.",
    where: "Your current city of residence.",
  },

  // ── Creation Info ──────────────────────────────────────────────────────────
  IntermediaryCity: {
    what: "City of the tax professional or intermediary preparing the return.",
    where: "If self-filing, enter your own city.",
  },
  SWVersionNo: {
    what: "Version of the software used to generate the JSON.",
    where: "Auto-filled. Do not change.",
  },
  SWCreatedBy: {
    what: "Name of the software/platform generating the return.",
    where: "Auto-filled. Do not change.",
  },
  JSONCreatedBy: {
    what: "Creator identifier for the JSON payload.",
    where: "Auto-filled. Do not change.",
  },
  JSONCreationDate: {
    what: "Date and time the JSON was generated.",
    where: "Auto-filled at submission time. Do not change.",
  },
  Digest: {
    what: "SHA-256 cryptographic hash of the payload for integrity verification.",
    where: "Auto-computed at submission. Do not change.",
  },

  // ── Tax Computation ────────────────────────────────────────────────────────
  GrossTotIncome: {
    what: "Total income before Chapter VI-A deductions.",
    where: "Auto-calculated: Income from Salary + HP + Other Sources.",
  },
  TotalIncome: {
    what: "Net taxable income after all deductions.",
    where: "Auto-calculated: Gross Total Income − Chapter VI-A Deductions.",
  },
  TotalTaxPayable: {
    what: "Income tax computed on your net taxable income per the applicable slab rates.",
    where: "Auto-calculated.",
  },
  Rebate87A: {
    what: "Tax rebate under Section 87A if net income ≤ ₹5,00,000 (old) or ₹7,00,000 (new regime).",
    where: "Auto-calculated. Up to ₹12,500 under old regime, ₹25,000 under new regime.",
  },
  EducationCess: {
    what: "4% Health & Education Cess on income tax.",
    where: "Auto-calculated.",
  },
  Section89: {
    what: "Relief under Section 89 for salary received in arrears.",
    where: "Form 10E filed separately on the ITD portal. Enter the relief amount from there.",
  },
  IntrstPayUs234A: {
    what: "Interest penalty for late filing of return under Section 234A.",
    where: "Auto-calculated if filing after the due date.",
  },
  IntrstPayUs234B: {
    what: "Interest for shortfall in advance tax payment under Section 234B.",
    where: "Auto-calculated if advance tax paid was less than 90% of assessed tax.",
  },
  IntrstPayUs234C: {
    what: "Interest for deferred advance tax installments under Section 234C.",
    where: "Auto-calculated based on your advance tax payment schedule.",
  },
  LateFilingFee234F: {
    what: "Late filing fee under Section 234F — ₹1,000 if income ≤ ₹5L, else ₹5,000.",
    where: "Auto-calculated if filing after the due date.",
  },
};

// ── Tooltip component ─────────────────────────────────────────────────────────
interface GuideTooltipProps {
  fieldKey: string;
}

const GuideTooltip = ({ fieldKey }: GuideTooltipProps) => {
  const [open, setOpen] = useState(false);

  // Try exact key, then last segment of path
  const lastSegment = fieldKey.split(".").pop() ?? fieldKey;
  const guide = FIELD_GUIDES[lastSegment] ?? FIELD_GUIDES[fieldKey];

  if (!guide) return null;

  return (
    <span style={{ position: "relative", display: "inline-flex", alignItems: "center", marginLeft: "6px", flexShrink: 0 }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        style={{
          width: "16px",
          height: "16px",
          borderRadius: "50%",
          background: open ? "rgba(6,182,212,0.25)" : "rgba(255,255,255,0.08)",
          border: "1px solid " + (open ? "rgba(6,182,212,0.5)" : "rgba(255,255,255,0.15)"),
          color: open ? "#06b6d4" : "#64748b",
          fontSize: "10px",
          fontWeight: 700,
          lineHeight: 1,
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 0,
          transition: "all 0.15s",
          flexShrink: 0,
        }}
        title="Field guide"
        aria-label={`Guide for ${lastSegment}`}
      >
        ?
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            bottom: "calc(100% + 8px)",
            left: "50%",
            transform: "translateX(-50%)",
            width: "280px",
            background: "#0f172a",
            border: "1px solid rgba(6,182,212,0.25)",
            borderRadius: "10px",
            padding: "12px 14px",
            zIndex: 100,
            boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
            pointerEvents: "auto",
          }}
        >
          {/* Arrow */}
          <div style={{
            position: "absolute",
            bottom: "-5px",
            left: "50%",
            transform: "translateX(-50%) rotate(45deg)",
            width: "8px",
            height: "8px",
            background: "#0f172a",
            borderRight: "1px solid rgba(6,182,212,0.25)",
            borderBottom: "1px solid rgba(6,182,212,0.25)",
          }} />

          <p style={{ margin: "0 0 6px", fontSize: "11px", fontWeight: 700, color: "#06b6d4", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            What is this?
          </p>
          <p style={{ margin: "0 0 8px", fontSize: "12px", color: "#e2e8f0", lineHeight: 1.5 }}>
            {guide.what}
          </p>

          <p style={{ margin: "0 0 4px", fontSize: "11px", fontWeight: 700, color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Where to find it
          </p>
          <p style={{ margin: 0, fontSize: "12px", color: "#94a3b8", lineHeight: 1.5 }}>
            {guide.where}
          </p>

          {guide.tip && (
            <div style={{
              marginTop: "8px",
              padding: "6px 10px",
              borderRadius: "6px",
              background: "rgba(6,182,212,0.08)",
              border: "1px solid rgba(6,182,212,0.15)",
            }}>
              <p style={{ margin: 0, fontSize: "11px", color: "#67e8f9", lineHeight: 1.5 }}>
                💡 {guide.tip}
              </p>
            </div>
          )}
        </div>
      )}
    </span>
  );
};

// ── Field error ───────────────────────────────────────────────────────────────
interface DynamicFieldProps {
  field: FormFieldSchema;
  disabled?: boolean;
  depth?: number;
}

const FieldError = ({ name }: { name: string }) => {
  const { formState: { errors } } = useFormContext();

  const message = name
    .split(".")
    .reduce<unknown>((current, segment) => {
      if (current && typeof current === "object" && segment in (current as Record<string, unknown>)) {
        return (current as Record<string, unknown>)[segment];
      }
      return undefined;
    }, errors) as { message?: string } | undefined;

  if (!message?.message) return null;

  return (
    <p style={{ color: "var(--itr-red)", fontSize: "11px", marginTop: "2px", fontWeight: 600 }}>
      {message.message}
    </p>
  );
};

// ── Field label with optional tooltip ────────────────────────────────────────
const FieldLabel = ({
  label,
  required,
  description,
  fieldPath,
}: {
  label: string;
  required: boolean;
  description?: string;
  fieldPath: string;
}) => (
  <div style={{ flex: 1, paddingRight: "16px", minWidth: 0 }}>
    <div style={{ display: "flex", alignItems: "center", gap: "2px", flexWrap: "wrap" }}>
      <label className="field-label" style={{ marginRight: "2px" }}>
        {label}
        {required ? <span style={{ color: "var(--itr-red)", marginLeft: "3px" }}>*</span> : null}
      </label>
      <GuideTooltip fieldKey={fieldPath} />
    </div>
    {description ? (
      <p style={{ color: "var(--itr-text-dim)", fontSize: "11px", marginTop: "2px", margin: "2px 0 0" }}>
        {description}
      </p>
    ) : null}
  </div>
);

// ── Primitive field ───────────────────────────────────────────────────────────
const PrimitiveField = ({ field, disabled }: DynamicFieldProps) => {
  const { register } = useFormContext();
  const effectiveDisabled = disabled || field.readOnly;
  const isNumber = field.kind === "number";

  if (field.kind === "boolean") {
    return (
      <div className="field-card">
        <FieldLabel label={field.label} required={field.required} description={field.description} fieldPath={field.path} />
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <input
            type="checkbox"
            className="field-input"
            style={{ width: "22px", height: "22px", cursor: "pointer", display: "block" }}
            disabled={effectiveDisabled}
            {...register(field.path)}
          />
        </div>
        <FieldError name={field.path} />
      </div>
    );
  }

  if (field.kind === "boolean-string" || field.kind === "enum-string") {
    const options = field.validation?.options ?? [];
    return (
      <div className="field-card">
        <FieldLabel label={field.label} required={field.required} description={field.description} fieldPath={field.path} />
        <select className="field-input" disabled={effectiveDisabled} {...register(field.path)} style={{ textAlign: "left" }}>
          {options.map((option) => (
            <option key={String(option.value)} value={String(option.value)}>
              {option.label}
            </option>
          ))}
        </select>
        <FieldError name={field.path} />
      </div>
    );
  }

  if (field.kind === "select") {
    const options = field.validation?.options ?? [];
    const expectsNumber = typeof field.defaultValue === "number";
    return (
      <div className="field-card">
        <FieldLabel label={field.label} required={field.required} description={field.description} fieldPath={field.path} />
        <select
          className="field-input"
          disabled={effectiveDisabled}
          style={{ textAlign: "left" }}
          {...register(field.path, {
            setValueAs: (input) => (expectsNumber ? Number(input) : input),
          })}
        >
          {options.map((option) => (
            <option key={String(option.value)} value={String(option.value)}>
              {option.label}
            </option>
          ))}
        </select>
        <FieldError name={field.path} />
      </div>
    );
  }

  return (
    <div className="field-card">
      <FieldLabel label={field.label} required={field.required} description={field.description} fieldPath={field.path} />
      <div className="field-input-wrapper">
        {isNumber && <span className="currency-symbol">₹</span>}
        <input
          type={isNumber ? "number" : field.kind === "date" ? "date" : "text"}
          step={isNumber ? "any" : undefined}
          className="field-input"
          disabled={effectiveDisabled}
          placeholder={field.placeholder ?? (isNumber ? "0" : "")}
          {...register(field.path, { valueAsNumber: isNumber })}
        />
      </div>
      <FieldError name={field.path} />
    </div>
  );
};

// ── Array field ───────────────────────────────────────────────────────────────
const ArrayField = ({ field, disabled, depth = 0 }: DynamicFieldProps) => {
  const { control, getValues } = useFormContext<JsonObject>();
  const { fields, append, remove } = useFieldArray({ control, name: field.path as never });

  const itemDefaultValue = (() => {
    if (!field.itemSchema) return "";
    return typeof field.itemSchema.defaultValue === "object"
      ? JSON.parse(JSON.stringify(field.itemSchema.defaultValue))
      : field.itemSchema.defaultValue;
  })();

  return (
    <section className="nested-section">
      <div className="section-title-bar">
        <h3 className="section-label" style={{ fontSize: "1rem" }}>{field.label}</h3>
        <button
          type="button"
          disabled={disabled}
          onClick={() => append(itemDefaultValue)}
          className="btn btn-secondary"
          style={{ padding: "4px 12px", fontSize: "0.75rem", display: "inline-flex", alignItems: "center", gap: "4px" }}
        >
          <span style={{ fontSize: "1.2rem", fontWeight: 400 }}>+</span> Add Another
        </button>
      </div>

      <div className="section-content" style={{ display: "flex", flexDirection: "column", gap: "1px" }}>
        {fields.map((arrayField, index) => {
          const itemPath = `${field.path}.${index}`;
          const liveValue = getValues(itemPath as never);
          return (
            <div key={arrayField.id} style={{ padding: "16px 0", borderBottom: index < fields.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
                <span className="field-label" style={{ color: "var(--itr-cyan)", fontWeight: 700, fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  Entry #{index + 1}
                </span>
                <button
                  type="button"
                  disabled={disabled || fields.length === 1}
                  onClick={() => remove(index)}
                  className="btn btn-danger"
                  style={{ padding: "2px 8px", fontSize: "10px" }}
                >
                  Remove
                </button>
              </div>
              {field.itemSchema?.kind === "object" ? (
                <div style={{ display: "flex", flexDirection: "column" }}>
                  {field.itemSchema.children?.map((child) => (
                    <DynamicField
                      key={`${itemPath}.${child.key}`}
                      depth={depth + 1}
                      disabled={disabled}
                      field={{ ...child, path: `${itemPath}.${child.key}` }}
                    />
                  ))}
                </div>
              ) : (
                <PrimitiveField
                  disabled={disabled}
                  field={{ ...(field.itemSchema ?? field), path: itemPath, defaultValue: liveValue }}
                />
              )}
            </div>
          );
        })}
      </div>
      <FieldError name={field.path} />
    </section>
  );
};

// ── Object field ──────────────────────────────────────────────────────────────
const ObjectField = ({ field, disabled, depth = 0 }: DynamicFieldProps) => (
  <section className={depth === 0 ? "" : "nested-section"} style={{ marginBottom: "20px" }}>
    {(depth > 0 || field.kind === "object") && (
      <div className="section-title-bar">
        <h3 className="section-label">{field.label}</h3>
      </div>
    )}
    <div className={depth === 0 ? "" : "section-content"} style={{ display: "flex", flexDirection: "column" }}>
      {field.children?.map((child) => (
        <DynamicField key={child.path} depth={depth + 1} disabled={disabled} field={child} />
      ))}
    </div>
  </section>
);

// ── Main export ───────────────────────────────────────────────────────────────
export const DynamicField = ({ field, disabled, depth = 0 }: DynamicFieldProps) => {
  if (field.kind === "object") return <ObjectField depth={depth} disabled={disabled} field={field} />;
  if (field.kind === "array") return <ArrayField depth={depth} disabled={disabled} field={field} />;
  return (
    <Fragment>
      <PrimitiveField disabled={disabled} field={field} />
    </Fragment>
  );
};
