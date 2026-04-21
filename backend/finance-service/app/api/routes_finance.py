from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

import hashlib
import logging
import re
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, Request, UploadFile, status
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core import cryptography as security_crypto
from app.core.audit import record_audit as _audit
from app.core.config import settings
from app.core.database import check_database_connection, get_db
from app.core.redis import enqueue_task, get_identity_from_request, is_rate_limited, record_event, clear_user_financial_cache
from app.core.security import UserContext, get_current_user
from app.models import ApiAuditLog, CreditCard, DebitCard, FinancePlan, ITRData, Loan, NetWorthSnapshot, StatementRecord, TaxProfile, Transaction, UserProfile, WealthItem
from pydantic import BaseModel
from typing import List
from app.schemas import (
    CreditCardOut,
    CreditCardPayload,
    DebitCardOut,
    DebitCardPayload,
    ITRPayload,
    LoanOut,
    LoanPayload,
    TaxProfilePayload,
    TransactionCategory,
    TransactionPayload,
    UserProfilePayload,
    WealthPayload,
    StatementRecordOut,
    StatementRecordPayload,
    NetWorthSnapshotOut,
    NetWorthSnapshotPayload,
)
from app.services.parser.digital_deterministic_parser import parse_transactions
from app.utils.files import sanitize_filename, validate_file_security
from app.utils.response import error_response, success_response
from app.utils.error_codes import ErrorCode

router = APIRouter(tags=["finance"])
logger = logging.getLogger("finance.routes")

TITLE_DYNAMIC_PATTERNS = (
    re.compile(r"\bref(?:erence)?\s*(?:no|num(?:ber)?|id)?\s*[:#-]?\s*[a-z0-9/-]{4,}\b", re.IGNORECASE),
    re.compile(r"\b(?:txn|tx|transaction|utr|rrn)\s*(?:no|num(?:ber)?|id)?\s*[:#-]?\s*[a-z0-9/-]{4,}\b", re.IGNORECASE),
    re.compile(r"\bupi\s*/\s*[a-z0-9/-]{6,}\b", re.IGNORECASE),
    re.compile(r"\b\d{6,}\b"),
)
TITLE_NON_ALNUM = re.compile(r"[^a-z0-9]+")
TITLE_WHITESPACE = re.compile(r"\s+")
FINGERPRINT_STOPWORDS = {
    "by",
    "cr",
    "credit",
    "debit",
    "dr",
    "from",
    "imps",
    "inward",
    "neft",
    "no",
    "org",
    "outward",
    "payment",
    "ref",
    "rtgs",
    "to",
    "transaction",
    "transfer",
    "tx",
    "txn",
    "upi",
    "via",
}

def _safe_category(raw: str | None) -> str:
    value = str(raw or "other").strip().lower()
    if value not in {e.value for e in TransactionCategory}:
        return "other"
    return value


def _safe_type(raw: str | None) -> str:
    value = str(raw or "expense").strip().lower()
    if value in {"income", "credit", "cr", "deposit"}:
        return "income"
    if value in {"expense", "debit", "dr", "withdrawal", "paid"}:
        return "expense"
    return "expense"


def _safe_source(raw: str | None) -> str:
    value = str(raw or "manual").strip().lower()
    return value if value in {"manual", "statement"} else "manual"


def _safe_confidence(raw: float | str | None) -> float:
    if isinstance(raw, str):
        mapping = {"high": 1.0, "medium": 0.7, "low": 0.4}
        return mapping.get(raw.strip().lower(), 0.0)
    try:
        value = float(raw or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, value))


def _safe_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw))
    except Exception:
        return None


def normalize_title(title: str) -> str:
    value = str(title or "").strip().lower()
    for pattern in TITLE_DYNAMIC_PATTERNS:
        value = pattern.sub(" ", value)
    value = TITLE_NON_ALNUM.sub(" ", value)
    value = TITLE_WHITESPACE.sub(" ", value).strip()
    return value or "parsed transaction"


def normalize_title_for_fingerprint(title: str) -> str:
    normalized = normalize_title(title)
    canonical_tokens: list[str] = []
    seen_tokens: set[str] = set()
    for token in normalized.split():
        if token in FINGERPRINT_STOPWORDS or token in seen_tokens:
            continue
        seen_tokens.add(token)
        canonical_tokens.append(token)

    if not canonical_tokens:
        canonical_tokens = normalized.split()
    return " ".join(sorted(canonical_tokens)) or "parsed transaction"


def generate_transaction_fingerprint(user_id: int, tx_date: date, amount: Decimal | str, tx_type: str, title: str) -> str:
    amount_value = Decimal(str(amount)).quantize(Decimal("0.01"))
    canonical_title = normalize_title_for_fingerprint(title)
    raw = f"{user_id}|{tx_date.isoformat()}|{amount_value}|{tx_type}|{canonical_title}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _compute_transaction_fingerprint(user_id: int, tx_date: date, amount: Decimal | str, tx_type: str, raw_title: str) -> str:
    return generate_transaction_fingerprint(user_id, tx_date, amount, tx_type, raw_title)


def _display_title(tx: Transaction) -> str:
    return (tx.raw_description or tx.title or "Untitled Transaction").strip() or "Untitled Transaction"


def _infer_category(description: str, tx_type: str) -> str:
    text = str(description or "").lower()

    if tx_type == "income":
        investment_signals = ("interest", "dividend", "mutual fund", "sip", "nps", "stock")
        if any(signal in text for signal in investment_signals):
            return "investment"

    keyword_map: dict[str, str] = {
        "food": "food",
        "restaurant": "food",
        "swiggy": "food",
        "zomato": "food",
        "uber": "travel",
        "ola": "travel",
        "fuel": "travel",
        "petrol": "travel",
        "diesel": "travel",
        "flight": "travel",
        "train": "travel",
        "rent": "rent",
        "landlord": "rent",
        "electricity": "utilities",
        "water": "utilities",
        "gas": "utilities",
        "internet": "utilities",
        "mobile": "utilities",
        "shopping": "shopping",
        "amazon": "shopping",
        "flipkart": "shopping",
        "myntra": "shopping",
        "sip": "investment",
        "mf": "investment",
        "mutual fund": "investment",
        "nps": "investment",
        "stock": "investment",
        "apple": "tech",
        "google": "tech",
        "electronics": "tech",
        "doctor": "health",
        "hospital": "health",
        "medicine": "health",
        "pharmacy": "health",
        "school": "education",
        "college": "education",
        "tuition": "education",
        "course": "education",
    }
    for keyword, category in keyword_map.items():
        if keyword in text:
            return category
    return "other"


def _build_financial_summary(db: Session, user_id: int) -> dict:
    income = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == user_id, Transaction.type == "income"
    ).scalar()
    expense = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == user_id, Transaction.type == "expense"
    ).scalar()
    count = db.query(func.count(Transaction.id)).filter(Transaction.user_id == user_id).scalar()

    income_val = Decimal(str(income or 0))
    expense_val = Decimal(str(expense or 0))

    return {
        "income": str(income_val.quantize(Decimal("0.01"))),
        "expense": str(expense_val.quantize(Decimal("0.01"))),
        "balance": str((income_val - expense_val).quantize(Decimal("0.01"))),
        "transaction_count": int(count or 0),
    }


def _persist_parsed_transactions(db: Session, user_id: int, parsed_transactions: list[dict]) -> int:
    saved = 0
    seen_in_batch: set[str] = set()
    imported_statement_hashes = {
        row_hash
        for (row_hash,) in db.query(Transaction.statement_hash)
        .filter(
            Transaction.user_id == user_id,
            Transaction.source == "statement",
            Transaction.statement_hash.isnot(None),
        )
        .distinct()
        .all()
        if row_hash
    }
    for item in parsed_transactions:
        raw_amount = item.get("amount")
        try:
            amount = Decimal(str(raw_amount))
        except (InvalidOperation, TypeError):
            continue

        if amount <= 0:
            continue

        raw_title = (item.get("description") or "Parsed Transaction").strip() or "Parsed Transaction"
        title = normalize_title(raw_title)[:255] or "parsed transaction"
        tx_type = _safe_type(item.get("type"))
        tx_category = _safe_category(item.get("category"))
        tx_date = _safe_date(item.get("date")) or date.today()
        fingerprint = _compute_transaction_fingerprint(user_id, tx_date, amount, tx_type, raw_title)
        tx_balance = item.get("balance")
        tx_source = _safe_source(item.get("source"))
        statement_hash = str(item.get("statement_hash") or "").strip() or None
        statement_row_hash = str(item.get("statement_row_hash") or "").strip() or None
        
        # Phase 1: Global Reconciliation status and flags
        tx_status = "flagged" if not item.get("is_valid", True) else "active"
        reconciliation_flags = item.get("reconciliation_flags", [])
        
        try:
            balance_value = Decimal(str(tx_balance)) if tx_balance not in (None, "") else None
        except (InvalidOperation, TypeError):
            balance_value = None

        if tx_source == "statement" and statement_hash in imported_statement_hashes:
            continue

        if fingerprint in seen_in_batch:
            continue
        seen_in_batch.add(fingerprint)

        if tx_source == "statement" and statement_hash and statement_row_hash:
            exists = db.query(Transaction.id).filter(
                Transaction.user_id == user_id,
                Transaction.source == tx_source,
                Transaction.statement_hash == statement_hash,
                Transaction.statement_row_hash == statement_row_hash,
            ).first()
            if exists:
                continue

        fingerprint_exists = db.query(Transaction.id).filter(
            Transaction.user_id == user_id,
            Transaction.fingerprint == fingerprint,
        ).first()
        if fingerprint_exists:
            continue

        legacy_semantic_exists = db.query(Transaction.id).filter(
            Transaction.user_id == user_id,
            Transaction.fingerprint.is_(None),
            Transaction.date == tx_date,
            Transaction.amount == amount,
            Transaction.type == tx_type,
            Transaction.title == title,
        ).first()
        if legacy_semantic_exists:
            continue

        raw_confidence = item.get("confidence")
        try:
            confidence_val = int(round(float(raw_confidence) * 100)) if raw_confidence is not None else 100
            confidence_val = max(0, min(100, confidence_val))
        except (TypeError, ValueError):
            confidence_val = 100

        tx = Transaction(
            user_id=user_id,
            title=title,
            raw_description=raw_title[:255],
            amount=amount,
            type=tx_type,
            category=tx_category,
            is_recurring=False,
            date=tx_date,
            balance=balance_value,
            source=tx_source,
            statement_hash=statement_hash,
            statement_row_hash=statement_row_hash,
            fingerprint=fingerprint,
            confidence=confidence_val,
            status=tx_status,
            reconciliation_flags=reconciliation_flags,
            account_type=item.get("account_type"),
        )

        db.add(tx)
        saved += 1

    try:
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise
    except IntegrityError:
        db.rollback()
        logger.warning("statement_persist conflict user_id=%s", user_id)
    except Exception:
        db.rollback()
        raise
    return saved


def _enforce_ownership(user: UserContext, path_uid: str) -> None:
    """Raise HTTP 403 immediately if URL uid != token uid and != token id."""
    # Allow match against either UUID (user.uid) or numeric ID (user.id)
    if str(path_uid) != user.uid and str(path_uid) != str(user.id):
        logger.warning(
            "IDOR_DENIED: path_uid=%s token_uid=%s token_id=%s",
            path_uid,
            user.uid,
            user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you may only access your own resources",
        )


@router.get("/health")
def health(request: Request):
    db_ok, db_detail = check_database_connection()
    http_status = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return success_response(
        request,
        {
            "service": "finance",
            "status": "ok" if db_ok else "degraded",
            "database_connected": db_ok,
            "database_detail": db_detail if not db_ok else "ok",
        },
        message="Finance service healthy" if db_ok else "Finance service degraded",
        http_status=http_status,
    )


@router.get("/ready")
def readiness(request: Request, db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except SQLAlchemyError:
        db.rollback()
        db_ok = False
    status_code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return success_response(
        request,
        {"service": "finance", "db_ok": db_ok},
        message="Ready" if db_ok else "Not ready",
        http_status=status_code,
    )


@router.get("/summary")
def financial_summary(request: Request, user: UserContext = Depends(get_current_user), db: Session = Depends(get_db)):
    summary = _build_financial_summary(db, user.id)
    return success_response(request, summary, message="Financial summary")


@router.get("/profile/{uid}")
@router.post("/profile/{uid}")
def profile_settings(
    request: Request,
    uid: str,
    payload: UserProfilePayload | None = None,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # IDOR fix: strict 403 if URL doesn't match token
    _enforce_ownership(user, uid)

    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise
        db.refresh(profile)

    if request.method == "POST" and payload is not None:
        updates = payload.model_dump(exclude_unset=True, by_alias=False)
        if "monthly_income" in updates:
            profile.monthly_income = updates["monthly_income"]
        if "monthly_budget" in updates:
            profile.monthly_budget = updates["monthly_budget"]
        if "daily_budget" in updates:
            profile.daily_budget = updates["daily_budget"]
        if "is_business" in updates:
            profile.is_business = updates["is_business"]
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise
        _audit(db, request, action="profile_updated", resource_type="profile", status_code=200, user=user)

    payload_out = {
        "username": user.username,
        "email": user.email,
        "monthlyIncome": str(profile.monthly_income or Decimal("0")),
        "monthlyBudget": str(profile.monthly_budget or Decimal("0")),
        "dailyBudget": str(profile.daily_budget or Decimal("0")),
        "is_business": bool(profile.is_business),
    }
    return success_response(request, payload_out)


@router.post("/transactions", responses={400: {"model": dict}, 422: {"model": dict}, 201: {"model": dict}})
def add_transaction(
    request: Request,
    payload: TransactionPayload,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    identity = get_identity_from_request(request)
    if is_rate_limited("finance:transaction", identity, settings.finance_rate_limit_default, settings.finance_rate_limit_window_seconds):
        return error_response(request, "Too many transaction creation attempts", code=ErrorCode.RATE_LIMIT_EXCEEDED, http_status=429)

    data = payload.model_dump(exclude_unset=True)
    logger.info(f"add_transaction received: {data}")
    if "amount" not in data or data["amount"] is None:
        return error_response(request, "Amount is required and must be > 0", code=ErrorCode.INVALID_AMOUNT)
    if "type" not in data or data["type"] is None:
        return error_response(request, "Transaction type must be 'income' or 'expense'", code=ErrorCode.INVALID_TRANSACTION_TYPE)

    raw_title = (data.get("title") or data.get("description") or "Untitled Transaction").strip() or "Untitled Transaction"
    title = normalize_title(raw_title)[:255] or "untitled transaction"
    category = data.get("category")
    category_val = category.value if hasattr(category, "value") else (str(category) if category else "other")

    tx = Transaction(
        user_id=user.id,
        title=title,
        raw_description=raw_title[:255],
        amount=data["amount"],
        type=data["type"],
        category=category_val,
        date=data.get("date") or date.today(),
        balance=data.get("balance"),
        source=_safe_source(data.get("source")),
        fingerprint=_compute_transaction_fingerprint(
            user.id,
            data.get("date") or date.today(),
            data["amount"],
            data["type"],
            raw_title,
        ),
        is_recurring=data.get("is_recurring") or False,
        account_type=data.get("account_type"),
    )

    db.add(tx)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(tx)
    logger.info(f"add_transaction created transaction id={tx.id} with amount={tx.amount} (type: {type(tx.amount).__name__})")
    _audit(
        db,
        request,
        action="transaction_created",
        resource_type="transaction",
        resource_id=str(tx.id),
        status_code=status.HTTP_201_CREATED,
        details={"amount": str(tx.amount), "type": tx.type},
        user=user,
    )

    return success_response(
        request,
        {"id": tx.id, "uid": tx.uid},
        message="Transaction saved successfully",
        http_status=status.HTTP_201_CREATED,
    )


@router.get("/transactions", responses={500: {"model": dict}, 200: {"model": dict}})
def get_transaction_history(
    request: Request,
    limit: int = 50,
    cursor: str | None = None,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cursor-based paginated transaction list. cursor is the last transaction id (encoded as str)."""
    if limit < 1 or limit > 200:
        limit = 50

    try:
        query = db.query(Transaction).filter(Transaction.user_id == user.id)

        search = request.query_params.get("search")
        if search:
            query = query.filter(func.coalesce(Transaction.raw_description, Transaction.title).ilike(f"%{search}%"))

        # Cursor: decode cursor -> last seen ID, fetch only rows with ID < cursor (older)
        if cursor:
            try:
                last_id = int(cursor)
                query = query.filter(Transaction.id < last_id)
            except (ValueError, TypeError):
                pass

        transactions = query.order_by(Transaction.id.desc()).limit(limit + 1).all()

        has_more = len(transactions) > limit
        page = transactions[:limit]

        next_cursor = str(page[-1].id) if has_more and page else None

        data = [
            {
                "id": t.id,
                "uid": t.uid,
                "title": _display_title(t),
                "description": _display_title(t),
                "raw_description": t.raw_description,
                "amount": str(t.amount),
                "type": t.type,
                "category": t.category,
                "date": t.date.isoformat(),
                "balance": str(t.balance) if t.balance is not None else None,
                "source": t.source,
                "fingerprint": t.fingerprint,
                "is_recurring": t.is_recurring,
                "account_type": t.account_type,
                "status": t.status,

                "reconciliation_flags": t.reconciliation_flags,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in page
        ]
        return success_response(request, {"data": data, "next_cursor": next_cursor})
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("transactions_query_failed user_id=%s", user.id)
        error_text = str(exc).lower()
        details = None
        message = "Unable to fetch transactions"
        if any(token in error_text for token in ("no such column", "undefined column", "unknown column", "does not exist", "undefined table", "no such table")):
            message = "Transaction schema is out of date. Run finance-service migrations."
            details = {"hint": "Run `alembic upgrade head` in backend/finance-service"}
        return error_response(
            request,
            message,
            code=ErrorCode.INTERNAL_ERROR,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )
    except Exception:
        db.rollback()
        logger.exception("transactions_response_failed user_id=%s", user.id)
        return error_response(
            request,
            "Unable to fetch transactions",
            code=ErrorCode.INTERNAL_ERROR,
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class BulkDeletePayload(BaseModel):
    ids: List[int]


@router.delete("/transactions/bulk", responses={200: {"model": dict}})
def bulk_delete_transactions(
    request: Request,
    payload: BulkDeletePayload,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete multiple transactions in a single atomic database transaction."""
    if not payload.ids:
        return success_response(request, {"deleted_count": 0}, message="No transactions to delete")

    try:
        # Perform bulk delete within a single transaction, filtering by integer ID
        deleted_count = db.query(Transaction).filter(
            Transaction.user_id == user.id,
            Transaction.id.in_(payload.ids)
        ).delete(synchronize_session=False)
        
        db.commit()
        # Invalidate cache after bulk deletion
        clear_user_financial_cache(user.id)
        
        _audit(
            db, 
            request, 
            action="bulk_transactions_deleted", 
            resource_type="transaction", 
            details={"count": deleted_count, "ids": payload.ids},
            status_code=200, 
            user=user
        )
        return success_response(request, {"deleted_count": deleted_count}, message=f"Deleted {deleted_count} transactions")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"bulk_delete_error user_id={user.id}: {e}")
        return error_response(request, "Failed to delete transactions", code=ErrorCode.INTERNAL_ERROR, http_status=500)


@router.delete("/transactions/{uid}", responses={404: {"model": dict}, 200: {"model": dict}})
def delete_transaction(
    request: Request,
    uid: str,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    txn = db.query(Transaction).filter(Transaction.uid == uid, Transaction.user_id == user.id).first()
    if txn is None and uid.isdigit():
        txn = db.query(Transaction).filter(Transaction.id == int(uid), Transaction.user_id == user.id).first()
    
    if txn is None:
        return error_response(request, "Transaction not found", code=ErrorCode.NOT_FOUND, http_status=404)

    db.delete(txn)
    try:
        db.commit()
        clear_user_financial_cache(user.id)
    except SQLAlchemyError:
        db.rollback()
        raise
    _audit(db, request, action="transaction_deleted", resource_type="transaction", resource_id=uid, status_code=200, user=user)
    return success_response(request, {"id": uid, "deleted": True}, message="Transaction deleted")


@router.patch("/transactions/{uid}", responses={404: {"model": dict}, 400: {"model": dict}, 200: {"model": dict}})
@router.put("/transactions/{uid}", responses={404: {"model": dict}, 400: {"model": dict}, 200: {"model": dict}})
def update_transaction(
    request: Request,
    uid: str,
    payload: TransactionPayload,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    txn = db.query(Transaction).filter(Transaction.uid == uid, Transaction.user_id == user.id).first()
    if txn is None and uid.isdigit():
        txn = db.query(Transaction).filter(Transaction.id == int(uid), Transaction.user_id == user.id).first()

    if txn is None:
        return error_response(request, "Transaction not found", code=ErrorCode.NOT_FOUND, http_status=404)

    data = payload.model_dump(exclude_unset=True)
    if "type" in data and data["type"] is None:
        return error_response(request, "Transaction type must be 'income' or 'expense'", code=ErrorCode.INVALID_TRANSACTION_TYPE)
    if "amount" in data and data["amount"] is None:
        return error_response(request, "Amount must be > 0", code=ErrorCode.INVALID_AMOUNT)

    if "title" in data or "description" in data:
        raw_title = (data.get("title") or data.get("description") or _display_title(txn)).strip() or _display_title(txn)
        txn.title = normalize_title(raw_title)[:255] or txn.title
        txn.raw_description = raw_title[:255]
    if "amount" in data:
        txn.amount = data["amount"]
    if "type" in data:
        txn.type = data["type"]
    if "category" in data and data["category"]:
        cat = data["category"]
        txn.category = cat.value if hasattr(cat, "value") else str(cat)
    if "date" in data and data["date"]:
        txn.date = data["date"]
    if "balance" in data:
        txn.balance = data["balance"]
    if "source" in data and data["source"]:
        txn.source = _safe_source(data["source"])
    if "is_recurring" in data and data["is_recurring"] is not None:
        txn.is_recurring = data["is_recurring"]

    txn.fingerprint = _compute_transaction_fingerprint(
        txn.user_id,
        txn.date,
        txn.amount,
        txn.type,
        txn.raw_description or txn.title,
    )

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    _audit(db, request, action="transaction_updated", resource_type="transaction", resource_id=uid, status_code=200, user=user)
    clear_user_financial_cache(user.id)
    return success_response(request, {"id": txn.id, "title": _display_title(txn)}, message="Updated successfully")


@router.get("/wealth", responses={200: {"model": dict}})
@router.post("/wealth", responses={400: {"model": dict}, 201: {"model": dict}})
def wealth_list_create(
    request: Request,
    payload: WealthPayload | None = None,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if request.method == "GET":
        items = db.query(WealthItem).filter(WealthItem.user_id == user.id).order_by(WealthItem.created_at.desc()).all()
        # Aggregate Loans into Wealth View
        loans = db.query(Loan).filter(Loan.user_id == user.id).all()
        
        payload_out = [
            {
                "id": f"wealth_{item.id}",
                "uid": item.uid,
                "title": item.title,
                "amount": str(item.amount),
                "type": item.type,
                "category": item.category,
                "is_loan": False
            }
            for item in items
        ]
        
        for loan in loans:
            payload_out.append({
                "id": f"loan_{loan.id}",
                "uid": loan.uid,
                "title": f"{loan.loan_type.capitalize()} Loan",
                "amount": str(loan.remaining_balance),
                "type": "liability",
                "category": "Debt",
                "is_loan": True,
                "loan_details": {
                    "bank_name": loan.bank_name or "Unknown Bank",
                    "principal": str(loan.principal_amount),
                    "roi": str(loan.interest_rate),
                    "tenure": loan.tenure_months,
                    "emi": str(loan.emi_amount)
                }
            })
            
        return success_response(request, payload_out)

    if payload is None:
        return error_response(request, "Invalid wealth payload", code=ErrorCode.VALIDATION_ERROR)

    data = payload.model_dump(exclude_unset=True)
    if "amount" not in data or data["amount"] is None:
        return error_response(request, "Amount must be > 0", code=ErrorCode.INVALID_AMOUNT)
    if "type" not in data or data["type"] is None:
        return error_response(request, "Wealth type must be 'asset' or 'liability'", code=ErrorCode.INVALID_WEALTH_TYPE)

    title = (data.get("title") or data.get("name") or "Untitled").strip() or "Untitled"
    item = WealthItem(
        user_id=user.id,
        title=title,
        amount=data["amount"],
        type=data["type"],
        category=(data.get("category") or "General").strip() or "General",
    )
    db.add(item)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(item)
    _audit(db, request, action="wealth_created", resource_type="wealth", resource_id=item.uid, status_code=201, user=user)
    return success_response(
        request,
        {
            "id": item.id,
            "title": item.title,
            "amount": str(item.amount),
            "type": item.type,
            "category": item.category,
        },
        message="Item added successfully",
        http_status=status.HTTP_201_CREATED,
    )


@router.delete("/wealth/{uid}", responses={404: {"model": dict}, 200: {"model": dict}})
def delete_wealth_item(
    request: Request,
    uid: str,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(WealthItem).filter(WealthItem.uid == uid, WealthItem.user_id == user.id).first()
    if item is None:
        return error_response(request, "Item not found", code=ErrorCode.NOT_FOUND, http_status=404)

    db.delete(item)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    _audit(db, request, action="wealth_deleted", resource_type="wealth", resource_id=uid, status_code=200, user=user)
    return success_response(request, {"id": uid, "deleted": True}, message="Item deleted")


@router.patch("/wealth/{item_id}", responses={404: {"model": dict}, 400: {"model": dict}, 200: {"model": dict}})
@router.put("/wealth/{uid}", responses={404: {"model": dict}, 400: {"model": dict}, 200: {"model": dict}})
def update_wealth_item(
    request: Request,
    uid: str,
    payload: WealthPayload,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(WealthItem).filter(WealthItem.uid == uid, WealthItem.user_id == user.id).first()
    if item is None:
        return error_response(request, "Item not found", code=ErrorCode.NOT_FOUND, http_status=404)

    data = payload.model_dump(exclude_unset=True)
    if "type" in data and data["type"] is None:
        return error_response(request, "Wealth type must be 'asset' or 'liability'", code=ErrorCode.INVALID_WEALTH_TYPE)
    if "amount" in data and data["amount"] is None:
        return error_response(request, "Amount must be > 0", code=ErrorCode.INVALID_AMOUNT)

    if "title" in data or "name" in data:
        item.title = (data.get("title") or data.get("name") or item.title).strip() or item.title
    if "amount" in data:
        item.amount = data["amount"]
    if "type" in data:
        item.type = data["type"]
    if "category" in data and data["category"]:
        item.category = data["category"]

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    _audit(db, request, action="wealth_updated", resource_type="wealth", resource_id=uid, status_code=200, user=user)
    return success_response(
        request,
        {
            "id": item.id,
            "title": item.title,
            "amount": str(item.amount),
            "type": item.type,
            "category": item.category,
        },
        message="Item updated",
    )


@router.get("/tax-profile/{uid}", responses={403: {"model": dict}, 200: {"model": dict}})
@router.post("/tax-profile/{uid}", responses={403: {"model": dict}, 200: {"model": dict}})
def manage_tax_profile(
    request: Request,
    uid: str,
    payload: TaxProfilePayload | None = None,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _enforce_ownership(user, uid)

    profile = db.query(TaxProfile).filter(TaxProfile.user_id == user.id).first()
    if profile is None:
        profile = TaxProfile(user_id=user.id)
        db.add(profile)
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise
        db.refresh(profile)

    if request.method == "POST" and payload is not None:
        data = payload.model_dump(exclude_unset=True)
        mapping = {
            "isBusiness": "is_business",
            "annualRent": "annual_rent",
            "annualEPF": "annual_epf",
            "npsContribution": "nps_contribution",
            "healthInsuranceSelf": "health_insurance_self",
            "healthInsuranceParents": "health_insurance_parents",
            "homeLoanInterest": "home_loan_interest",
            "educationLoanInterest": "education_loan_interest",
            "parentsAreSenior": "parents_are_senior",
            "age": "age",
            "isMetro": "is_metro",
            "isPresumptive": "is_presumptive",
            "isNRI": "is_nri",
            "foreignAssets": "foreign_assets",
        }
        for key, attr in mapping.items():
            if key in data:
                setattr(profile, attr, data[key])
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise
        _audit(db, request, action="tax_profile_updated", resource_type="tax_profile", resource_id=str(user.id), status_code=200, user=user)

    payload_out = {
        "isBusiness": bool(profile.is_business),
        "annualRent": str(profile.annual_rent),
        "annualEPF": str(profile.annual_epf),
        "npsContribution": str(profile.nps_contribution),
        "healthInsuranceSelf": str(profile.health_insurance_self),
        "healthInsuranceParents": str(profile.health_insurance_parents),
        "homeLoanInterest": str(profile.home_loan_interest),
        "educationLoanInterest": str(profile.education_loan_interest),
    }
    return success_response(request, payload_out, message="Tax profile" if request.method == "GET" else "Tax profile updated")


@router.get("/itr-data/{uid}", responses={403: {"model": dict}, 200: {"model": dict}})
@router.post("/itr-data/{uid}", responses={403: {"model": dict}, 400: {"model": dict}, 200: {"model": dict}})
def itr_data_handler(
    request: Request,
    uid: str,
    payload: ITRPayload | None = None,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _enforce_ownership(user, uid)

    record = db.query(ITRData).filter(ITRData.user_id == user.id).first()
    if record is None:
        record = ITRData(user_id=user.id)
        db.add(record)
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise
        db.refresh(record)

    if request.method == "POST" and payload is not None:
        data = payload.model_dump(exclude_unset=True)
        if "tax_regime" in data and data["tax_regime"] is None:
            return error_response(request, "tax_regime must be 'new' or 'old'", code=ErrorCode.INVALID_TAX_REGIME)
        for key in ("income_data", "deductions_data", "filing_details", "tax_regime"):
            if key in data:
                setattr(record, key, data[key])
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise
        _audit(db, request, action="itr_updated", resource_type="itr", resource_id=str(user.id), status_code=200, user=user)
        return success_response(request, {"saved": True}, message="ITR data updated")

    return success_response(
        request,
        {
            "income_data": record.income_data,
            "deductions_data": record.deductions_data,
            "filing_details": record.filing_details,
            "tax_regime": record.tax_regime,
        },
    )



@router.get("/credit-cards")
def list_credit_cards(
    request: Request,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    cards = db.query(CreditCard).filter(CreditCard.user_id == user.id).all()
    for c in cards:
        c.card_holder_name = security_crypto.decrypt_string(c.card_holder_name)
    return success_response(request, [CreditCardOut.model_validate(c).model_dump(by_alias=True) for c in cards])


@router.post("/credit-cards")
def create_credit_card(
    request: Request,
    payload: CreditCardPayload,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    card = CreditCard(
        user_id=user.id,
        bank_name=payload.bank_name,
        card_holder_name=security_crypto.encrypt_string(payload.card_holder_name),
        last_four_digits=payload.last_four_digits,
        credit_limit=payload.credit_limit,
        billing_cycle=payload.billing_cycle,
        due_day=payload.due_day,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    
    # Decrypt for response
    card.card_holder_name = security_crypto.decrypt_string(card.card_holder_name)
    return success_response(request, CreditCardOut.model_validate(card).model_dump(by_alias=True), message="Credit card created")


@router.put("/credit-cards/{uid}")
def update_credit_card(
    request: Request,
    uid: str,
    payload: CreditCardPayload,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    card = db.query(CreditCard).filter(CreditCard.uid == uid, CreditCard.user_id == user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    card.bank_name = payload.bank_name
    card.card_holder_name = security_crypto.encrypt_string(payload.card_holder_name)
    card.last_four_digits = payload.last_four_digits
    card.credit_limit = payload.credit_limit
    card.billing_cycle = payload.billing_cycle
    card.due_day = payload.due_day

    db.commit()
    db.refresh(card)
    card.card_holder_name = security_crypto.decrypt_string(card.card_holder_name)
    return success_response(request, CreditCardOut.model_validate(card).model_dump(by_alias=True), message="Credit card updated")


@router.delete("/credit-cards/{uid}")
def delete_credit_card(
    request: Request,
    uid: str,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    card = db.query(CreditCard).filter(CreditCard.uid == uid, CreditCard.user_id == user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    db.delete(card)
    db.commit()
    return success_response(request, {"id": uid, "deleted": True}, message="Credit card deleted")


@router.get("/debit-cards")
def list_debit_cards(
    request: Request,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    cards = db.query(DebitCard).filter(DebitCard.user_id == user.id).all()
    for c in cards:
        c.card_holder_name = security_crypto.decrypt_string(c.card_holder_name)
    return success_response(request, [DebitCardOut.model_validate(c).model_dump(by_alias=True) for c in cards])


@router.post("/debit-cards")
def create_debit_card(
    request: Request,
    payload: DebitCardPayload,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    card = DebitCard(
        user_id=user.id,
        bank_name=payload.bank_name,
        last_four_digits=payload.last_four_digits,
        card_holder_name=security_crypto.encrypt_string(payload.card_holder_name),
        expiry_date=payload.expiry_date,
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    card.card_holder_name = security_crypto.decrypt_string(card.card_holder_name)
    return success_response(request, DebitCardOut.model_validate(card).model_dump(by_alias=True), message="Debit card created")


@router.put("/debit-cards/{uid}")
def update_debit_card(
    request: Request,
    uid: str,
    payload: DebitCardPayload,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    card = db.query(DebitCard).filter(DebitCard.uid == uid, DebitCard.user_id == user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    card.bank_name = payload.bank_name
    card.last_four_digits = payload.last_four_digits
    card.card_holder_name = security_crypto.encrypt_string(payload.card_holder_name)
    card.expiry_date = payload.expiry_date

    db.commit()
    db.refresh(card)
    card.card_holder_name = security_crypto.decrypt_string(card.card_holder_name)
    return success_response(request, DebitCardOut.model_validate(card).model_dump(by_alias=True), message="Debit card updated")


@router.delete("/debit-cards/{uid}")
def delete_debit_card(
    request: Request,
    uid: str,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    card = db.query(DebitCard).filter(DebitCard.uid == uid, DebitCard.user_id == user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    db.delete(card)
    db.commit()
    return success_response(request, {"id": uid, "deleted": True}, message="Debit card deleted")


@router.get("/loans")
def list_loans(
    request: Request,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    loans = db.query(Loan).filter(Loan.user_id == user.id).all()
    return success_response(request, [LoanOut.model_validate(l).model_dump() for l in loans])


@router.post("/loans")
def create_loan(
    request: Request,
    payload: LoanPayload,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    loan = Loan(
        user_id=user.id,
        loan_type=payload.loan_type,
        bank_name=payload.bank_name,
        principal_amount=payload.principal_amount,
        interest_rate=payload.interest_rate,
        tenure_months=payload.tenure_months,
        start_date=payload.start_date or date.today(),
        emi_amount=payload.emi_amount,
        remaining_balance=payload.remaining_balance,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return success_response(request, LoanOut.model_validate(loan).model_dump(), message="Loan created")


@router.delete("/loans/{uid}")
def delete_loan(
    request: Request,
    uid: str,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    loan = db.query(Loan).filter(Loan.uid == uid, Loan.user_id == user.id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    db.delete(loan)
    db.commit()
    return success_response(request, {"id": uid, "deleted": True}, message="Loan deleted")


@router.put("/loans/{uid}")
def update_loan(
    request: Request,
    uid: str,
    payload: LoanUpdatePayload,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    loan = db.query(Loan).filter(Loan.uid == uid, Loan.user_id == user.id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(loan, key, value)
    
    db.commit()
    db.refresh(loan)
    return success_response(request, LoanOut.model_validate(loan).model_dump(), message="Loan updated")


@router.get("/net-worth/history")
def get_net_worth_history(
    request: Request,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    snapshots = db.query(NetWorthSnapshot).filter(NetWorthSnapshot.user_id == user.id).order_by(NetWorthSnapshot.date.asc()).all()
    return success_response(request, [NetWorthSnapshotOut.model_validate(s).model_dump() for s in snapshots])


@router.post("/net-worth/snapshot")
def create_net_worth_snapshot(
    request: Request,
    payload: NetWorthSnapshotPayload,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    # Check if a snapshot for today already exists
    existing = db.query(NetWorthSnapshot).filter(
        NetWorthSnapshot.user_id == user.id,
        NetWorthSnapshot.date == payload.date
    ).first()
    
    if existing:
        existing.total_assets = payload.total_assets
        existing.total_liabilities = payload.total_liabilities
        existing.net_worth = payload.net_worth
        db.commit()
        db.refresh(existing)
        return success_response(request, NetWorthSnapshotOut.model_validate(existing).model_dump(), message="Snapshot updated")
    
    snapshot = NetWorthSnapshot(
        user_id=user.id,
        date=payload.date,
        total_assets=payload.total_assets,
        total_liabilities=payload.total_liabilities,
        net_worth=payload.net_worth,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return success_response(request, NetWorthSnapshotOut.model_validate(snapshot).model_dump(), message="Snapshot created")


@router.get("/statements/history")
def get_statement_history(
    request: Request,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    records = db.query(StatementRecord).filter(StatementRecord.user_id == user.id).order_by(StatementRecord.created_at.desc()).all()
    return success_response(request, [StatementRecordOut.model_validate(r).model_dump() for r in records])


@router.post("/statements/record")
def create_statement_record(
    request: Request,
    payload: StatementRecordPayload,
    db: Session = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    record = StatementRecord(
        user_id=user.id,
        filename=payload.filename,
        status=payload.status,
        account_type=payload.account_type,
        tx_count=payload.tx_count,
        reconciliation_score=payload.reconciliation_score,
        file_size=payload.file_size,
        file_hash=payload.file_hash,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return success_response(request, StatementRecordOut.model_validate(record).model_dump(), message="Statement record created")


@router.post("/parse-digital-pdf", responses={400: {"model": dict}, 422: {"model": dict}, 503: {"model": dict}, 200: {"model": dict}})
async def parse_digital_pdf_route(
    request: Request,
    file: UploadFile = File(...),
    account_type: str | None = None,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),

):
    if file is None:
        return error_response(request, "Missing statement file upload", code=ErrorCode.MISSING_FILE)

    validate_file_security(file)
    file.filename = sanitize_filename(file.filename or "statement.pdf")
    if not (file.content_type == "application/pdf" or file.filename.lower().endswith(".pdf")):
        return error_response(request, "Only PDF uploads are supported for statement parsing.", code=ErrorCode.BAD_REQUEST, http_status=400)

    content = await file.read()
    file_size = len(content)
    file_hash = hashlib.sha256(content).hexdigest()
    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or str(uuid.uuid4())

    record = StatementRecord(
        user_id=user.id,
        filename=file.filename,
        status="processing",
        file_size=file_size,
        file_hash=file_hash,
        account_type=account_type,
    )


    db.add(record)
    db.commit()

    try:
        parsed_result = parse_transactions(content)
        tx_list = parsed_result.get("transactions", [])
        meta = parsed_result.get("meta", {})
    except Exception as exc:
        import traceback
        record.status = "failed"
        db.commit()
        error_msg = str(exc)
        logger.error("Deterministic parser exception: %s\n%s", error_msg, traceback.format_exc())
        
        if "OCR_REQUIRED" in error_msg:
            return error_response(request, "This PDF appears to be a scanned image. Please provide a digital statement or use an OCR tool.", code=ErrorCode.OCR_REQUIRED, http_status=422)
            
        return error_response(request, error_msg, code=ErrorCode.PARSER_ERROR, http_status=422)

    transactions = []
    for idx, tx in enumerate(tx_list):
        amount = tx.get("amount") or 0.0
        row_hash = hashlib.sha256(
            f"{file_hash}|{idx}|{tx['date']}|{tx['description']}|{amount}|{tx['type']}".encode("utf-8")
        ).hexdigest()
        
        tx_uuid = uuid.uuid5(
            uuid.NAMESPACE_DNS,
            f"{tx['date']}|{tx['description'].lower()}|{amount:.2f}|{tx['type']}",
        )
        
        tx_type_safe = _safe_type(tx.get("type"))
        transactions.append(
            {
                "id": tx_uuid.hex,
                "date": tx.get("date"),
                "title": tx.get("description"),
                "description": tx.get("description"),
                "amount": amount,
                "type": tx_type_safe,
                "category": _infer_category(tx.get("description", ""), tx_type_safe),
                "source": "statement",
                "confidence": 100,
                "reconciliation_flags": [],
                "bank": "unknown",
                "balance": None,
                "is_valid": True,
                "statement_hash": file_hash,
                "statement_row_hash": row_hash,
                "account_type": account_type,
                "reference": None
            }
        )


    parsed_payload = {
        "status": "success",
        "request_id": request_id,
        "reconciliation_score": 1.0,
        "transactions": transactions,
        "statement_metadata": {
            "institution": "unknown",
            "account_id": "unknown",
            "currency": "INR",
            "period": {"from": None, "to": None}
        },
        "meta": {
            "count": len(transactions),
            "bank": "generic",
            "method": "digital_pdf",
            "avg_confidence": 1.0,
            "requires_review": False,
            "extraction_notes": None,
            "warnings": [],
            "errors": [],
            "parsing_time_seconds": meta.get("parsing_time_seconds", 0)
        },
    }

    persisted_count = _persist_parsed_transactions(db, user.id, transactions)
    summary = _build_financial_summary(db, user.id)

    parsed_payload["saved_count"] = persisted_count
    parsed_payload["financial_summary"] = summary

    try:
        record.status = "success"
        record.tx_count = len(transactions)
        record.reconciliation_score = Decimal("1.0")
        record.account_type = "generic"
        db.commit()
    except Exception as e:
        logger.error(f"Failed to update statement record: {e}")
        db.rollback()

    _audit(
        db,
        request,
        action="statement_parsed",
        resource_type="digital_pdf_parser",
        status_code=status.HTTP_200_OK,
        user=user,
        details={
            "parsed_transactions": len(transactions),
            "persisted_transactions": persisted_count,
            "file_size": file_size,
            "file_hash": file_hash,
        },
    )

    return success_response(request, parsed_payload, message="Digital PDF parsed", http_status=status.HTTP_200_OK)


# ─── Planner System ───────────────────────────────────────────────────────────

@router.get("/plans")
def get_user_plans(request: Request, user: UserContext = Depends(get_current_user), db: Session = Depends(get_db)):
    """Fetch all financial plans for the authenticated user."""
    plans = db.query(FinancePlan).filter(FinancePlan.user_id == user.id).all()
    data = [
        {
            "id": p.id,
            "uid": p.uid,
            "title": p.title,
            "source": p.source,
            "target_amount": float(p.target_amount),
            "current_saved": float(p.current_saved),
            "deadline": p.deadline.isoformat(),
            "monthly_saving": float(p.monthly_saving),
            "daily_saving": float(p.daily_saving),
            "loan_id": p.loan_id,
            "status": p.status,
            "reasoning": p.reasoning,
        }
        for p in plans
    ]
    return success_response(request, data)

@router.post("/plans")
def create_user_plan(request: Request, payload: dict, user: UserContext = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new plan manually from the frontend."""
    from datetime import datetime
    
    try:
        deadline = datetime.fromisoformat(payload["deadline"].replace("Z", "+00:00")).date()
    except Exception:
        from datetime import date
        deadline = date.today()

    plan = FinancePlan(
        user_id=user.id,
        title=payload["title"],
        source=payload.get("source", "manual"),
        target_amount=payload["target_amount"],
        monthly_saving=payload["monthly_saving"],
        daily_saving=float(payload["monthly_saving"]) / 30,
        loan_id=payload.get("loan_id"),
        deadline=deadline,
        status="on_track",
    )
    db.add(plan)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(plan)
    _audit(db, request, action="plan_created", resource_type="finance_plan", resource_id=str(plan.id), status_code=201, user=user)
    return success_response(request, {"id": plan.id, "uid": plan.uid}, http_status=201)

@router.patch("/plans/{uid}")
def update_user_plan(request: Request, uid: str, payload: dict, user: UserContext = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update or adjust an existing plan."""
    plan = db.query(FinancePlan).filter(FinancePlan.uid == uid, FinancePlan.user_id == user.id).first()
    if not plan:
        return error_response(request, "Plan not found", code=ErrorCode.NOT_FOUND, http_status=404)
        
    if "monthly_saving" in payload:
        plan.monthly_saving = payload["monthly_saving"]
        plan.daily_saving = float(payload["monthly_saving"]) / 30
    if "status" in payload:
        plan.status = payload["status"]
    if "title" in payload:
        plan.title = payload["title"]
    if "loan_id" in payload:
        plan.loan_id = payload["loan_id"]

        
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    _audit(db, request, action="plan_updated", resource_type="finance_plan", resource_id=str(plan.id), status_code=200, user=user)
    return success_response(request, {"id": plan.id, "uid": plan.uid}, message="Plan updated")

@router.delete("/plans/{uid}")
def delete_user_plan(request: Request, uid: str, user: UserContext = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a financial plan."""
    plan = db.query(FinancePlan).filter(FinancePlan.uid == uid, FinancePlan.user_id == user.id).first()
    if not plan:
        return error_response(request, "Plan not found", code=ErrorCode.NOT_FOUND, http_status=404)
        
    plan_id = plan.id
    db.delete(plan)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
        
    _audit(db, request, action="plan_deleted", resource_type="finance_plan", resource_id=str(plan_id), status_code=200, user=user)
    return success_response(request, None, message="Plan deleted")
