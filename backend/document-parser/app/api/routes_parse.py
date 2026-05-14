"""
Document parsing endpoints.

POST /parse/form16
POST /parse/broker
POST /parse/bank
POST /parse/detect          ← auto-detect doc type, parse, verify
"""
from __future__ import annotations

import hashlib
import logging
from typing import Optional

import fitz
from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile, status

from app.core.config import settings
from app.core.schemas import (
    BankStatementData,
    BrokerStatementData,
    DocumentType,
    Form16Data,
    ParseResponse,
    VerificationStatus,
)
from app.services.autofill import bank_to_autofill, broker_to_autofill, form16_to_autofill
from app.services.glm_ocr import GLMOCREngine, sha256_of
from app.services.verifier import verify_broker_statement, verify_form16

logger = logging.getLogger("doc_parser.routes")
router = APIRouter(prefix="/parse", tags=["parse"])

MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024


def _auth(x_internal_key: Optional[str]):
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal API key.")


def _get_pdf_creator(pdf_bytes: bytes) -> Optional[str]:
    """Extract PDF creator metadata without full parse."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        meta = doc.metadata
        doc.close()
        return meta.get("creator") or meta.get("producer")
    except Exception:
        return None


@router.post("/form16", response_model=ParseResponse)
async def parse_form16(
    file: UploadFile = File(...),
    user_pan: Optional[str] = Form(None),
    ais_tds: Optional[float] = Form(None),
    x_internal_key: Optional[str] = Header(None),
):
    """
    Upload Form 16 PDF → OCR with GLM-4V → verify → return autofill map.

    - user_pan: the PAN of the logged-in user (for identity binding)
    - ais_tds: TDS amount from user's 26AS (for cross-reference)
    """
    _auth(x_internal_key)

    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_BYTES:
        raise HTTPException(413, f"File too large. Max {settings.max_upload_size_mb}MB.")
    if not pdf_bytes[:4] == b"%PDF":
        raise HTTPException(400, "Uploaded file does not appear to be a PDF.")

    doc_hash = sha256_of(pdf_bytes)
    pdf_creator = _get_pdf_creator(pdf_bytes)

    engine = GLMOCREngine()
    try:
        raw, _, page_count = engine.parse_pdf(pdf_bytes, DocumentType.FORM_16)
    except Exception as e:
        logger.exception("GLM OCR failed for Form 16")
        raise HTTPException(500, f"Document parsing failed: {str(e)}")

    # Attach metadata from PDF headers
    raw["pdf_creator"] = pdf_creator

    extracted: Form16Data = engine.to_form16(raw)
    verification = verify_form16(
        data=extracted,
        pdf_creator=pdf_creator,
        user_pan=user_pan,
        ais_tds=ais_tds,
    )
    autofill = form16_to_autofill(extracted)

    warnings = [
        c.message
        for c in verification.checks
        if c.status == VerificationStatus.FAILED
    ]

    return ParseResponse(
        document_type=DocumentType.FORM_16,
        document_hash=doc_hash,
        page_count=page_count,
        extracted=extracted,
        verification=verification,
        autofill=autofill,
        warnings=warnings,
    )


@router.post("/broker", response_model=ParseResponse)
async def parse_broker(
    file: UploadFile = File(...),
    user_pan: Optional[str] = Form(None),
    ais_capital_gains: Optional[float] = Form(None),
    x_internal_key: Optional[str] = Header(None),
):
    """Upload broker capital gains statement → OCR → verify → autofill."""
    _auth(x_internal_key)

    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_BYTES:
        raise HTTPException(413, f"File too large. Max {settings.max_upload_size_mb}MB.")

    doc_hash = sha256_of(pdf_bytes)
    engine = GLMOCREngine()
    try:
        raw, _, page_count = engine.parse_pdf(pdf_bytes, DocumentType.BROKER_STATEMENT)
    except Exception as e:
        logger.exception("GLM OCR failed for broker statement")
        raise HTTPException(500, f"Document parsing failed: {str(e)}")

    extracted: BrokerStatementData = engine.to_broker(raw)
    verification = verify_broker_statement(
        data=extracted,
        user_pan=user_pan,
        ais_capital_gains=ais_capital_gains,
    )
    autofill = broker_to_autofill(extracted)

    warnings = [c.message for c in verification.checks if c.status == VerificationStatus.FAILED]

    return ParseResponse(
        document_type=DocumentType.BROKER_STATEMENT,
        document_hash=doc_hash,
        page_count=page_count,
        extracted=extracted,
        verification=verification,
        autofill=autofill,
        warnings=warnings,
    )


@router.post("/bank", response_model=ParseResponse)
async def parse_bank(
    file: UploadFile = File(...),
    x_internal_key: Optional[str] = Header(None),
):
    """Upload bank statement PDF → OCR → extract interest income → autofill."""
    _auth(x_internal_key)

    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_BYTES:
        raise HTTPException(413, f"File too large. Max {settings.max_upload_size_mb}MB.")

    doc_hash = sha256_of(pdf_bytes)
    engine = GLMOCREngine()
    try:
        raw, _, page_count = engine.parse_pdf(pdf_bytes, DocumentType.BANK_STATEMENT)
    except Exception as e:
        logger.exception("GLM OCR failed for bank statement")
        raise HTTPException(500, f"Document parsing failed: {str(e)}")

    extracted: BankStatementData = engine.to_bank(raw)
    autofill = bank_to_autofill(extracted)

    # Basic verification for bank statements
    from app.core.schemas import VerificationCheck, VerificationResult, VerificationStatus
    checks = []
    if extracted.bank_name:
        checks.append(VerificationCheck(name="bank_name", status=VerificationStatus.PASSED, message=f"Bank identified: {extracted.bank_name}"))
    else:
        checks.append(VerificationCheck(name="bank_name", status=VerificationStatus.WARNING, message="Bank name not detected."))

    verification = VerificationResult(
        overall=VerificationStatus.PASSED if extracted.bank_name else VerificationStatus.WARNING,
        checks=checks,
        trust_score=90 if extracted.bank_name else 60,
    )

    return ParseResponse(
        document_type=DocumentType.BANK_STATEMENT,
        document_hash=doc_hash,
        page_count=page_count,
        extracted=extracted,
        verification=verification,
        autofill=autofill,
        warnings=[],
    )
