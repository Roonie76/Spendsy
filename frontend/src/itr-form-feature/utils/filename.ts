import type { JsonObject } from "../types";

export const generateITRFilename = (payload: JsonObject | null): string => {
  if (!payload) return "itr_payload.json";

  const itr1 = (payload.ITR as any)?.ITR1;
  const pan = itr1?.PersonalInfo?.PAN || "UNKNOWN_PAN";
  const ay = itr1?.Form_ITR1?.AssessmentYear || "2025";
  
  // Format AY: 2025 -> 2025-26
  const ayNext = (parseInt(ay) + 1).toString().slice(-2);
  const ayFormatted = `${ay}-${ayNext}`;

  const now = new Date();
  
  // Date format: M-D-YYYY
  const datePart = `${now.getMonth() + 1}-${now.getDate()}-${now.getFullYear()}`;
  
  // Time format: H-MM-SS-AM/PM
  const hours = now.getHours();
  const minutes = now.getMinutes().toString().padStart(2, "0");
  const seconds = now.getSeconds().toString().padStart(2, "0");
  const ampm = hours >= 12 ? "PM" : "AM";
  const displayHours = (hours % 12 || 12).toString();
  const timePart = `${displayHours}-${minutes}-${seconds}-${ampm}`;

  // Full format: [PAN]_upload_[AYFormatted][DatePart]--[TimePart].json
  const filename = `${pan}_upload_${ayFormatted}${datePart}--${timePart}.json`.replace(/\s+/g, "_");
  return filename;
};
