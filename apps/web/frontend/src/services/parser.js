import { apiFetch } from "../api";

export function parseDigitalPdfUpload(apiBaseUrl, file, accountType = "debit") {
  const formData = new FormData();
  formData.append("file", file);
  if (accountType) {
    formData.append("account_type", accountType);
  }

  return apiFetch(`${apiBaseUrl}/parse-digital-pdf`, {
    method: "POST",
    body: formData,
  });
}

