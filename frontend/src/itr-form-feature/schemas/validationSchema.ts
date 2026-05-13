import { z } from "zod";

import { getFieldOptions } from "./fieldOptions";
import type { JsonObject, JsonValue } from "../types";

const DATE_REGEX = /^\d{4}-\d{2}-\d{2}$/;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PAN_REGEX = /^[A-Z]{5}[0-9]{4}[A-Z]$/;
const AADHAAR_REGEX = /^\d{12}$/;
const IFSC_REGEX = /^[A-Z]{4}0[A-Z0-9]{6}$/;

const isObject = (value: JsonValue): value is JsonObject =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const buildStringSchema = (key: string, sample: string, path: string) => {
  const options = getFieldOptions(path);

  if (options) {
    const allowedValues = new Set(options.map((option) => String(option.value)));
    return z.string().refine((value) => allowedValues.has(value), {
      message: `Choose a valid ${key}.`,
    });
  }

  if (DATE_REGEX.test(sample)) {
    return z.string().regex(DATE_REGEX, "Use YYYY-MM-DD format.");
  }

  if (key === "EmailAddress") {
    return z.string().regex(EMAIL_REGEX, "Enter a valid email address.");
  }

  if (key === "PAN" || key === "AssesseeVerPAN") {
    return z
      .string()
      .trim()
      .toUpperCase()
      .regex(PAN_REGEX, "PAN must be 10 characters in standard format.");
  }

  if (key === "AadhaarCardNo") {
    return z.string().regex(AADHAAR_REGEX, "Aadhaar must be 12 digits.");
  }

  if (key === "IFSCCode") {
    return z
      .string()
      .trim()
      .toUpperCase()
      .regex(IFSC_REGEX, "Enter a valid IFSC code.");
  }

  return z.string().min(1, `${key} is required.`);
};

const buildNodeSchema = (key: string, value: JsonValue, path: string): z.ZodTypeAny => {
  if (Array.isArray(value)) {
    const itemSchema = value.length > 0 ? buildNodeSchema(`${key}Item`, value[0], `${path}.0`) : z.any();
    return z.array(itemSchema).min(1, `${key} must contain at least one item.`);
  }

  if (isObject(value)) {
    const shape: Record<string, z.ZodTypeAny> = {};
    Object.entries(value).forEach(([childKey, childValue]) => {
      shape[childKey] = buildNodeSchema(childKey, childValue, `${path}.${childKey}`);
    });
    return z.object(shape);
  }

  if (typeof value === "number") {
    const options = getFieldOptions(path);

    if (options) {
      const allowedValues = new Set(options.map((option) => Number(option.value)));
      return z.coerce.number().refine((current) => allowedValues.has(current), {
        message: `Choose a valid ${key}.`,
      });
    }

    return z
      .coerce
      .number()
      .finite()
      .refine((current) => current >= 0, `${key} cannot be negative.`);
  }

  if (typeof value === "boolean") {
    return z.coerce.boolean();
  }

  if (typeof value === "string") {
    return buildStringSchema(key, value, path);
  }

  return z.any();
};

export const createValidationSchema = <TSchema extends JsonObject>(schema: TSchema) =>
  buildNodeSchema("root", schema, "root") as z.ZodType<TSchema>;
