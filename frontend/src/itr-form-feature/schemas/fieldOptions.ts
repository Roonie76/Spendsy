import type { SelectOption } from "../types";

const normalizePath = (path: string) => path.replace(/\.\d+(?=\.|$)/g, "");

const yesNoOptions: SelectOption[] = [
  { value: "Y", label: "Yes" },
  { value: "N", label: "No" },
];

const filingReasonOptions: SelectOption[] = [
  { value: "taxable_income", label: "Taxable income is more than basic exemption limit" },
  {
    value: "seventh_proviso",
    label: "Filing due to one or more conditions under Seventh Proviso to section 139(1)",
  },
  { value: "others", label: "Others" },
];

const refundOptions: SelectOption[] = [
  { value: "true", label: "Yes" },
  { value: "false", label: "No" },
];

const housePropertyTypeOptions: SelectOption[] = [
  { value: "S", label: "Self Occupied" },
  { value: "L", label: "Let Out" },
  { value: "D", label: "Deemed Let Out" },
];

const returnFileSectionOptions: SelectOption[] = [
  { value: 11, label: "11 - 139(1) - On or before due date" },
  { value: 12, label: "12 - 139(4) - After due date" },
  { value: 13, label: "13 - 139(5) - Revised Return" },
  { value: 14, label: "14 - 139(9) - Defective Return" },
  { value: 15, label: "15 - 142(1)" },
  { value: 16, label: "16 - 148" },
  { value: 17, label: "17 - 153C" },
  { value: 18, label: "18 - 119(2)(b)" },
  { value: 20, label: "20 - 139(8A) - Updated return" },
  { value: 21, label: "21 - 170A - Modified return" },
];

const employerCategoryOptions: SelectOption[] = [
  { value: "CGOV", label: "Central Government" },
  { value: "SGOV", label: "State Government" },
  { value: "PSU", label: "Public Sector Undertaking" },
  { value: "PE", label: "CG-Pensioners" },
  { value: "PESG", label: "SG-Pensioners" },
  { value: "PEPS", label: "PSU-Pensioners" },
  { value: "PEO", label: "Other Pensioners" },
  { value: "OTH", label: "Others" },
  { value: "OTHNO", label: "Not Applicable (e.g. Family pension etc.)" },
];

const stateCodeOptions: SelectOption[] = [
  { value: "01", label: "01-Andaman and Nicobar islands" },
  { value: "02", label: "02-Andhra Pradesh" },
  { value: "03", label: "03-Arunachal Pradesh" },
  { value: "04", label: "04-Assam" },
  { value: "05", label: "05-Bihar" },
  { value: "06", label: "06-Chandigarh" },
  { value: "07", label: "07-Dadra Nagar and Haveli" },
  { value: "08", label: "08-Daman and Diu" },
  { value: "09", label: "09-Delhi" },
  { value: "10", label: "10-Goa" },
  { value: "11", label: "11-Gujarat" },
  { value: "12", label: "12-Haryana" },
  { value: "13", label: "13-Himachal Pradesh" },
  { value: "14", label: "14-Jammu and Kashmir" },
  { value: "15", label: "15-Karnataka" },
  { value: "16", label: "16-Kerala" },
  { value: "17", label: "17-Lakshadweep" },
  { value: "18", label: "18-Madhya Pradesh" },
  { value: "19", label: "19-Maharashtra" },
  { value: "20", label: "20-Manipur" },
  { value: "21", label: "21-Meghalaya" },
  { value: "22", label: "22-Mizoram" },
  { value: "23", label: "23-Nagaland" },
  { value: "24", label: "24-Odisha" },
  { value: "25", label: "25-Puducherry" },
  { value: "26", label: "26-Punjab" },
  { value: "27", label: "27-Rajasthan" },
  { value: "28", label: "28-Sikkim" },
  { value: "29", label: "29-Tamil Nadu" },
  { value: "30", label: "30-Tripura" },
  { value: "31", label: "31-Uttar Pradesh" },
  { value: "32", label: "32-West Bengal" },
  { value: "33", label: "33-Chhattisgarh" },
  { value: "34", label: "34-Uttarakhand" },
  { value: "35", label: "35-Jharkhand" },
  { value: "36", label: "36-Telangana" },
  { value: "37", label: "37-Ladakh" },
];

const countryCodeOptions: SelectOption[] = [
  { value: "91", label: "91-India" },
];

const mobileCountryCodeOptions: SelectOption[] = [
  { value: 91, label: "91-India" },
];

const accountTypeOptions: SelectOption[] = [
  { value: "SB", label: "Savings Account" },
  { value: "CA", label: "Current Account" },
  { value: "NRO", label: "NRO" },
  { value: "NRE", label: "NRE" },
];

const capacityOptions: SelectOption[] = [
  { value: "S", label: "Self" },
  { value: "K", label: "Karta" },
  { value: "R", label: "Representative" },
  { value: "P", label: "Partner" },
  { value: "D", label: "Managing Director" },
  { value: "O", label: "Principal Officer" },
  { value: "A", label: "Authorised Signatory" },
  { value: "C", label: "Chief Executive Officer" },
  { value: "T", label: "Trustee" },
  { value: "E", label: "Executor" },
  { value: "L", label: "Liquidator" },
  { value: "G", label: "Guardian" },
  { value: "M", label: "Manager" },
  { value: "X", label: "Others" },
];

const pathOptions = new Map<string, SelectOption[]>([
  ["ITR.ITR1.PersonalInfo.Address.StateCode", stateCodeOptions],
  ["ITR.ITR1.PersonalInfo.Address.CountryCode", countryCodeOptions],
  ["ITR.ITR1.PersonalInfo.Address.CountryCodeMobile", mobileCountryCodeOptions],
  ["ITR.ITR1.PersonalInfo.EmployerCategory", employerCategoryOptions],
  ["ITR.ITR1.FilingStatus.FilingReasonCategory", filingReasonOptions],
  ["ITR.ITR1.FilingStatus.ReturnFileSec", returnFileSectionOptions],
  ["ITR.ITR1.FilingStatus.OptOutNewTaxRegime", yesNoOptions],
  ["ITR.ITR1.FilingStatus.SeventhProvisio139", yesNoOptions],
  ["ITR.ITR1.Verification.Capacity", capacityOptions],
  ["ITR.ITR1.ITR1_IncomeDeductions.TypeOfHP", housePropertyTypeOptions],
  ["ITR.ITR1.Refund.BankAccountDtls.AddtnlBankDetails.AccountType", accountTypeOptions],
  ["ITR.ITR1.Refund.BankAccountDtls.AddtnlBankDetails.UseForRefund", refundOptions],
]);

export const getFieldOptions = (path: string): SelectOption[] | undefined =>
  pathOptions.get(normalizePath(path));
