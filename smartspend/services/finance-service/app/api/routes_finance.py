from __future__ import annotations

import logging
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import func
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
        db.commit()
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


def _safe_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw))
    except Exception:
        return None


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
    for item in parsed_transactions:
        raw_amount = item.get("amount")
        try:
            amount = Decimal(str(raw_amount))
        except (InvalidOperation, TypeError):
            continue

        if amount <= 0:
            continue

        title = (item.get("description") or "Parsed Transaction").strip()[:255] or "Parsed Transaction"
        tx_type = _safe_type(item.get("type"))
        tx_category = _safe_category(item.get("category"))
        parsed_date = _safe_date(item.get("date"))

        query = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.title.ilike(title),
            Transaction.amount == amount,
            Transaction.type == tx_type,
            Transaction.category == tx_category,
            Transaction.is_recurring.is_(False),
        )
        if parsed_date is not None:
            query = query.filter(Transaction.date == parsed_date)
        if db.query(query.exists()).scalar():
            continue

        tx = Transaction(
            user_id=user_id,
            title=title,
            amount=amount,
            type=tx_type,
            category=tx_category,
            is_recurring=False,
            date=parsed_date or date.today(),
        )
        db.add(tx)
        saved += 1

    db.commit()
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
        db.commit()
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
        db.commit()
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


@router.post("/transactions")
def add_transaction(
    request: Request,
    payload: TransactionPayload,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = payload.model_dump(exclude_unset=True)
    if "amount" not in data or data["amount"] is None:
        return error_response(request, "Amount is required and must be > 0", code=ErrorCode.INVALID_AMOUNT)
    if "type" not in data or data["type"] is None:
        return error_response(request, "Transaction type must be 'income' or 'expense'", code=ErrorCode.INVALID_TRANSACTION_TYPE)

    title = (data.get("title") or data.get("description") or "Untitled Transaction").strip() or "Untitled Transaction"
    category = data.get("category")
    category_val = category.value if hasattr(category, "value") else (str(category) if category else "other")

    tx = Transaction(
        user_id=user.id,
        title=title,
        amount=data["amount"],
        type=data["type"],
        category=category_val,
        date=data.get("date") or date.today(),
        is_recurring=data.get("is_recurring") or False,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
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


@router.get("/transactions")
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

    query = db.query(Transaction).filter(Transaction.user_id == user.id)

    search = request.query_params.get("search")
    if search:
        query = query.filter(Transaction.title.ilike(f"%{search}%"))

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
            "title": t.title,
            "amount": str(t.amount),
            "type": t.type,
            "category": t.category,
            "date": t.date.isoformat(),
            "is_recurring": t.is_recurring,
        }
        for t in page
    ]
    return success_response(request, {"data": data, "next_cursor": next_cursor})


@router.delete("/transactions/{transaction_id}")
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
    db.commit()
    _audit(db, request, action="transaction_deleted", resource_type="transaction", resource_id=str(transaction_id), status_code=200, user=user)
    return success_response(request, {"id": transaction_id, "deleted": True}, message="Transaction deleted")


@router.patch("/transactions/{transaction_id}")
@router.put("/transactions/{transaction_id}")
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
        title = (data.get("title") or data.get("description") or tx.title).strip() or tx.title
        tx.title = title
    if "amount" in data:
        tx.amount = data["amount"]
    if "type" in data:
        tx.type = data["type"]
    if "category" in data and data["category"]:
        cat = data["category"]
        tx.category = cat.value if hasattr(cat, "value") else str(cat)
    if "date" in data and data["date"]:
        tx.date = data["date"]
    if "is_recurring" in data and data["is_recurring"] is not None:
        tx.is_recurring = data["is_recurring"]

    db.commit()
    _audit(db, request, action="transaction_updated", resource_type="transaction", resource_id=str(transaction_id), status_code=200, user=user)
    return success_response(request, {"id": tx.id, "title": tx.title}, message="Updated successfully")


@router.get("/wealth")
@router.post("/wealth")
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
    db.commit()
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


@router.delete("/wealth/{item_id}")
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
    db.commit()
    _audit(db, request, action="wealth_deleted", resource_type="wealth", resource_id=str(item_id), status_code=200, user=user)
    return success_response(request, {"id": item_id, "deleted": True}, message="Item deleted")


@router.patch("/wealth/{item_id}")
@router.put("/wealth/{item_id}")
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

    db.commit()
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


@router.get("/tax-profile/{user_id}")
@router.post("/tax-profile/{user_id}")
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
        db.commit()
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
        db.commit()
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


@router.get("/itr-data/{user_id}")
@router.post("/itr-data/{user_id}")
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
        db.commit()
        db.refresh(record)

    if request.method == "POST" and payload is not None:
        data = payload.model_dump(exclude_unset=True)
        if "tax_regime" in data and data["tax_regime"] is None:
            return error_response(request, "tax_regime must be 'new' or 'old'", code=ErrorCode.INVALID_TAX_REGIME)
        for key in ("income_data", "deductions_data", "filing_details", "tax_regime"):
            if key in data:
                setattr(record, key, data[key])
        db.commit()
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


@router.post("/parse-statement")
def parse_statement_proxy(
    request: Request,
    file: UploadFile = File(...),
    preview_mode: bool = False,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file is None:
        return error_response(request, "Missing PDF file upload", code=ErrorCode.MISSING_FILE)

    content = file.file.read()
    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or str(uuid.uuid4())

    try:
        parsed = parse_statement(content, file.filename)
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
            "Statement parser failed. Please try again shortly.",
            code=ErrorCode.PARSER_UNAVAILABLE,
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    transactions = []
    for tx in parsed.get("transactions", []):
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
                "category": "other",
                "confidence": 95 if parsed.get("meta", {}).get("method") == "digital" else 80,
                "bank": "Detected",
                "balance": tx.get("balance"),
                "is_valid": tx.get("is_valid", True),
            }
        )

    parsed_payload = {
        "status": parsed.get("status", "success"),
        "request_id": request_id,
        "reconciliation_score": float(parsed.get("reconciliation_score", 1.0)),
        "transactions": transactions,
        "meta": {
            "count": len(transactions),
            "method": parsed.get("meta", {}).get("method", "digital"),
            "checksum_verified": bool(parsed.get("meta", {}).get("checksum_verified", True)),
            "warnings": [],
            "errors": [],
        },
    }

    persisted_count = 0 if preview_mode else _persist_parsed_transactions(db, user.id, transactions)
    summary = _build_financial_summary(db, user.id)

    parsed_payload["saved_count"] = persisted_count
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
            "preview_mode": preview_mode,
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
