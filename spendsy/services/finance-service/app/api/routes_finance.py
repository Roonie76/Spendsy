from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

import hashlib
import logging
import re
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.redis import enqueue_task, get_identity_from_request, record_event
from ..core.security import UserContext, get_current_user
from ..models import ApiAuditLog, ITRData, TaxProfile, Transaction, UserProfile, WealthItem
from ..schemas import (
    ITRPayload,
    TaxProfilePayload,
    TransactionCategory,
    TransactionPayload,
    UserProfilePayload,
    WealthPayload,
)
from ..services.parser_client import parse_statement
from ..utils.error_codes import ErrorCode
from ..utils.response import error_response, success_response

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


def _audit(
    db: Session,
    request: Request,
    *,
    action: str,
    resource_type: str,
    status_code: int,
    resource_id: str = "",
    error_code: str = "",
    details: dict | None = None,
    user: UserContext | None = None,
) -> None:
    try:
        entry = ApiAuditLog(
            user_id=user.id if user else None,
            request_id=getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or str(uuid.uuid4()),
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id or ""),
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            error_code=error_code,
            ip_address=get_identity_from_request(request),
            details=details or {},
        )
        db.add(entry)
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise
    except Exception:
        db.rollback()


def _safe_category(raw: str | None) -> str:
    value = str(raw or "other").strip().lower()
    if value not in {e.value for e in TransactionCategory}:
        return "other"
    return value


def _safe_type(raw: str | None) -> str:
    value = str(raw or "expense").strip().lower()
    return value if value in {"income", "expense"} else "expense"


def _safe_source(raw: str | None) -> str:
    value = str(raw or "manual").strip().lower()
    return value if value in {"manual", "statement"} else "manual"


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


def _enforce_ownership(user: UserContext, path_user_id: int) -> None:
    """Raise HTTP 403 immediately if URL user_id != token user_id."""
    if int(path_user_id) != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you may only access your own resources",
        )


@router.get("/health")
def health(request: Request):
    return success_response(request, {"service": "finance", "status": "ok"}, message="Finance service healthy")


@router.get("/ready")
def readiness(request: Request, db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        db_ok = True
    except Exception:
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


@router.get("/profile/{user_id}")
@router.post("/profile/{user_id}")
def profile_settings(
    request: Request,
    user_id: int,
    payload: UserProfilePayload | None = None,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # IDOR fix: strict 403 if URL doesn't match token
    _enforce_ownership(user, user_id)

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
        {"id": tx.id},
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
        if any(token in error_text for token in ("no such column", "undefined column", "unknown column")):
            message = "Transaction schema is out of date. Run finance-service migrations."
            details = {"hint": "Run `alembic upgrade head` in spendsy/services/finance-service"}
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


@router.delete("/transactions/{transaction_id}", responses={404: {"model": dict}, 200: {"model": dict}})
def delete_transaction(
    request: Request,
    transaction_id: int,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tx = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == user.id).first()
    if tx is None:
        return error_response(request, "Transaction not found", code=ErrorCode.NOT_FOUND, http_status=404)

    db.delete(tx)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    _audit(db, request, action="transaction_deleted", resource_type="transaction", resource_id=str(transaction_id), status_code=200, user=user)
    return success_response(request, {"id": transaction_id, "deleted": True}, message="Transaction deleted")


@router.patch("/transactions/{transaction_id}", responses={404: {"model": dict}, 400: {"model": dict}, 200: {"model": dict}})
@router.put("/transactions/{transaction_id}", responses={404: {"model": dict}, 400: {"model": dict}, 200: {"model": dict}})
def update_transaction(
    request: Request,
    transaction_id: int,
    payload: TransactionPayload,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tx = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.user_id == user.id).first()
    if tx is None:
        return error_response(request, "Transaction not found", code=ErrorCode.NOT_FOUND, http_status=404)

    data = payload.model_dump(exclude_unset=True)
    if "type" in data and data["type"] is None:
        return error_response(request, "Transaction type must be 'income' or 'expense'", code=ErrorCode.INVALID_TRANSACTION_TYPE)
    if "amount" in data and data["amount"] is None:
        return error_response(request, "Amount must be > 0", code=ErrorCode.INVALID_AMOUNT)

    if "title" in data or "description" in data:
        raw_title = (data.get("title") or data.get("description") or _display_title(tx)).strip() or _display_title(tx)
        tx.title = normalize_title(raw_title)[:255] or tx.title
        tx.raw_description = raw_title[:255]
    if "amount" in data:
        tx.amount = data["amount"]
    if "type" in data:
        tx.type = data["type"]
    if "category" in data and data["category"]:
        cat = data["category"]
        tx.category = cat.value if hasattr(cat, "value") else str(cat)
    if "date" in data and data["date"]:
        tx.date = data["date"]
    if "balance" in data:
        tx.balance = data["balance"]
    if "source" in data and data["source"]:
        tx.source = _safe_source(data["source"])
    if "is_recurring" in data and data["is_recurring"] is not None:
        tx.is_recurring = data["is_recurring"]

    tx.fingerprint = _compute_transaction_fingerprint(
        tx.user_id,
        tx.date,
        tx.amount,
        tx.type,
        tx.raw_description or tx.title,
    )

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    _audit(db, request, action="transaction_updated", resource_type="transaction", resource_id=str(transaction_id), status_code=200, user=user)
    return success_response(request, {"id": tx.id, "title": _display_title(tx)}, message="Updated successfully")


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
        payload_out = [
            {
                "id": item.id,
                "title": item.title,
                "amount": str(item.amount),
                "type": item.type,
                "category": item.category,
            }
            for item in items
        ]
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
    _audit(db, request, action="wealth_created", resource_type="wealth", resource_id=str(item.id), status_code=201, user=user)
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


@router.delete("/wealth/{item_id}", responses={404: {"model": dict}, 200: {"model": dict}})
def delete_wealth_item(
    request: Request,
    item_id: int,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(WealthItem).filter(WealthItem.id == item_id, WealthItem.user_id == user.id).first()
    if item is None:
        return error_response(request, "Item not found", code=ErrorCode.NOT_FOUND, http_status=404)

    db.delete(item)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    _audit(db, request, action="wealth_deleted", resource_type="wealth", resource_id=str(item_id), status_code=200, user=user)
    return success_response(request, {"id": item_id, "deleted": True}, message="Item deleted")


@router.patch("/wealth/{item_id}", responses={404: {"model": dict}, 400: {"model": dict}, 200: {"model": dict}})
@router.put("/wealth/{item_id}", responses={404: {"model": dict}, 400: {"model": dict}, 200: {"model": dict}})
def update_wealth_item(
    request: Request,
    item_id: int,
    payload: WealthPayload,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(WealthItem).filter(WealthItem.id == item_id, WealthItem.user_id == user.id).first()
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
    _audit(db, request, action="wealth_updated", resource_type="wealth", resource_id=str(item_id), status_code=200, user=user)
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


@router.get("/tax-profile/{user_id}", responses={403: {"model": dict}, 200: {"model": dict}})
@router.post("/tax-profile/{user_id}", responses={403: {"model": dict}, 200: {"model": dict}})
def manage_tax_profile(
    request: Request,
    user_id: int,
    payload: TaxProfilePayload | None = None,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _enforce_ownership(user, user_id)

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


@router.get("/itr-data/{user_id}", responses={403: {"model": dict}, 200: {"model": dict}})
@router.post("/itr-data/{user_id}", responses={403: {"model": dict}, 400: {"model": dict}, 200: {"model": dict}})
def itr_data_handler(
    request: Request,
    user_id: int,
    payload: ITRPayload | None = None,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _enforce_ownership(user, user_id)

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


@router.post("/parse-statement", responses={400: {"model": dict}, 503: {"model": dict}, 200: {"model": dict}})
def parse_statement_proxy(
    request: Request,
    file: UploadFile = File(...),
    preview_mode: bool = False,
    confirm_persist: bool = False,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file is None:
        return error_response(request, "Missing statement file upload", code=ErrorCode.MISSING_FILE)

    logger.info(f"parse_statement_proxy: file={file.filename}, size={file.size}, content_type={file.content_type}, user={user.id}")
    content = file.file.read()
    statement_hash = hashlib.sha256(content).hexdigest()
    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or str(uuid.uuid4())

    try:
        parsed = parse_statement(content, file.filename, file.content_type)
        logger.info(f"parse_statement_proxy: parser returned {len(parsed.get('transactions', []))} transactions")
    except Exception as exc:
        logger.error("parser_failed request_id=%s error=%s", request_id, str(exc))
        _audit(
            db,
            request,
            action="parser_failed",
            resource_type="statement_parser",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.PARSER_UNAVAILABLE,
            user=user,
        )
        return error_response(
            request,
            f"Statement parser failed: {str(exc)}",
            code=ErrorCode.PARSER_UNAVAILABLE,
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    transactions = []
    parsed_meta = parsed.get("meta", {})
    parsed_method = parsed_meta.get("method", "digital")
    parsed_bank = parsed_meta.get("bank", "generic")
    for idx, tx in enumerate(parsed.get("transactions", [])):
        balance_value = tx.get("balance")
        row_hash = hashlib.sha256(
            f"{statement_hash}|{idx}|{tx['date']}|{tx['description']}|{tx['amount']}|{tx['type']}|{balance_value}".encode("utf-8")
        ).hexdigest()
        tx_uuid = uuid.uuid5(
            uuid.NAMESPACE_DNS,
            f"{tx['date']}|{tx['description'].lower()}|{tx['amount']:.2f}|{tx['type']}",
        )
        transactions.append(
            {
                "id": tx_uuid.hex,
                "date": tx["date"],
                "description": tx["description"],
                "amount": float(tx["amount"]),
                "type": tx["type"],
                "category": _infer_category(tx.get("description", ""), str(tx.get("type", ""))),
                "source": tx.get("source", "statement"),
                "confidence": int(round(float(tx.get("confidence", 0.99 if parsed_method == "digital" else 0.8)) * 100)),
                "bank": parsed_bank,
                "balance": balance_value,
                "is_valid": tx.get("is_valid", True),
                "statement_hash": statement_hash,
                "statement_row_hash": row_hash,
            }
        )

    parsed_payload = {
        "status": parsed.get("status", "success"),
        "request_id": request_id,
        "reconciliation_score": float(parsed.get("reconciliation_score", 1.0)),
        "transactions": transactions,
        "meta": {
            "count": len(transactions),
            "bank": parsed_bank,
            "method": parsed_method,
            "avg_confidence": float(parsed_meta.get("avg_confidence", 0.99 if parsed_method == "digital" else 0.8)),
            "min_confidence": float(parsed_meta.get("min_confidence", 0.99 if parsed_method == "digital" else 0.8)),
            "requires_review": bool(parsed_meta.get("requires_review", False)),
            "checksum_verified": bool(parsed_meta.get("checksum_verified", True)),
            "warnings": [],
            "errors": [],
        },
    }

    review_required = bool(parsed_payload["meta"]["requires_review"])
    effective_preview_mode = preview_mode
    if review_required and not confirm_persist:
        effective_preview_mode = True
        parsed_payload["meta"]["warnings"].append(
            "OCR-derived transactions require review before saving. Re-submit with confirm_persist=true after verification."
        )

    persisted_count = 0 if effective_preview_mode else _persist_parsed_transactions(db, user.id, transactions)
    summary = _build_financial_summary(db, user.id)

    parsed_payload["saved_count"] = persisted_count
    parsed_payload["preview_mode"] = effective_preview_mode
    parsed_payload["financial_summary"] = summary

    _audit(
        db,
        request,
        action="statement_parsed",
        resource_type="statement_parser",
        status_code=status.HTTP_200_OK,
        details={
            "parsed_transactions": len(transactions),
            "persisted_transactions": persisted_count,
            "source": parsed_payload["meta"]["method"],
            "reconciliation_score": parsed_payload["reconciliation_score"],
            "preview_mode": effective_preview_mode,
            "requires_review": review_required,
            "confirm_persist": confirm_persist,
        },
        user=user,
    )

    try:
        enqueue_task("app.tasks.post_parse_notification", {"user_id": user.id, "count": len(transactions)})
    except Exception as exc:
        logger.error(
            "enqueue_task failed for post_parse_notification user_id=%s request_id=%s error=%s",
            user.id, request_id, str(exc),
        )
        # Non-fatal: notification is best-effort; continue returning parsed data.

    return success_response(request, parsed_payload, message="Statement parsed", http_status=status.HTTP_200_OK)
