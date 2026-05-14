export { FormRenderer, ITRForm } from "./components/FormRenderer";
export { DynamicField } from "./components/DynamicField";
export { useFormSchema, createFormSchema } from "./hooks/useFormSchema";
export { createValidationSchema } from "./schemas/validationSchema";
export { itrSampleSchema } from "./schemas/itrSampleSchema";
export {
  itr1AppExtractedEnums,
  itr1AppFieldNames,
  itr1AppLogicNotes,
} from "./schemas/itr1AppReference";
export { createDraftStorage } from "./services/draftStorage";
export {
  buildExactJsonFromTemplate,
  deepCloneJson,
  isValidJsonObject,
  mergeWithTemplateDefaults,
  parseUploadedJson,
} from "./utils/jsonTransformer";
export { generateITRFilename } from "./utils/filename";
export type {
  DraftStorageAdapter,
  FieldKind,
  FormFieldSchema,
  ITRFormProps,
  JsonObject,
  JsonPrimitive,
  JsonValue,
  ValidationHint,
} from "./types";
