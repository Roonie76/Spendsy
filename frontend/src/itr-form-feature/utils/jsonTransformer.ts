import type { JsonObject, JsonValue } from "../types";

const isObject = (value: JsonValue | undefined): value is JsonObject =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export const deepCloneJson = <T extends JsonValue>(value: T): T =>
  JSON.parse(JSON.stringify(value)) as T;

export const buildExactJsonFromTemplate = <T extends JsonObject>(
  template: T,
  formValues?: unknown,
): T => mergeFromTemplate(template, formValues as JsonValue | undefined) as T;

export const mergeWithTemplateDefaults = <T extends JsonObject>(
  template: T,
  value?: unknown,
): T => mergeFromTemplate(template, value as JsonValue | undefined) as T;

export const isValidJsonObject = (value: unknown): value is JsonObject =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export const parseUploadedJson = (raw: string): JsonObject => {
  const parsed = JSON.parse(raw) as unknown;

  if (!isValidJsonObject(parsed)) {
    throw new Error("Uploaded JSON must be a valid object at the root.");
  }

  return parsed;
};

function mergeFromTemplate(
  template: JsonValue,
  candidate?: JsonValue,
): JsonValue {
  if (Array.isArray(template)) {
    const source = Array.isArray(candidate) ? candidate : template;

    if (template.length === 0) {
      return Array.isArray(source) ? deepCloneJson(source) : [];
    }

    const itemTemplate = template[0];
    return source.map((item) => mergeFromTemplate(itemTemplate, item));
  }

  if (isObject(template)) {
    const source = isObject(candidate) ? candidate : {};
    const result: JsonObject = {};

    Object.keys(template).forEach((key) => {
      result[key] = mergeFromTemplate(template[key], source[key]);
    });

    return result;
  }

  if (candidate === undefined || candidate === null) {
    return deepCloneJson(template);
  }

  if (typeof template === "number") {
    return typeof candidate === "number" && Number.isFinite(candidate)
      ? candidate
      : template;
  }

  if (typeof template === "boolean") {
    return typeof candidate === "boolean" ? candidate : template;
  }

  if (typeof template === "string") {
    return typeof candidate === "string" ? candidate : template;
  }

  return candidate ?? template;
}
