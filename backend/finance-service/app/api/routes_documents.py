"""
Document Upload API — routes_documents.py

Endpoints:
  POST   /tax/documents/upload        — multipart upload, auto-detect doc_type,
                                        parse, store ParsedDocument, return prefill_diff
  POST   /tax/documents/upload-multi  — batch upload (up to 10 files)
  GET    /tax/documents/list          — list user's ParsedDocuments for an AY
  GET    /tax/documents/{id}          — fetch single ParsedDocument + parsed data
  DELETE /tax/documents/{id}          — soft-delete (sets parse_status="deleted")
  POST   /tax/documents/{id}/reparse  — re-run parser on stored content
  GET    /tax/documents/bundle/{ay}   — return merged PrefillBundle for all docs + transactions
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import asdict
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi import status as http_status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import UserContext, get_current_user
from app.models import ParsedDocument, Transaction

from app.utils.response import error_response, success_response

# Parser imports (lazy where heavy deps involved)
from app.services.parser.form16_parser import parse_form16, form16_to_itr_fields
from app.services.parser.form26as_parser import parse_form26as, form26as_to_itr_fields
from app.services.parser.cg_statement_parser import parse_cg_statement, cg_to_itr_fields
from app.services.parser.investment_parser import (
    parse_investment_doc,
    investment_to_itr_fields,
    DOC_TYPE_MAP as _INV_DOC_TYPES,
)

router = APIRouter(prefix="/tax/documents", tags=["documents"])
logger = logging.getLogger("finance.documents")

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024   # 20 MB per file
MAX_BATCH_FILES     = 10

# Filename-hint → doc_type mapping (checked before content-sniff)
_FILENAME_HINTS: dict[str, str] = {
    "form16":         "form16",
    "form 16":        "form16",
    "form-16":        "form16",
    "26as":           "form26as",
    "form26as":       "form26as",
    "form 26as":      "form26as",
    "ais":            "form26as",
    "tis":            "form26as",
    "capital gain":   "cg_statement",
    "capital gains":  "cg_statement",
    "tax p&l":        "cg_statement",
    "tax pl":         "cg_statement",
    "zerodha":        "cg_statement",
    "groww cg":       "cg_statement",
    "upstox":         "cg_statement",
    "cams":           "cg_statement",
    "kfintech":       "cg_statement",
    "nps":            "nps_statement",
    "ppf":            "ppf_passbook",
    "elss":           "elss_statement",
    "rent receipt":   "rent_receipt",
    "rent":           "rent_receipt",
    "home loan":      "hl_certificate",
    "housing loan":   "hl_certificate",
    "interest cert":  "hl_certificate",
    "health ins":     "health_ins",
    "mediclaim":      "health_ins",
}

# doc_type → parser function + itr_fields mapper
_PARSER_MAP: dict[str, tuple] = {
    "form16":        (parse_form16,        form16_to_itr_fields),
    "form26as":      (parse_form26as,      form26as_to_itr_fields),
    "cg_statement":  (parse_cg_statement,  cg_to_itr_fields),
}
# Investment types handled by investment_parser
_INV_TYPES = {"nps_statement", "ppf_passbook", "elss_statement",
              "rent_receipt", "hl_certificate", "health_ins"}

# investment_parser doc_type alias map (routes_documents key → investment_parser key)
_INV_ALIAS: dict[str, str] = {
    "nps_statement":  "nps",
    "ppf_passbook":   "ppf",
    "elss_statement": "elss",
    "rent_receipt":   "rent",
    "hl_certificate": "home_loan",
    "health_ins":     "home_loan",  # no specific parser yet — best-effort
}

# doc_type → parser_version (import from each parser module)
_PARSER_VERSIONS: dict[str, str] = {
    "form16":       "1.0.0",
    "form26as":     "1.0.0",
    "cg_statement": "1.0.0",
    "nps_statement":"1.0.0",
    "ppf_passbook": "1.0.0",
    "elss_statement":"1.0.0",
    "rent_receipt": "1.0.0",
    "hl_certificate":"1.0.0",
    "health_ins":   "1.0.0",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _detect_doc_type(filename: str, content_head: bytes) -> str:
    """
    Best-effort doc_type detection from filename hint first,
    then content-sniff for known header strings.
    """
    fn_lower = filename.lower()
    for hint, dtype in _FILENAME_HINTS.items():
        if hint in fn_lower:
            return dtype

    # Content sniff (first 2 KB decoded)
    try:
        snippet = content_head[:2048].decode("utf-8", errors="ignore").lower()
    except Exception:
        snippet = ""

    if "form 16" in snippet or "part a" in snippet and "tds" in snippet:
        return "form16"
    if "form 26as" in snippet or "annual tax statement" in snippet or "annual information" in snippet:
        return "form26as"
    if "capital gain" in snippet or "tax p&l" in snippet or "zerodha" in snippet:
        return "cg_statement"
    if "pran" in snippet or "national pension" in snippet:
        return "nps_statement"
    if "public provident" in snippet or "ppf" in snippet:
        return "ppf_passbook"
    if "elss" in snippet or "equity linked saving" in snippet:
        return "elss_statement"
    if "rent receipt" in snippet or "landlord" in snippet:
        return "rent_receipt"
    if "home loan" in snippet or "housing loan" in snippet:
        return "hl_certificate"

    return "other"


def _run_parser(doc_type: str, content: bytes, filename: str) -> dict:
    """
    Run the appropriate parser and return a normalised dict with keys:
      parsed_result, itr_fields, confidence_score, field_confidence,
      page_count, ocr_used, parser_version, error
    """
    out: dict[str, Any] = {
        "parsed_result": None,
        "itr_fields": {},
        "confidence_score": 0.0,
        "field_confidence": {},
        "page_count": 0,
        "ocr_used": False,
        "parser_version": _PARSER_VERSIONS.get(doc_type, "1.0.0"),
        "error": None,
    }
    try:
        if doc_type in _PARSER_MAP:
            parse_fn, mapper_fn = _PARSER_MAP[doc_type]
            result = parse_fn(content, filename)
            out["parsed_result"] = result
            out["itr_fields"]    = mapper_fn(result)
            out["confidence_score"] = getattr(result, "confidence_score", 0.0)
            out["field_confidence"] = getattr(result, "field_confidence", {})
            out["page_count"]    = getattr(result, "page_count", 0)
            out["ocr_used"]      = getattr(result, "ocr_used", False)

        elif doc_type in _INV_TYPES:
            inv_key = _INV_ALIAS.get(doc_type, "other")
            result = parse_investment_doc(content, inv_key)
            out["parsed_result"] = result
            out["itr_fields"]    = investment_to_itr_fields(result, inv_key)
            out["confidence_score"] = getattr(result, "confidence_score", 0.0)
            out["field_confidence"] = getattr(result, "field_confidence", {})
            out["page_count"]    = getattr(result, "page_count", 0)
            out["ocr_used"]      = getattr(result, "ocr_used", False)
        else:
            out["error"] = f"No parser for doc_type='{doc_type}'"

    except Exception as exc:
        logger.exception("Parser error doc_type=%s file=%s", doc_type, filename)
        out["error"] = str(exc)

    return out


def _parsed_result_to_dict(result: Any) -> dict:
    """Best-effort serialisation of a parser dataclass."""
    if result is None:
        return {}
    try:
        from dataclasses import asdict as _asdict
        return _asdict(result)
    except Exception:
        return {}


def _doc_to_response(doc: ParsedDocument) -> dict:
    return {
        "id":               doc.id,
        "doc_type":         doc.doc_type,
        "filename":         doc.filename,
        "ay":               doc.ay,
        "parse_status":     doc.parse_status,
        "parse_error":      doc.parse_error,
        "confidence_score": float(doc.confidence_score or 0),
        "field_confidence": doc.field_confidence or {},
        "page_count":       doc.page_count,
        "ocr_used":         doc.ocr_used,
        "parser_version":   doc.parser_version,
        "parsed_data":      doc.parsed_data or {},
        "created_at":       doc.created_at.isoformat() if doc.created_at else None,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    doc_type: Optional[str] = Form(default=None),
    ay: str = Form(default="2025-26"),
    submission_id: Optional[int] = Form(default=None),
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """
    Upload and parse a single tax document.
    doc_type is auto-detected if not supplied.
    Returns the ParsedDocument record + prefill_diff.
    """
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {MAX_FILE_SIZE_BYTES // (1024*1024)} MB limit.",
        )

    filename = file.filename or "upload.pdf"
    file_hash = _sha256(content)

    # Dedup: same file already parsed for this user+AY?
    existing = (
        db.query(ParsedDocument)
        .filter_by(user_id=user.user_id, file_hash=file_hash, ay=ay)
        .first()
    )
    if existing and existing.parse_status == "done":
        return success_response(
            request,
            {"document": _doc_to_response(existing), "duplicate": True},
            message="Document already parsed (duplicate detected).",
        )

    # Detect doc_type
    detected_type = doc_type or _detect_doc_type(filename, content)

    # Create DB record (pending)
    doc = ParsedDocument(
        user_id=user.user_id,
        submission_id=submission_id,
        ay=ay,
        doc_type=detected_type,
        filename=filename,
        file_hash=file_hash,
        parse_status="pending",
    )
    db.add(doc)
    db.flush()   # get doc.id without committing

    # Run parser
    parse_out = _run_parser(detected_type, content, filename)

    if parse_out["error"]:
        doc.parse_status = "failed"
        doc.parse_error  = parse_out["error"][:500]
    else:
        doc.parse_status     = "done"
        doc.parsed_data      = {
            "raw": _parsed_result_to_dict(parse_out["parsed_result"]),
            "itr_fields": parse_out["itr_fields"],
        }
        doc.confidence_score = parse_out["confidence_score"]
        doc.field_confidence = parse_out["field_confidence"]
        doc.page_count       = parse_out["page_count"]
        doc.ocr_used         = parse_out["ocr_used"]
        doc.parser_version   = parse_out["parser_version"]

    try:
        db.commit()
        db.refresh(doc)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save parsed document.")

    return success_response(
        request,
        {
            "document":    _doc_to_response(doc),
            "itr_fields":  parse_out["itr_fields"],
            "duplicate":   False,
        },
        message=f"Document parsed successfully ({detected_type})." if not parse_out["error"]
                else f"Parse failed: {parse_out['error']}",
    )


@router.post("/upload-multi")
async def upload_documents_batch(
    request: Request,
    files: list[UploadFile] = File(...),
    ay: str = Form(default="2025-26"),
    submission_id: Optional[int] = Form(default=None),
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Upload and parse up to 10 files in a single request."""
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_BATCH_FILES} files per batch.",
        )

    results = []
    for f in files:
        content = await f.read()
        if len(content) > MAX_FILE_SIZE_BYTES:
            results.append({"filename": f.filename, "status": "skipped",
                             "reason": "file too large"})
            continue

        filename  = f.filename or "upload.pdf"
        file_hash = _sha256(content)
        detected  = _detect_doc_type(filename, content)

        existing = (
            db.query(ParsedDocument)
            .filter_by(user_id=user.user_id, file_hash=file_hash, ay=ay)
            .first()
        )
        if existing and existing.parse_status == "done":
            results.append({"filename": filename, "status": "duplicate",
                             "document_id": existing.id})
            continue

        doc = ParsedDocument(
            user_id=user.user_id, submission_id=submission_id, ay=ay,
            doc_type=detected, filename=filename, file_hash=file_hash,
            parse_status="pending",
        )
        db.add(doc)
        db.flush()

        parse_out = _run_parser(detected, content, filename)

        if parse_out["error"]:
            doc.parse_status = "failed"
            doc.parse_error  = parse_out["error"][:500]
            results.append({"filename": filename, "status": "failed",
                             "error": parse_out["error"], "document_id": doc.id})
        else:
            doc.parse_status     = "done"
            doc.parsed_data      = {
                "raw": _parsed_result_to_dict(parse_out["parsed_result"]),
                "itr_fields": parse_out["itr_fields"],
            }
            doc.confidence_score = parse_out["confidence_score"]
            doc.field_confidence = parse_out["field_confidence"]
            doc.page_count       = parse_out["page_count"]
            doc.ocr_used         = parse_out["ocr_used"]
            doc.parser_version   = parse_out["parser_version"]
            results.append({"filename": filename, "status": "done",
                             "doc_type": detected, "document_id": doc.id,
                             "confidence": parse_out["confidence_score"]})

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save documents.")

    return success_response(request, {"results": results},
                            message=f"Processed {len(files)} file(s).")


@router.get("/list")
def list_documents(
    request: Request,
    ay: str = "2025-26",
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """List all parsed documents for the user's AY (excludes deleted)."""
    docs = (
        db.query(ParsedDocument)
        .filter(
            ParsedDocument.user_id == user.user_id,
            ParsedDocument.ay == ay,
            ParsedDocument.parse_status != "deleted",
        )
        .order_by(ParsedDocument.created_at.desc())
        .all()
    )
    return success_response(
        request,
        {"documents": [_doc_to_response(d) for d in docs], "count": len(docs)},
    )



@router.get("/{doc_id}")
def get_document(
    request: Request,
    doc_id: int,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    doc = db.query(ParsedDocument).filter_by(id=doc_id, user_id=user.user_id).first()
    if not doc or doc.parse_status == "deleted":
        raise HTTPException(status_code=404, detail="Document not found.")
    return success_response(request, {"document": _doc_to_response(doc)})


@router.delete("/{doc_id}")
def delete_document(
    request: Request,
    doc_id: int,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    doc = db.query(ParsedDocument).filter_by(id=doc_id, user_id=user.user_id).first()
    if not doc or doc.parse_status == "deleted":
        raise HTTPException(status_code=404, detail="Document not found.")
    doc.parse_status = "deleted"
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Delete failed.")
    return success_response(request, {"id": doc_id}, message="Document removed.")


@router.post("/{doc_id}/reparse")
async def reparse_document(
    request: Request,
    doc_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Re-upload the file and re-run the parser (e.g. after OCR correction)."""
    doc = db.query(ParsedDocument).filter_by(id=doc_id, user_id=user.user_id).first()
    if not doc or doc.parse_status == "deleted":
        raise HTTPException(status_code=404, detail="Document not found.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large.")

    parse_out = _run_parser(doc.doc_type, content, file.filename or doc.filename or "")

    doc.file_hash     = _sha256(content)
    doc.filename      = file.filename or doc.filename
    if parse_out["error"]:
        doc.parse_status = "failed"
        doc.parse_error  = parse_out["error"][:500]
    else:
        doc.parse_status     = "done"
        doc.parse_error      = None
        doc.parsed_data      = {
            "raw": _parsed_result_to_dict(parse_out["parsed_result"]),
            "itr_fields": parse_out["itr_fields"],
        }
        doc.confidence_score = parse_out["confidence_score"]
        doc.field_confidence = parse_out["field_confidence"]
        doc.page_count       = parse_out["page_count"]
        doc.ocr_used         = parse_out["ocr_used"]
        doc.parser_version   = parse_out["parser_version"]

    try:
        db.commit()
        db.refresh(doc)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save re-parse result.")

    return success_response(request, {"document": _doc_to_response(doc)},
                            message="Document re-parsed.")


# ── Hydration helpers ─────────────────────────────────────────────────────────

def _dict_to_result(d: dict, cls):
    """Shallow hydration of a stored dict back into a dataclass."""
    import inspect
    sig = inspect.signature(cls.__init__)
    params = {k: v.default for k, v in sig.parameters.items() if k != "self"}
    kwargs = {k: d.get(k, params[k]) for k in params}
    return cls(**kwargs)


def _dict_to_cg_result(d: dict):
    from app.services.parser.cg_statement_parser import CGParseResult, CGAssetClass

    def _cls(sub: dict) -> CGAssetClass:
        if isinstance(sub, dict):
            return CGAssetClass(
                buy_value=sub.get("buy_value", 0.0),
                sell_value=sub.get("sell_value", 0.0),
                gain=sub.get("gain", 0.0),
            )
        return CGAssetClass()

    r = CGParseResult()
    r.broker           = d.get("broker", "GENERIC")
    r.assessment_year  = d.get("assessment_year", "2025-26")
    r.equity_stcg      = _cls(d.get("equity_stcg", {}))
    r.equity_ltcg      = _cls(d.get("equity_ltcg", {}))
    r.equity_mf_stcg   = _cls(d.get("equity_mf_stcg", {}))
    r.equity_mf_ltcg   = _cls(d.get("equity_mf_ltcg", {}))
    r.debt_stcg        = _cls(d.get("debt_stcg", {}))
    r.debt_ltcg        = _cls(d.get("debt_ltcg", {}))
    r.gold_stcg        = _cls(d.get("gold_stcg", {}))
    r.gold_ltcg        = _cls(d.get("gold_ltcg", {}))
    r.crypto           = _cls(d.get("crypto", {}))
    r.stcg_111a_net    = d.get("stcg_111a_net", 0.0)
    r.ltcg_112a_net    = d.get("ltcg_112a_net", 0.0)
    r.stcg_other_net   = d.get("stcg_other_net", 0.0)
    r.ltcg_other_net   = d.get("ltcg_other_net", 0.0)
    r.crypto_net       = d.get("crypto_net", 0.0)
    r.stcl_111a        = d.get("stcl_111a", 0.0)
    r.ltcl_112a        = d.get("ltcl_112a", 0.0)
    r.stcl_other       = d.get("stcl_other", 0.0)
    r.ltcl_other       = d.get("ltcl_other", 0.0)
    r.confidence_score = d.get("confidence_score", 0.0)
    r.field_confidence = d.get("field_confidence", {})
    return r


def _dict_to_inv_result(d: dict, inv_key: str):
    from app.services.parser import investment_parser as ip
    type_map = {
        "nps":       ip.NPSParseResult,
        "ppf":       ip.PPFParseResult,
        "elss":      ip.ELSSParseResult,
        "rent":      ip.RentReceiptParseResult,
        "home_loan": ip.HomeLoanCertParseResult,
    }
    cls = type_map.get(inv_key)
    if cls is None:
        return None
    return _dict_to_result(d, cls)
