import { apiFetch } from "../api";

export function parseDigitalPdfUpload(apiBaseUrl, file) {
  const formData = new FormData();
  formData.append("file", file);

  return apiFetch(`${apiBaseUrl}/parse-digital-pdf`, {
    method: "POST",
    body: formData,
  });
}
