import type { DraftStorageAdapter, JsonObject } from "../types";
import { isValidJsonObject, parseUploadedJson } from "../utils/jsonTransformer";

export const createDraftStorage = <TSchema extends JsonObject>(
  storageKey: string,
): DraftStorageAdapter<TSchema> => ({
  save: (value) => {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(storageKey, JSON.stringify(value));
  },
  load: () => {
    if (typeof window === "undefined") {
      return null;
    }

    const raw = window.localStorage.getItem(storageKey);

    if (!raw) {
      return null;
    }

    try {
      const parsed = parseUploadedJson(raw);
      return isValidJsonObject(parsed) ? (parsed as TSchema) : null;
    } catch {
      return null;
    }
  },
  clear: () => {
    if (typeof window === "undefined") {
      return;
    }

    window.localStorage.removeItem(storageKey);
  },
});
