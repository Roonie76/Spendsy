"""
GLM-4V OCR engine.

Flow:
  PDF bytes → pdf2image (per page PNGs) → base64 encode
           → GLM-4V prompt per page → structured JSON response
           → merge multi-page results → Form16Data / BrokerStatementData

GLM-4V API: https://open.bigmodel.cn/dev/api#glm-4v
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import re
from typing import Any

import fitz  # PyMuPDF — faster than pdf2image for text PDFs
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential
from zhipuai import ZhipuAI

from app.core.config import settings
from app.core.schemas import (
    BankStatementData,
    BrokerStatementData,
    DocumentType,
    Form16Data,
)

logger = logging.getLogger("doc_parser.glm_ocr")

# ── Prompts ───────────────────────────────────────────────────────────────────

FORM16_PROMPT = """
You are an expert Indian tax document parser. This image is a page from an Indian Form 16 (TDS certificate issued by an employer for FY 2025-26 / AY 2026-27).

Extract ALL of the following fields that are visible on this page. Return ONLY valid JSON — no explanation, no markdown.

{
  "employee_name": "string or null",
  "employee_pan": "string or null",
  "employer_name": "string or null",
  "employer_tan": "string or null",
  "employer_pan": "string or null",
  "assessment_year": "string or null",
  "financial_year": "string or null",
  "certificate_number": "string or null",
  "gross_salary": number_or_null,
  "basic_salary": number_or_null,
  "hra_received": number_or_null,
  "special_allowance": number_or_null,
  "other_allowances": number_or_null,
  "perquisites": number_or_null,
  "hra_exemption": number_or_null,
  "lta_exemption": number_or_null,
  "standard_deduction": number_or_null,
  "deduction_80c": number_or_null,
  "deduction_80d": number_or_null,
  "deduction_nps_80ccd": number_or_null,
  "deduction_employer_nps": number_or_null,
  "home_loan_interest": number_or_null,
  "tds_deducted": number_or_null,
  "net_taxable_salary": number_or_null
}

Rules:
- All monetary amounts must be plain numbers (no commas, no ₹ symbol).
- If a field is not visible on this page, set it to null.
- PAN format: 5 uppercase letters + 4 digits + 1 uppercase letter (e.g. ABCDE1234F).
- TAN format: 4 uppercase letters + 5 digits + 1 uppercase letter (e.g. BLRX12345A).
- Assessment year format: "YYYY-YY" (e.g. "2026-27").
"""

BROKER_PROMPT = """
You are an expert Indian tax document parser. This image is from a capital gains statement / broker statement for FY 2025-26.

Extract the following fields and return ONLY valid JSON:

{
  "broker_name": "string or null",
  "pan": "string or null",
  "financial_year": "string or null",
  "stcg_equity": number_or_null,
  "ltcg_equity": number_or_null,
  "stcg_debt": number_or_null,
  "ltcg_debt": number_or_null,
  "tds_on_gains": number_or_null
}

Rules:
- STCG = Short Term Capital Gains. LTCG = Long Term Capital Gains.
- Equity includes equity mutual funds. Debt includes debt MFs, bonds.
- All monetary values as plain numbers without commas or currency symbols.
- Negative values (losses) should be negative numbers.
"""

BANK_PROMPT = """
You are an expert Indian tax document parser. This image is from an Indian bank statement or interest certificate for FY 2025-26.

Extract the following fields and return ONLY valid JSON:

{
  "bank_name": "string or null",
  "account_number_masked": "string or null",
  "ifsc": "string or null",
  "account_type": "savings or current or null",
  "savings_interest": number_or_null,
  "fd_interest": number_or_null,
  "rd_interest": number_or_null
}

Rules:
- All monetary values as plain numbers.
- Mask account number to last 4 digits if full number visible (e.g. "XXXXXXXX1234").
"""

PROMPT_MAP = {
    DocumentType.FORM_16: FORM16_PROMPT,
    DocumentType.FORM_16A: FORM16_PROMPT,
    DocumentType.BROKER_STATEMENT: BROKER_PROMPT,
    DocumentType.BANK_STATEMENT: BANK_PROMPT,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pdf_to_images(pdf_bytes: bytes, max_pages: int = 10) -> list[Image.Image]:
    """Convert PDF pages to PIL images using PyMuPDF (fast, no poppler needed)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    for page_num in range(min(len(doc), max_pages)):
        page = doc.load_page(page_num)
        # Render at 150 DPI — good enough for OCR, keeps token count low
        mat = fitz.Matrix(150 / 72, 150 / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    doc.close()
    return images


def image_to_base64(img: Image.Image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def extract_json_from_response(text: str) -> dict:
    """
    GLM sometimes wraps JSON in markdown code blocks.
    Strip and parse robustly.
    """
    # Remove markdown code fences
    text = re.sub(r"```(?:json)?", "", text).strip()
    # Find first { ... } block
    match = re.search(r"\{[\s\S]+\}", text)
    if not match:
        raise ValueError(f"No JSON object found in GLM response: {text[:200]}")
    return json.loads(match.group(0))


def merge_page_results(pages: list[dict]) -> dict:
    """
    Merge extracted fields across multiple pages.
    Non-null values from later pages override earlier ones,
    EXCEPT for numeric accumulations (e.g. tds_deducted sums up).
    """
    ACCUMULATE = {"tds_deducted", "deduction_80c"}
    merged: dict[str, Any] = {}
    for page in pages:
        for k, v in page.items():
            if v is None:
                continue
            if k in ACCUMULATE and k in merged and merged[k] is not None:
                merged[k] = (merged[k] or 0) + v
            else:
                merged[k] = v
    return merged


# ── Main OCR class ────────────────────────────────────────────────────────────

class GLMOCREngine:
    def __init__(self):
        if not settings.glm_api_key:
            raise RuntimeError(
                "GLM_API_KEY not set. Add it to .env: GLM_API_KEY=your_key_here"
            )
        self.client = ZhipuAI(api_key=settings.glm_api_key)
        self.model = settings.glm_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _call_glm(self, image_b64: str, prompt: str) -> dict:
        """Call GLM-4V with a single page image and return parsed JSON."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}"
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            temperature=0.1,   # low temperature = more deterministic extraction
            max_tokens=1024,
        )
        raw = response.choices[0].message.content
        logger.debug("GLM raw response (truncated): %s", raw[:300])
        return extract_json_from_response(raw)

    def parse_pdf(
        self,
        pdf_bytes: bytes,
        doc_type: DocumentType,
    ) -> tuple[dict, str, int]:
        """
        Parse a PDF document using GLM-4V OCR.

        Returns:
            (merged_fields_dict, sha256_hash, page_count)
        """
        doc_hash = sha256_of(pdf_bytes)
        prompt = PROMPT_MAP.get(doc_type, FORM16_PROMPT)
        images = pdf_to_images(pdf_bytes, max_pages=settings.max_pdf_pages)
        page_count = len(images)

        if page_count == 0:
            raise ValueError("PDF has no renderable pages.")

        page_results = []
        for i, img in enumerate(images):
            logger.info("OCR page %d/%d (doc_type=%s)", i + 1, page_count, doc_type)
            b64 = image_to_base64(img)
            try:
                result = self._call_glm(b64, prompt)
                page_results.append(result)
            except Exception as e:
                logger.warning("GLM failed on page %d: %s", i + 1, e)
                page_results.append({})

        merged = merge_page_results(page_results)
        return merged, doc_hash, page_count

    def to_form16(self, raw: dict) -> Form16Data:
        return Form16Data(**{k: v for k, v in raw.items() if k in Form16Data.model_fields})

    def to_broker(self, raw: dict) -> BrokerStatementData:
        return BrokerStatementData(**{k: v for k, v in raw.items() if k in BrokerStatementData.model_fields})

    def to_bank(self, raw: dict) -> BankStatementData:
        return BankStatementData(**{k: v for k, v in raw.items() if k in BankStatementData.model_fields})
