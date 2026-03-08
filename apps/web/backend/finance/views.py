from __future__ import annotations

import logging
import os
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation


from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import connection
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated

from .api_contract import error_response, request_id_from_request, success_response
from .error_codes import ErrorCode
from .integrated_parser import IntegratedParser
from .models import ApiAuditLog, ITRData, TaxProfile, Transaction, UserProfile, WealthItem
from .security import client_ip, is_rate_limited
from .serializers import (
    ITRDataSerializer,
    TaxProfileSerializer,
    TransactionWriteSerializer,
    UserProfileUpdateSerializer,
    WealthItemWriteSerializer,
)

logger = logging.getLogger(__name__)

AUTH_RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "300"))
AUTH_RATE_LIMIT_LOGIN = int(os.getenv("AUTH_RATE_LIMIT_LOGIN", "10"))
AUTH_RATE_LIMIT_REGISTER = int(os.getenv("AUTH_RATE_LIMIT_REGISTER", "5"))

_integrated_parser = IntegratedParser()


def _audit(
    request,
    *,
    action: str,
    resource_type: str,
    status_code: int,
    resource_id: str = "",
    error_code: str = "",
    details: dict | None = None,
    user: User | None = None,
) -> None:
    try:
        ApiAuditLog.objects.create(
            user=user if user is not None else (request.user if getattr(request, "user", None) and request.user.is_authenticated else None),
            request_id=request_id_from_request(request),
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id or ""),
            method=request.method,
            path=request.path,
            status_code=status_code,
            error_code=error_code,
            ip_address=client_ip(request),
            details=details or {},
        )
    except Exception:
        logger.exception("Failed to write audit log action=%s path=%s", action, request.path)




def _safe_category(raw: str | None) -> str:
    value = str(raw or "other").strip().lower()
    return value or "other"


def _safe_type(raw: str | None) -> str:
    value = str(raw or "expense").strip().lower()
    return value if value in {"income", "expense"} else "expense"


def _safe_date(raw: str | None):
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw))
    except Exception:
        return None


def _build_financial_summary(user: User) -> dict:
    qs = Transaction.objects.filter(user=user)
    decimal_out = DecimalField(max_digits=14, decimal_places=2)
    agg = qs.aggregate(
        income=Coalesce(
            Sum("amount", filter=Q(type="income"), output_field=decimal_out),
            Value(0, output_field=decimal_out),
        ),
        expense=Coalesce(
            Sum("amount", filter=Q(type="expense"), output_field=decimal_out),
            Value(0, output_field=decimal_out),
        ),
    )

    income = float(agg.get("income") or 0)
    expense = float(agg.get("expense") or 0)

    return {
        "income": round(income, 2),
        "expense": round(expense, 2),
        "balance": round(income - expense, 2),
        "transaction_count": qs.count(),
    }


def _persist_parsed_transactions(user: User, parsed_transactions: list[dict]) -> int:
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

        duplicate_qs = Transaction.objects.filter(
            user=user,
            title__iexact=title,
            amount=amount,
            type=tx_type,
            category=tx_category,
            is_recurring=False,
        )
        if parsed_date is not None:
            duplicate_qs = duplicate_qs.filter(date=parsed_date)
        if duplicate_qs.exists():
            continue

        tx = Transaction(
            user=user,
            title=title,
            amount=amount,
            type=tx_type,
            category=tx_category,
            is_recurring=False,
        )
        if parsed_date is not None:
            tx.date = parsed_date
        tx.save()
        saved += 1
    return saved

def _forbidden_for_mismatched_path_user(request, user_id: int):
    # Backward-compatible route shape. Authorization scope is always request.user.
    if int(user_id) != request.user.id:
        _audit(
            request,
            action="path_user_ignored",
            resource_type="user",
            resource_id=str(user_id),
            status_code=status.HTTP_200_OK,
            details={"scoped_user_id": request.user.id},
        )
    return None


@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):
    ip = client_ip(request)
    if is_rate_limited("register", ip, AUTH_RATE_LIMIT_REGISTER, AUTH_RATE_LIMIT_WINDOW_SECONDS):
        _audit(
            request,
            action="register_rate_limited",
            resource_type="auth",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=ErrorCode.RATE_LIMITED,
        )
        return error_response(
            request,
            "Too many registration attempts. Please try again later.",
            code=ErrorCode.RATE_LIMITED,
            http_status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    username = (request.data.get("username") or "").strip()
    password = request.data.get("password")
    email = (request.data.get("email") or "").strip()

    if not username or not password:
        return error_response(request, "Username and password are required", code=ErrorCode.BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return error_response(request, "Username already exists", code=ErrorCode.USERNAME_CONFLICT)

    try:
        user = User.objects.create_user(username=username, password=password, email=email)
        UserProfile.objects.get_or_create(user=user)
        token, _ = Token.objects.get_or_create(user=user)
    except Exception:
        logger.exception("Registration failed for username=%s", username)
        _audit(
            request,
            action="register_failed",
            resource_type="auth",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.REGISTRATION_FAILED,
            details={"username": username},
        )
        return error_response(
            request,
            "Registration failed. Please try a different username/password.",
            code=ErrorCode.REGISTRATION_FAILED,
        )

    _audit(
        request,
        action="register_success",
        resource_type="auth",
        resource_id=str(user.id),
        status_code=status.HTTP_201_CREATED,
        user=user,
    )
    return success_response(
        request,
        {"id": user.id, "username": user.username, "token": token.key},
        message="User created successfully",
        http_status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_user(request):
    ip = client_ip(request)
    if is_rate_limited("login", ip, AUTH_RATE_LIMIT_LOGIN, AUTH_RATE_LIMIT_WINDOW_SECONDS):
        _audit(
            request,
            action="login_rate_limited",
            resource_type="auth",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=ErrorCode.RATE_LIMITED,
        )
        return error_response(
            request,
            "Too many login attempts. Please try again later.",
            code=ErrorCode.RATE_LIMITED,
            http_status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    identifier = (request.data.get("username") or "").strip()
    password = request.data.get("password")

    if not identifier or not password:
        return error_response(
            request,
            "Username/email and password are required",
            code=ErrorCode.BAD_REQUEST,
        )

    user = authenticate(username=identifier, password=password)
    if user is None:
        try:
            candidate = User.objects.get(email__iexact=identifier)
            user = authenticate(username=candidate.username, password=password)
        except User.DoesNotExist:
            user = None

    if user is None:
        _audit(
            request,
            action="login_failed",
            resource_type="auth",
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.AUTH_FAILED,
            details={"identifier": identifier},
        )
        return error_response(
            request,
            "Invalid username or password",
            code=ErrorCode.AUTH_FAILED,
            http_status=status.HTTP_401_UNAUTHORIZED,
        )

    token = Token.objects.get_or_create(user=user)[0]
    _audit(
        request,
        action="login_success",
        resource_type="auth",
        resource_id=str(user.id),
        status_code=status.HTTP_200_OK,
        user=user,
    )
    return success_response(
        request,
        {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "token": token.key,
        },
        message="Login successful",
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def profile_settings(request, user_id):
    mismatch = _forbidden_for_mismatched_path_user(request, user_id)
    if mismatch:
        return mismatch

    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        serializer = UserProfileUpdateSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(
                request,
                "Invalid profile payload",
                code=ErrorCode.INVALID_PROFILE_DATA,
                details=serializer.errors,
            )

        validated = serializer.validated_data
        for field in ("monthlyIncome", "monthlyBudget", "dailyBudget", "is_business"):
            if field in validated:
                setattr(profile, field, validated[field])
        if "email" in validated:
            user.email = (validated["email"] or "").strip()
            user.save(update_fields=["email"])
        profile.save()
        _audit(
            request,
            action="profile_updated",
            resource_type="profile",
            resource_id=str(user.id),
            status_code=status.HTTP_200_OK,
        )

    payload = {
        "username": user.username,
        "email": user.email,
        "monthlyIncome": float(profile.monthlyIncome),
        "monthlyBudget": float(profile.monthlyBudget),
        "dailyBudget": float(profile.dailyBudget),
        "is_business": profile.is_business,
    }
    return success_response(request, payload)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_transaction(request):
    provided_user_id = request.data.get("user_id")
    if provided_user_id is not None and str(provided_user_id) != str(request.user.id):
        _audit(
            request,
            action="payload_user_ignored",
            resource_type="transaction",
            status_code=status.HTTP_201_CREATED,
            details={"payload_user_id": str(provided_user_id), "scoped_user_id": request.user.id},
        )

    write_serializer = TransactionWriteSerializer(data=request.data, partial=True)
    if not write_serializer.is_valid():
        details = write_serializer.errors
        if "type" in details:
            return error_response(request, "Transaction type must be 'income' or 'expense'", code=ErrorCode.INVALID_TRANSACTION_TYPE)
        if "amount" in details:
            return error_response(request, "Invalid amount format", code=ErrorCode.INVALID_AMOUNT)
        return error_response(request, "Invalid transaction payload", code=ErrorCode.VALIDATION_ERROR, details=details)

    validated = write_serializer.validated_data
    if "amount" not in validated:
        return error_response(request, "Invalid amount format", code=ErrorCode.INVALID_AMOUNT)
    if "type" not in validated:
        return error_response(
            request,
            "Transaction type must be 'income' or 'expense'",
            code=ErrorCode.INVALID_TRANSACTION_TYPE,
        )

    create_kwargs = {
        "user": request.user,
        "title": validated.get("title", "Untitled Transaction"),
        "amount": validated["amount"],
        "type": validated["type"],
        "category": validated.get("category", "other"),
        "is_recurring": validated.get("is_recurring", False),
    }
    if "date" in validated:
        create_kwargs["date"] = validated["date"]

    transaction = Transaction.objects.create(**create_kwargs)
    _audit(
        request,
        action="transaction_created",
        resource_type="transaction",
        resource_id=str(transaction.id),
        status_code=status.HTTP_201_CREATED,
        details={"amount": str(transaction.amount), "type": transaction.type},
    )

    return success_response(
        request,
        {"id": transaction.id},
        message="Transaction saved successfully",
        http_status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_transaction_history(request, user_id):
    mismatch = _forbidden_for_mismatched_path_user(request, user_id)
    if mismatch:
        return mismatch

    queryset = Transaction.objects.filter(user=request.user)
    search = request.query_params.get("search")
    if search:
        queryset = queryset.filter(Q(title__icontains=search) | Q(amount__icontains=search))

    data = [
        {
            "id": t.id,
            "title": t.title,
            "amount": float(t.amount),
            "type": t.type,
            "category": t.category,
            "date": t.date.isoformat(),
            "is_recurring": t.is_recurring,
        }
        for t in queryset.order_by("-date", "-id")
    ]
    return success_response(request, data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_transaction(request, pk):
    try:
        transaction = Transaction.objects.get(pk=pk, user=request.user)
    except Transaction.DoesNotExist:
        return error_response(request, "Transaction not found", code=ErrorCode.NOT_FOUND, http_status=status.HTTP_404_NOT_FOUND)

    transaction.delete()
    _audit(
        request,
        action="transaction_deleted",
        resource_type="transaction",
        resource_id=str(pk),
        status_code=status.HTTP_200_OK,
    )
    return success_response(request, {"id": pk, "deleted": True}, message="Transaction deleted")


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_transaction(request, pk):
    try:
        transaction = Transaction.objects.get(pk=pk, user=request.user)
    except Transaction.DoesNotExist:
        return error_response(request, "Transaction not found", code=ErrorCode.NOT_FOUND, http_status=status.HTTP_404_NOT_FOUND)

    serializer = TransactionWriteSerializer(transaction, data=request.data, partial=True)
    if not serializer.is_valid():
        details = serializer.errors
        if "type" in details:
            return error_response(request, "Transaction type must be 'income' or 'expense'", code=ErrorCode.INVALID_TRANSACTION_TYPE)
        if "amount" in details:
            return error_response(request, "Invalid amount format", code=ErrorCode.INVALID_AMOUNT)
        return error_response(request, "Invalid transaction payload", code=ErrorCode.VALIDATION_ERROR, details=details)

    serializer.save()
    _audit(
        request,
        action="transaction_updated",
        resource_type="transaction",
        resource_id=str(pk),
        status_code=status.HTTP_200_OK,
    )
    return success_response(request, {"id": transaction.id, "title": transaction.title}, message="Updated successfully")


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def wealth_list_create(request, user_id):
    mismatch = _forbidden_for_mismatched_path_user(request, user_id)
    if mismatch:
        return mismatch

    if request.method == "GET":
        items = WealthItem.objects.filter(user=request.user).order_by("-created_at")
        payload = [
            {
                "id": item.id,
                "title": item.title,
                "amount": float(item.amount),
                "type": item.type,
                "category": item.category,
            }
            for item in items
        ]
        return success_response(request, payload)

    serializer = WealthItemWriteSerializer(data=request.data, partial=True)
    if not serializer.is_valid():
        details = serializer.errors
        if "type" in details:
            return error_response(request, "Wealth type must be 'asset' or 'liability'", code=ErrorCode.INVALID_WEALTH_TYPE)
        if "amount" in details:
            return error_response(request, "Invalid amount format", code=ErrorCode.INVALID_AMOUNT)
        return error_response(request, "Invalid wealth payload", code=ErrorCode.VALIDATION_ERROR, details=details)

    validated = serializer.validated_data
    if "amount" not in validated:
        return error_response(request, "Invalid amount format", code=ErrorCode.INVALID_AMOUNT)

    item = WealthItem.objects.create(
        user=request.user,
        title=validated.get("title", "Untitled"),
        amount=validated["amount"],
        type=validated.get("type", "asset"),
        category=validated.get("category", "General"),
    )
    _audit(
        request,
        action="wealth_created",
        resource_type="wealth",
        resource_id=str(item.id),
        status_code=status.HTTP_201_CREATED,
    )
    return success_response(
        request,
        {
            "id": item.id,
            "title": item.title,
            "amount": float(item.amount),
            "type": item.type,
            "category": item.category,
        },
        message="Item added successfully",
        http_status=status.HTTP_201_CREATED,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_wealth_item(request, item_id):
    try:
        item = WealthItem.objects.get(id=item_id, user=request.user)
    except WealthItem.DoesNotExist:
        return error_response(request, "Item not found", code=ErrorCode.NOT_FOUND, http_status=status.HTTP_404_NOT_FOUND)

    item.delete()
    _audit(
        request,
        action="wealth_deleted",
        resource_type="wealth",
        resource_id=str(item_id),
        status_code=status.HTTP_200_OK,
    )
    return success_response(request, {"id": item_id, "deleted": True}, message="Item deleted")


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_wealth_item(request, item_id):
    try:
        item = WealthItem.objects.get(id=item_id, user=request.user)
    except WealthItem.DoesNotExist:
        return error_response(request, "Item not found", code=ErrorCode.NOT_FOUND, http_status=status.HTTP_404_NOT_FOUND)

    serializer = WealthItemWriteSerializer(item, data=request.data, partial=True)
    if not serializer.is_valid():
        details = serializer.errors
        if "type" in details:
            return error_response(request, "Wealth type must be 'asset' or 'liability'", code=ErrorCode.INVALID_WEALTH_TYPE)
        if "amount" in details:
            return error_response(request, "Invalid amount format", code=ErrorCode.INVALID_AMOUNT)
        return error_response(request, "Invalid wealth payload", code=ErrorCode.VALIDATION_ERROR, details=details)

    serializer.save()
    _audit(
        request,
        action="wealth_updated",
        resource_type="wealth",
        resource_id=str(item_id),
        status_code=status.HTTP_200_OK,
    )
    return success_response(
        request,
        {
            "id": item.id,
            "title": item.title,
            "amount": float(item.amount),
            "type": item.type,
            "category": item.category,
        },
        message="Item updated",
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def manage_tax_profile(request, user_id):
    mismatch = _forbidden_for_mismatched_path_user(request, user_id)
    if mismatch:
        return mismatch

    profile, _ = TaxProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        serializer = TaxProfileSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response(request, "Invalid tax profile payload", code=ErrorCode.INVALID_TAX_PROFILE, details=serializer.errors)

        serializer.save()
        _audit(
            request,
            action="tax_profile_updated",
            resource_type="tax_profile",
            resource_id=str(request.user.id),
            status_code=status.HTTP_200_OK,
        )
        return success_response(request, serializer.data, message="Tax profile updated")

    serializer = TaxProfileSerializer(profile)
    return success_response(request, serializer.data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def itr_data_handler(request, user_id):
    mismatch = _forbidden_for_mismatched_path_user(request, user_id)
    if mismatch:
        return mismatch

    obj, _ = ITRData.objects.get_or_create(user=request.user)

    if request.method == "POST":
        serializer = ITRDataSerializer(obj, data=request.data, partial=True)
        if not serializer.is_valid():
            details = serializer.errors
            if "tax_regime" in details:
                return error_response(request, "tax_regime must be 'new' or 'old'", code=ErrorCode.INVALID_TAX_REGIME)
            return error_response(request, "Invalid ITR payload", code=ErrorCode.INVALID_ITR_PAYLOAD, details=details)
        serializer.save()
        _audit(
            request,
            action="itr_updated",
            resource_type="itr",
            resource_id=str(request.user.id),
            status_code=status.HTTP_200_OK,
        )
        return success_response(request, {"saved": True}, message="ITR data updated")

    return success_response(
        request,
        {
            "income_data": obj.income_data,
            "deductions_data": obj.deductions_data,
            "filing_details": obj.filing_details,
            "tax_regime": obj.tax_regime,
        },
    )




@api_view(["GET"])
@permission_classes([IsAuthenticated])
@throttle_classes([])
def financial_summary(request):
    summary = _build_financial_summary(request.user)
    return success_response(request, summary, message="Financial summary")


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    return success_response(request, {"service": "finance", "status": "ok"}, message="Finance service healthy")


@api_view(["GET"])
@permission_classes([AllowAny])
def readiness_check(request):
    parser_reachable = True
    db_ok = False

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            _ = cursor.fetchone()
        db_ok = True
    except Exception:
        logger.exception("DB readiness check failed")

    overall_ok = db_ok
    http_status = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE

    return success_response(
        request,
        {
            "service": "finance",
            "db_ok": db_ok,
            "parser_reachable": parser_reachable,
        },
        message="Ready" if overall_ok else "Not ready",
        http_status=http_status,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def parse_statement_proxy(request):
    upload = request.FILES.get("file")
    if upload is None:
        return error_response(request, "Missing PDF file upload", code=ErrorCode.MISSING_FILE)

    content = upload.read()
    request_id = request_id_from_request(request)
    preview_mode = str(request.data.get("preview_mode", "false")).strip().lower() in {"1", "true", "yes"}

    try:
        logger.info(
            "parser_stage=request_received request_id=%s filename=%s content_type=%s bytes=%d preview_mode=%s",
            request_id,
            upload.name,
            upload.content_type,
            len(content),
            preview_mode,
        )
        parsed = _integrated_parser.parse(content)
    except Exception:
        logger.exception("parser_stage=failed request_id=%s", request_id)
        _audit(
            request,
            action="parser_failed",
            resource_type="statement_parser",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.PARSER_UNAVAILABLE,
        )
        return error_response(
            request,
            "Statement parser failed. Please try again shortly.",
            code=ErrorCode.PARSER_UNAVAILABLE,
            http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    transactions: list[dict] = []
    for tx in parsed.transactions:
        tx_uuid = uuid.uuid5(
            uuid.NAMESPACE_DNS,
            f"{tx.date.isoformat()}|{tx.description.lower()}|{tx.amount:.2f}|{tx.type}",
        )
        transactions.append(
            {
                "id": tx_uuid.hex,
                "date": tx.date.isoformat(),
                "description": tx.description,
                "amount": float(tx.amount),
                "type": tx.type,
                "category": "other",
                "confidence": 95 if parsed.meta.get("method") == "digital" else 80,
                "bank": "Detected",
                "balance": tx.balance,
                "is_valid": tx.is_valid,
            }
        )

    parsed_payload = {
        "status": parsed.status,
        "request_id": request_id,
        "reconciliation_score": float(parsed.reconciliation_score),
        "transactions": transactions,
        "meta": {
            "count": len(transactions),
            "method": parsed.meta.get("method", "digital"),
            "checksum_verified": bool(parsed.meta.get("checksum_verified", True)),
            "warnings": [],
            "errors": [],
        },
    }

    persisted_count = 0 if preview_mode else _persist_parsed_transactions(request.user, transactions)
    summary = _build_financial_summary(request.user)

    parsed_payload["saved_count"] = persisted_count
    parsed_payload["financial_summary"] = summary

    _audit(
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
    )
    return success_response(request, parsed_payload, message="Statement parsed", http_status=status.HTTP_200_OK)
