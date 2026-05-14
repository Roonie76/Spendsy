import { useMemo } from "react";

import { getFieldOptions } from "../schemas/fieldOptions";
import type { FormFieldSchema, JsonObject, JsonValue, ValidationHint } from "../types";

const DATE_REGEX = /^\d{4}-\d{2}-\d{2}$/;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PAN_REGEX = /^[A-Z]{5}[0-9]{4}[A-Z]$/;
const AADHAAR_REGEX = /^\d{12}$/;
const IFSC_REGEX = /^[A-Z]{4}0[A-Z0-9]{6}$/;
const READ_ONLY_PATHS = new Set([
  "ITR.ITR1.CreationInfo.JSONCreationDate",
  "ITR.ITR1.CreationInfo.SWVersionNo",
  "ITR.ITR1.CreationInfo.SWCreatedBy",
  "ITR.ITR1.CreationInfo.JSONCreatedBy",
  "ITR.ITR1.CreationInfo.Digest",
  "ITR.ITR1.CreationInfo.IntermediaryCity",
  "ITR.ITR1.ITR1_IncomeDeductions.GrossSalary",
  "ITR.ITR1.ITR1_IncomeDeductions.AllwncExemptUs10.TotalAllwncExemptUs10",
  "ITR.ITR1.ITR1_IncomeDeductions.NetSalary",
  "ITR.ITR1.ITR1_IncomeDeductions.DeductionUs16",
  "ITR.ITR1.ITR1_IncomeDeductions.IncomeFromSal",
  "ITR.ITR1.ITR1_IncomeDeductions.AnnualValue",
  "ITR.ITR1.ITR1_IncomeDeductions.StandardDeduction",
  "ITR.ITR1.ITR1_IncomeDeductions.ThirtyPercentOfAnnualValue",
  "ITR.ITR1.ITR1_IncomeDeductions.InterestPayable",
  "ITR.ITR1.ITR1_IncomeDeductions.ScheduleUs24B.TotalInterestUs24B",
  "ITR.ITR1.ITR1_IncomeDeductions.TotalIncomeOfHP",
  "ITR.ITR1.ITR1_IncomeDeductions.OthersInc.IncomeOthSrc",
  "ITR.ITR1.ITR1_IncomeDeductions.IncomeOthSrc",
  "ITR.ITR1.ITR1_IncomeDeductions.ExemptIncAgriOthUs10.ExemptIncAgriOthUs10Total",
  "ITR.ITR1.ITR1_IncomeDeductions.ExemptIncAgriOthUs10Total",
  "ITR.ITR1.ITR1_IncomeDeductions.LTCG112A.LongCap112A",
  "ITR.ITR1.ITR1_IncomeDeductions.GrossTotIncome",
  "ITR.ITR1.ITR1_IncomeDeductions.GrossTotIncomeIncLTCG112A",
  "ITR.ITR1.ITR1_IncomeDeductions.UsrDeductUndChapVIA.TotalChapVIADeductions",
  "ITR.ITR1.ITR1_IncomeDeductions.DeductUndChapVIA.TotalChapVIADeductions",
  "ITR.ITR1.ITR1_IncomeDeductions.TotalIncome",
  "ITR.ITR1.TDSonSalaries.TotalTDSonSalaries",
  "ITR.ITR1.TDSonOthThanSals.TotalTDSonOthThanSals",
  "ITR.ITR1.ScheduleTDS3Dtls.TotalTDS3Details",
  "ITR.ITR1.ScheduleTCS.TotalSchTCS",
  "ITR.ITR1.TaxPayments.TotalTaxPayments",
  "ITR.ITR1.TaxPaid.TaxesPaid.TDS",
  "ITR.ITR1.TaxPaid.TaxesPaid.TCS",
  "ITR.ITR1.TaxPaid.TaxesPaid.AdvanceTax",
  "ITR.ITR1.TaxPaid.TaxesPaid.SelfAssessmentTax",
  "ITR.ITR1.TaxPaid.TaxesPaid.TotalTaxesPaid",
  "ITR.ITR1.ITR1_TaxComputation.TotalTaxPayable",
  "ITR.ITR1.ITR1_TaxComputation.Rebate87A",
  "ITR.ITR1.ITR1_TaxComputation.TaxPayableOnRebate",
  "ITR.ITR1.ITR1_TaxComputation.EducationCess",
  "ITR.ITR1.ITR1_TaxComputation.GrossTaxLiability",
  "ITR.ITR1.ITR1_TaxComputation.NetTaxLiability",
  "ITR.ITR1.ITR1_TaxComputation.TotalIntrstPay",
  "ITR.ITR1.ITR1_TaxComputation.TotTaxPlusIntrstPay",
]);

const prettifyLabel = (value: string): string =>
  value
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/_/g, " ")
    .trim();

const detectValidation = (key: string, value: JsonValue, path: string): ValidationHint | undefined => {
  const options = getFieldOptions(path);

  if (options) {
    return {
      options,
      message: `Choose a valid ${prettifyLabel(key)} option.`,
    };
  }

  if (typeof value === "number") {
    return {
      integer: Number.isInteger(value),
      nonNegative: true,
    };
  }

  if (typeof value !== "string") {
    return undefined;
  }

  if (DATE_REGEX.test(value)) {
    return {
      regex: DATE_REGEX,
      message: "Use YYYY-MM-DD format.",
    };
  }

  if (key === "EmailAddress") {
    return {
      email: true,
      regex: EMAIL_REGEX,
      message: "Enter a valid email address.",
    };
  }

  if (key === "PAN" || key === "AssesseeVerPAN") {
    return {
      regex: PAN_REGEX,
      message: "PAN must be 10 characters in standard format.",
    };
  }

  if (key === "AadhaarCardNo") {
    return {
      regex: AADHAAR_REGEX,
      message: "Aadhaar must be 12 digits.",
    };
  }

  if (key === "IFSCCode") {
    return {
      regex: IFSC_REGEX,
      message: "Enter a valid IFSC code.",
    };
  }

  return undefined;
};

const inferKind = (key: string, value: JsonValue, path: string): FormFieldSchema["kind"] => {
  const options = getFieldOptions(path);

  if (options) {
    if (key === "UseForRefund") {
      return "boolean-string";
    }

    if (typeof value === "string") {
      return "enum-string";
    }

    return "select";
  }

  if (Array.isArray(value)) {
    return "array";
  }

  if (typeof value === "object" && value !== null) {
    return "object";
  }

  if (typeof value === "number") {
    return "number";
  }

  if (typeof value === "boolean") {
    return "boolean";
  }

  if (typeof value === "string" && DATE_REGEX.test(value)) {
    return "date";
  }

  return "string";
};

const buildFieldSchema = (
  key: string,
  value: JsonValue,
  path: string,
): FormFieldSchema => {
  const field: FormFieldSchema = {
    key,
    path,
    label: prettifyLabel(key),
    kind: inferKind(key, value, path),
    required: true,
    defaultValue: value,
    validation: detectValidation(key, value, path),
    readOnly: READ_ONLY_PATHS.has(path),
  };

  if (field.kind === "object" && typeof value === "object" && value !== null && !Array.isArray(value)) {
    field.children = Object.entries(value).map(([childKey, childValue]) =>
      buildFieldSchema(childKey, childValue, `${path}.${childKey}`),
    );
  }

  if (field.kind === "array" && Array.isArray(value)) {
    const itemSample = value[0];
    field.itemSchema = buildFieldSchema(`${key}Item`, itemSample ?? "", `${path}.0`);
  }

  return field;
};

export const createFormSchema = <TSchema extends JsonObject>(schema: TSchema): FormFieldSchema[] =>
  Object.entries(schema).map(([key, value]) => buildFieldSchema(key, value, key));

export const useFormSchema = <TSchema extends JsonObject>(schema: TSchema): FormFieldSchema[] =>
  useMemo(() => createFormSchema(schema), [schema]);
