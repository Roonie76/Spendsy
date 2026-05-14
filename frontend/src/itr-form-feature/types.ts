import type { ReactNode } from "react";

export type JsonPrimitive = string | number | boolean | null;
export interface JsonObject {
  [key: string]: JsonValue;
}
export interface JsonArray extends Array<JsonValue> {}
export type JsonValue = JsonPrimitive | JsonObject | JsonArray;

export type FieldKind =
  | "string"
  | "number"
  | "boolean"
  | "date"
  | "select"
  | "boolean-string"
  | "enum-string"
  | "object"
  | "array";

export interface SelectOption {
  value: string | number;
  label: string;
}

export interface ValidationHint {
  min?: number;
  max?: number;
  regex?: RegExp;
  message?: string;
  email?: boolean;
  integer?: boolean;
  nonNegative?: boolean;
  options?: SelectOption[];
}

export interface FormFieldSchema {
  key: string;
  path: string;
  label: string;
  kind: FieldKind;
  required: boolean;
  defaultValue: JsonValue;
  placeholder?: string;
  description?: string;
  validation?: ValidationHint;
  readOnly?: boolean;
  children?: FormFieldSchema[];
  itemSchema?: FormFieldSchema;
}

export interface ITRFormProps<TSchema extends JsonObject = JsonObject> {
  schema: TSchema;
  initialData?: Partial<TSchema>;
  onSubmit: (payload: TSchema) => void | Promise<void>;
  onChange?: (payload: TSchema) => void;
  onError?: (errors: unknown) => void;
  submitLabel?: string;
  className?: string;
  storageKey?: string;
  title?: ReactNode;
  description?: ReactNode;
  disabled?: boolean;
}

export interface DraftStorageAdapter<TSchema extends JsonObject = JsonObject> {
  save: (value: TSchema) => void;
  load: () => TSchema | null;
  clear: () => void;
}
