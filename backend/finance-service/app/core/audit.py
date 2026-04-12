from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from fastapi import Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ApiAuditLog
from app.core.redis import get_identity_from_request

if TYPE_CHECKING:
    from app.core.security import UserContext

logger = logging.getLogger("finance.audit")


def record_alert(
    db: Session,
    type: str,
    severity: str,
    description: str,
    actor_identity: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Standardized security alerting for finance-service.
    """
    try:
        from app.models import SecurityAlert

        alert = SecurityAlert(
            type=type,
            severity=severity,
            description=description,
            actor_identity=actor_identity,
            details=details or {},
        )
        db.add(alert)
        db.commit()
    except Exception:
        logger.exception("failed_to_record_security_alert")
        db.rollback()


def record_audit(
    db: Session,
    request: Request,
    *,
    action: str,
    resource_type: str,
    status_code: int,
    resource_id: str = "",
    error_code: str = "",
    details: dict[str, Any] | None = None,
    user: UserContext | None = None,
) -> None:
    """
    Standardized audit logging for finance-service.
    Persists to finance_apiauditlog table.
    """
    try:
        identity = get_identity_from_request(request)
        entry = ApiAuditLog(
            user_id=user.id if user else None,
            request_id=getattr(request.state, "request_id", None)
            or request.headers.get("X-Request-ID")
            or str(uuid.uuid4()),
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id or ""),
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            error_code=error_code,
            ip_address=identity,
            details=details or {},
        )
        db.add(entry)
        db.commit()

        # Anomaly Detection: Internal action spikes
        if action.startswith("internal_"):
            threshold_time = datetime.utcnow() - timedelta(minutes=5)
            action_count = (
                db.query(func.count(ApiAuditLog.id))
                .filter(
                    ApiAuditLog.ip_address == identity,
                    ApiAuditLog.action.like("internal_%"),
                    ApiAuditLog.created_at >= threshold_time,
                )
                .scalar()
            )

            if action_count >= 20:
                record_alert(
                    db,
                    type="mass_data_access",
                    severity="high",
                    description=f"Mass internal action spike from {identity}",
                    actor_identity=identity,
                    details={"action_count": action_count, "last_action": action},
                )

        # Anomaly Detection: Parser failures
        if action == "parser_failed":
            threshold_time = datetime.utcnow() - timedelta(minutes=10)
            fail_count = (
                db.query(func.count(ApiAuditLog.id))
                .filter(
                    ApiAuditLog.action == "parser_failed",
                    ApiAuditLog.created_at >= threshold_time,
                )
                .scalar()
            )
            if fail_count >= 5:
                record_alert(
                    db,
                    type="parser_attacks",
                    severity="medium",
                    description="Multiple statement parser failures detected",
                    details={"fail_count": fail_count},
                )

    except Exception:
        logger.exception("failed_to_record_audit_log")
        db.rollback()
