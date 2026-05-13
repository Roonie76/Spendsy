import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEventHandler } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useFormSchema } from "../hooks/useFormSchema";
import { createValidationSchema } from "../schemas/validationSchema";
import { createDraftStorage } from "../services/draftStorage";
import type { FormFieldSchema, ITRFormProps, JsonObject } from "../types";
import {
  buildExactJsonFromTemplate,
  mergeWithTemplateDefaults,
  parseUploadedJson,
} from "../utils/jsonTransformer";
import { generateITRFilename } from "../utils/filename";
import { getNestedObject, calculateITR1Fields } from "../utils/calculations";
import { DynamicField } from "./DynamicField";

const formShellClassName = "glass-container";
const stickyActionClassName = "sticky-footer";

type SectionDefinition = {
  key: string;
  badge: string;
  title: string;
  description: string;
  summary: (payload: JsonObject) => string;
  fieldFactory: (rootField: FormFieldSchema | undefined) => FormFieldSchema[];
};

const findFieldByPath = (
  field: FormFieldSchema | undefined,
  targetPath: string,
): FormFieldSchema | undefined => {
  if (!field) {
    return undefined;
  }

  if (field.path === targetPath) {
    return field;
  }

  for (const child of field.children ?? []) {
    const match = findFieldByPath(child, targetPath);
    if (match) {
      return match;
    }
  }

  return undefined;
};

const makeObjectGroup = (
  key: string,
  label: string,
  children: FormFieldSchema[],
): FormFieldSchema | undefined => {
  if (children.length === 0) {
    return undefined;
  }

  return {
    key,
    path: key,
    label,
    kind: "object",
    required: true,
    defaultValue: {},
    children,
  };
};

const pickChildren = (
  parent: FormFieldSchema | undefined,
  keys: string[],
): FormFieldSchema[] =>
  (parent?.children ?? []).filter((child) => keys.includes(child.key));

const getDisplayAmount = (value: unknown): string => {
  if (typeof value === "number") {
    return `Rs ${value.toLocaleString("en-IN")}`;
  }

  if (typeof value === "string" && value.trim()) {
    return value;
  }

  return "Provide your confirmation";
};

const createSectionDefinitions = (): SectionDefinition[] => [
  {
    key: "personal",
    badge: "P Info",
    title: "Personal Information",
    description: "Details of personal information, contact details, bank account details, and filing status.",
    summary: (payload) => {
      const itr = getNestedObject(payload, "ITR");
      const itr1 = itr ? getNestedObject(itr, "ITR1") : undefined;
      const personalInfo = itr1 ? getNestedObject(itr1, "PersonalInfo") : undefined;
      return typeof personalInfo?.PAN === "string" && personalInfo.PAN.trim()
        ? personalInfo.PAN
        : "Provide your confirmation";
    },
    fieldFactory: (rootField) => {
      const itr1 = findFieldByPath(rootField, "ITR.ITR1");
      return [
        "ITR.ITR1.CreationInfo",
        "ITR.ITR1.PersonalInfo",
        "ITR.ITR1.FilingStatus",
        "ITR.ITR1.Refund",
        "ITR.ITR1.Verification",
      ]
        .map((path) => findFieldByPath(itr1, path))
        .filter((field): field is FormFieldSchema => Boolean(field));
    },
  },
  {
    key: "gti",
    badge: "GTI",
    title: "Gross Total Income",
    description: "Please verify your income sources as collected from various sources and proceed.",
    summary: (payload) =>
      getDisplayAmount(
        (((payload.ITR as JsonObject | undefined)?.ITR1 as JsonObject | undefined)
          ?.ITR1_IncomeDeductions as JsonObject | undefined)?.GrossTotIncome,
      ),
    fieldFactory: (rootField) => {
      const income = findFieldByPath(rootField, "ITR.ITR1.ITR1_IncomeDeductions");
      const gtiField = makeObjectGroup("gross_total_income", "Gross Total Income", pickChildren(income, [
        "GrossSalary",
        "IncomeNotified89A",
        "IncomeNotified89AType",
        "IncomeNotifiedOther89A",
        "AllwncExemptUs10",
        "Increliefus89A",
        "NetSalary",
        "DeductionUs16",
        "DeductionUs16ia",
        "EntertainmentAlw16ii",
        "ProfessionalTaxUs16iii",
        "IncomeFromSal",
        "TypeOfHP",
        "GrossRentReceived",
        "TaxPaidToLocalAuth",
        "AnnualValue",
        "StandardDeduction",
        "InterestPayable",
        "ArrearsUnrealizedRentRcvd",
        "ScheduleUs24B",
        "TotalIncomeOfHP",
        "OthersInc",
        "IncomeOthSrc",
        "ExemptIncAgriOthUs10",
        "ExemptIncAgriOthUs10Total",
        "LTCG112A",
        "GrossTotIncome",
        "GrossTotIncomeIncLTCG112A",
      ]));

      return gtiField ? [gtiField] : [];
    },
  },
  {
    key: "deductions",
    badge: "Tot",
    title: "Total Deductions",
    description: "Please verify your deduction details and proceed further.",
    summary: (payload) =>
      getDisplayAmount(
        ((((payload.ITR as JsonObject | undefined)?.ITR1 as JsonObject | undefined)
          ?.ITR1_IncomeDeductions as JsonObject | undefined)?.DeductUndChapVIA as JsonObject | undefined)
          ?.TotalChapVIADeductions,
      ),
    fieldFactory: (rootField) => {
      const income = findFieldByPath(rootField, "ITR.ITR1.ITR1_IncomeDeductions");
      const deductionsField = makeObjectGroup("total_deductions", "Total Deductions", pickChildren(income, [
        "UsrDeductUndChapVIA",
        "DeductUndChapVIA",
        "TotalIncome",
      ]));

      return deductionsField ? [deductionsField] : [];
    },
  },
  {
    key: "tax_paid",
    badge: "TP",
    title: "Tax Paid",
    description: "Please verify details of taxes paid by you in the last financial year and proceed further.",
    summary: (payload) =>
      getDisplayAmount(
        ((((payload.ITR as JsonObject | undefined)?.ITR1 as JsonObject | undefined)?.TaxPaid as JsonObject | undefined)
          ?.TaxesPaid as JsonObject | undefined)?.TotalTaxesPaid,
      ),
    fieldFactory: (rootField) => {
      const itr1 = findFieldByPath(rootField, "ITR.ITR1");
      return [
        "ITR.ITR1.TDSonSalaries",
        "ITR.ITR1.TDSonOthThanSals",
        "ITR.ITR1.ScheduleTDS3Dtls",
        "ITR.ITR1.ScheduleTCS",
        "ITR.ITR1.TaxPayments",
        "ITR.ITR1.TaxPaid",
      ]
        .map((path) => findFieldByPath(itr1, path))
        .filter((field): field is FormFieldSchema => Boolean(field));
    },
  },
  {
    key: "tax_liability",
    badge: "Tax Liab",
    title: "Verify your tax liability details",
    description: "Please verify your tax liability details and proceed further.",
    summary: (payload) =>
      getDisplayAmount(
        (((payload.ITR as JsonObject | undefined)?.ITR1 as JsonObject | undefined)
          ?.ITR1_TaxComputation as JsonObject | undefined)?.TotTaxPlusIntrstPay,
      ),
    fieldFactory: (rootField) => {
      const income = findFieldByPath(rootField, "ITR.ITR1.ITR1_IncomeDeductions");
      const computation = findFieldByPath(rootField, "ITR.ITR1.ITR1_TaxComputation");
      const computationOfIncome = makeObjectGroup(
        "computation_of_income",
        "Computation of Income",
        [
          ...pickChildren(income, [
            "GrossTotIncome",
            "GrossTotIncomeIncLTCG112A",
          ]),
          ...pickChildren(findFieldByPath(income, "ITR.ITR1.ITR1_IncomeDeductions.DeductUndChapVIA"), [
            "TotalChapVIADeductions",
          ]),
          ...pickChildren(income, ["TotalIncome"]),
        ],
      );

      const taxPayableGroup = makeObjectGroup(
        "computation_of_tax_payable",
        "Computation of Tax Payable",
        pickChildren(computation, [
          "TotalTaxPayable",
          "Rebate87A",
          "TaxPayableOnRebate",
          "EducationCess",
          "GrossTaxLiability",
          "Section89",
          "NetTaxLiability",
        ]),
      );

      const interestGroup = makeObjectGroup(
        "total_interest_and_fee",
        "Total Interest and Fee",
        [
          ...(findFieldByPath(computation, "ITR.ITR1.ITR1_TaxComputation.IntrstPay")?.children ?? []),
          ...pickChildren(computation, ["TotalIntrstPay"]),
        ],
      );

      const totalGroup = makeObjectGroup(
        "total_tax_fee_interest",
        "Total Tax, Fee and Interest",
        pickChildren(computation, [
          "NetTaxLiability",
          "TotalIntrstPay",
          "TotTaxPlusIntrstPay",
        ]),
      );

      return [
        computationOfIncome,
        taxPayableGroup,
        interestGroup,
        totalGroup,
      ].filter((field): field is FormFieldSchema => Boolean(field));
    },
  },
];

export const FormRenderer = <TSchema extends JsonObject>({
  schema,
  initialData,
  onSubmit,
  onChange,
  onError,
  submitLabel = "Generate ITR JSON",
  className,
  storageKey = "itr-form-draft",
  title = "Income Tax Return Form",
  description = "Schema-driven form renderer with exact JSON reconstruction.",
  disabled = false,
}: ITRFormProps<TSchema>) => {
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const fields = useFormSchema(schema);
  const [activeSectionIndex, setActiveSectionIndex] = useState(0);
  const [confirmedSections, setConfirmedSections] = useState<string[]>([]);
  const validationSchema = useMemo(() => createValidationSchema(schema), [schema]);
  const draftStorage = useMemo(() => createDraftStorage<TSchema>(storageKey), [storageKey]);
  const defaultValues = useMemo(
    () => mergeWithTemplateDefaults(schema, initialData),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [schema], // intentionally omit initialData — handled by autofill effect below
  );

  const methods = useForm<JsonObject>({
    resolver: zodResolver(validationSchema as never),
    mode: "onBlur",
    reValidateMode: "onChange",
    defaultValues,
  });

  const { handleSubmit, reset, watch, setValue } = methods;
  const watchedValues = watch();
  const livePayload = useMemo(
    () => buildExactJsonFromTemplate(schema, watchedValues as Partial<TSchema>),
    [schema, watchedValues],
  );
  const rootField = fields[0];
  const sectionDefinitions = useMemo(() => createSectionDefinitions(), []);

  // Initial mount only — full reset from schema defaults
  const mountedRef = useRef(false);
  useEffect(() => {
    if (!mountedRef.current) {
      mountedRef.current = true;
      reset(mergeWithTemplateDefaults(schema, initialData));
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Autofill patch — merge incoming initialData onto current values without wiping user input
  const prevInitialDataRef = useRef(initialData);
  useEffect(() => {
    if (initialData === prevInitialDataRef.current) return;
    prevInitialDataRef.current = initialData;
    if (!initialData || Object.keys(initialData).length === 0) return;

    // Deep-walk the patch and call setValue only for leaf nodes that exist in schema
    const applyPatch = (patch: JsonObject, pathPrefix = "") => {
      for (const key of Object.keys(patch)) {
        const path = pathPrefix ? `${pathPrefix}.${key}` : key;
        const val = patch[key];
        if (val !== null && val !== undefined && typeof val === "object" && !Array.isArray(val)) {
          applyPatch(val as JsonObject, path);
        } else if (val !== null && val !== undefined) {
          setValue(path as never, val as never, { shouldDirty: true, shouldTouch: false, shouldValidate: false });
        }
      }
    };
    applyPatch(initialData as JsonObject);
  }, [initialData, setValue]);

  useEffect(() => {
    if (!onChange) {
      return;
    }

    const subscription = watch((value) => {
      onChange(buildExactJsonFromTemplate(schema, value as Partial<TSchema>));
    });

    return () => subscription.unsubscribe();
  }, [onChange, schema, watch]);

  useEffect(() => {
    const values = methods.getValues() as JsonObject;
    const itr = getNestedObject(values, "ITR");
    const itr1 = itr ? getNestedObject(itr, "ITR1") : undefined;

    if (!itr1) {
      return;
    }

    const setDerivedValue = (path: string, nextValue: number | string) => {
      const currentValue = methods.getValues(path as never) as unknown;
      if (currentValue === nextValue) {
        return;
      }

      methods.setValue(path as never, nextValue as never, {
        shouldDirty: false,
        shouldTouch: false,
        shouldValidate: false,
      });
    };

    const updates = calculateITR1Fields(itr1);
    Object.entries(updates).forEach(([path, value]) => {
      setDerivedValue(path, value);
    });
  }, [methods, watchedValues]);

  const submitHandler = handleSubmit(
    async (values) => {
      const now = new Date();
      const timestamp = `${now.toISOString().split("T")[0]} ${now.toTimeString().split(" ")[0]}`;
      const updatedValues = { ...values };

      // Automatically inject current date and time
      const itr1 = (updatedValues.ITR as any)?.ITR1;
      if (itr1?.CreationInfo) {
        itr1.CreationInfo.JSONCreationDate = timestamp;
      }

      const payload = buildExactJsonFromTemplate(schema, updatedValues as Partial<TSchema>);
      await onSubmit(payload);
    },
    (errors) => {
      onError?.(errors);
    },
  );

  const handleSaveDraft = () => {
    const payload = buildExactJsonFromTemplate(schema, methods.getValues() as Partial<TSchema>);
    draftStorage.save(payload);
  };

  const handleLoadDraft = () => {
    const draft = draftStorage.load();

    if (!draft) {
      return;
    }

    reset(mergeWithTemplateDefaults(schema, draft));
  };

  const handleResetToTemplate = () => {
    reset(mergeWithTemplateDefaults(schema, initialData));
  };

  const handleDownloadDraft = () => {
    const now = new Date();
    const timestamp = `${now.toISOString().split("T")[0]} ${now.toTimeString().split(" ")[0]}`;
    const values = methods.getValues();
    const updatedValues = { ...values };

    // Automatically inject current date and time
    const itr1 = (updatedValues.ITR as any)?.ITR1;
    if (itr1?.CreationInfo) {
      itr1.CreationInfo.JSONCreationDate = timestamp;
    }

    const payload = buildExactJsonFromTemplate(schema, updatedValues as Partial<TSchema>);
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = generateITRFilename(payload);
    link.type = "application/json";
    document.body.appendChild(link);
    link.click();
    setTimeout(() => {
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }, 200);
  };

  const handleImportClick = () => {
    uploadInputRef.current?.click();
  };

  const handleImportJson: ChangeEventHandler<HTMLInputElement> = async (event) => {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    try {
      const raw = await file.text();
      const parsed = parseUploadedJson(raw) as Partial<TSchema>;
      reset(mergeWithTemplateDefaults(schema, parsed));
    } catch (error) {
      onError?.(error);
    } finally {
      event.target.value = "";
    }
  };

  const activeSection = sectionDefinitions[activeSectionIndex];
  const activeFields = activeSection?.fieldFactory(rootField) ?? [];

  const markSectionConfirmed = (sectionKey: string) => {
    setConfirmedSections((current) =>
      current.includes(sectionKey) ? current : [...current, sectionKey],
    );
  };

  const goToSection = (index: number) => {
    if (index <= activeSectionIndex || confirmedSections.length >= index) {
      setActiveSectionIndex(index);
    }
  };

  const handleContinueSection = () => {
    if (!activeSection) {
      return;
    }

    markSectionConfirmed(activeSection.key);
    setActiveSectionIndex((current) =>
      current < sectionDefinitions.length - 1 ? current + 1 : current,
    );
  };

  const isSectionEnabled = (index: number) =>
    index <= activeSectionIndex || confirmedSections.length >= index;

  return (
    <FormProvider {...methods}>
      <form className={`${formShellClassName} ${className ?? ""}`.trim()} onSubmit={submitHandler}>
        <input
          ref={uploadInputRef}
          accept="application/json"
          className="hidden"
          onChange={handleImportJson}
          type="file"
        />
        <div className="form-header">
          <div className="header-info">
            <h2>{title}</h2>
            <p>{description}</p>
          </div>
          <div className="button-group">
            <button className="btn btn-secondary" disabled={disabled} onClick={handleImportClick} type="button">
              Import JSON
            </button>
            <button className="btn btn-secondary" disabled={disabled} onClick={handleSaveDraft} type="button">
              Save Draft
            </button>
            <button className="btn btn-secondary" disabled={disabled} onClick={handleLoadDraft} type="button">
              Load Draft
            </button>
            <button className="btn btn-secondary" disabled={disabled} onClick={handleDownloadDraft} type="button">
              Download JSON
            </button>
            <button className="btn btn-danger" style={{ marginLeft: 'auto' }} disabled={disabled} onClick={handleResetToTemplate} type="button">
              Reset
            </button>
          </div>
        </div>

        <div className="summary-shell">
          <div className="summary-header">
            <div>
              <h3>Return Summary</h3>
              <p>Complete each mandatory stage before proceeding to verification.</p>
            </div>
            <div className="summary-rocket" aria-hidden="true">Launch</div>
          </div>

          <div className="summary-cards">
            {sectionDefinitions.map((section, index) => {
              const confirmed = confirmedSections.includes(section.key);
              const enabled = isSectionEnabled(index);
              const active = index === activeSectionIndex;

              return (
                <button
                  key={section.key}
                  className={`summary-card ${active ? "active" : ""} ${confirmed ? "confirmed" : ""} ${enabled ? "" : "locked"}`.trim()}
                  disabled={!enabled}
                  onClick={() => goToSection(index)}
                  type="button"
                >
                  <div className="summary-badge">{section.badge}</div>
                  <div className="summary-copy">
                    <div className="summary-title-row">
                      <strong>{section.title}</strong>
                      <span>{confirmed ? "Confirmed" : "Mandatory"}</span>
                    </div>
                    <p>{section.description}</p>
                  </div>
                  <div className="summary-meta">
                    <strong>{section.summary(livePayload)}</strong>
                    <span>{confirmed ? "Modify if required" : "Provide your confirmation"}</span>
                  </div>
                  <div className="summary-arrow">›</div>
                </button>
              );
            })}
          </div>
        </div>

        <div className="step-panel">
          <div className="step-panel-header">
            <div>
              <h3>{activeSection.title}</h3>
              <p>{activeSection.description}</p>
            </div>
            <div className="step-progress">
              Step {activeSectionIndex + 1} of {sectionDefinitions.length}
            </div>
          </div>

          <div className="form-sections">
            {activeFields.map((field) => (
              <DynamicField key={field.path} disabled={disabled} field={field} />
            ))}
          </div>
        </div>

        <div className={stickyActionClassName}>
          <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
            <button
              className="btn btn-secondary"
              disabled={disabled || activeSectionIndex === 0}
              onClick={() => setActiveSectionIndex((current) => Math.max(0, current - 1))}
              type="button"
            >
              Back
            </button>
            <p style={{ fontSize: '0.875rem', color: 'var(--itr-text-dim)', margin: 0 }}>
              Submission generates official ITR-1 schema structure.
            </p>
          </div>
          <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
            {activeSectionIndex < sectionDefinitions.length - 1 ? (
              <button
                className="btn btn-primary"
                disabled={disabled}
                onClick={handleContinueSection}
                type="button"
              >
                Confirm And Continue
              </button>
            ) : (
              <button className="btn btn-primary" style={{ padding: '12px 32px' }} disabled={disabled} type="submit">
                {submitLabel}
              </button>
            )}
          </div>
        </div>
      </form>
    </FormProvider>
  );
};

export const ITRForm = FormRenderer;
