"""
Tax API Routes — Server-side tax computation endpoints.

Provides:
  POST /tax/compute      — Full tax computation under both regimes
  GET  /tax/compute/{uid} — Compute from saved ITR data
  POST /tax/itr-form     — Determine the correct ITR form
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Any, Optional

from app.core.audit import record_audit as _audit
from app.core.database import get_db
from app.core.security import UserContext, get_current_user
from app.models import ITRData
from app.services.tax_engine import (
    TaxInput,
    build_tax_input_from_itr_data,
    compare_regimes,
    compute_advance_tax_schedule,
    compute_tax,
    determine_itr_form,
    generate_recommendations,
    run_audit_checks,
)
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/tax", tags=["tax"])
logger = logging.getLogger("finance.tax")


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class TaxComputeRequest(BaseModel):
    """Request payload for on-demand tax computation."""
    income_data: dict[str, Any] = Field(default_factory=dict)
    deductions_data: dict[str, Any] = Field(default_factory=dict)
    filing_details: dict[str, Any] = Field(default_factory=dict)
    profile: dict[str, Any] = Field(default_factory=dict)


class ITRFormRequest(BaseModel):
    """Request payload for ITR form determination."""
    income_data: dict[str, Any] = Field(default_factory=dict)
    profile: dict[str, Any] = Field(default_factory=dict)


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/compute")
def compute_tax_endpoint(
    request: Request,
    payload: TaxComputeRequest,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compute tax liability under both Old and New regimes.

    Accepts income, deductions, filing details, and profile data.
    Returns a full regime comparison with recommendations.
    """
    try:
        tax_input = build_tax_input_from_itr_data(
            payload.income_data,
            payload.deductions_data,
            payload.filing_details,
        )

        # Apply profile overrides
        profile = payload.profile
        if profile.get("age"):
            tax_input.age = int(profile["age"])
        if profile.get("isPresumptive"):
            tax_input.is_presumptive = True
        if profile.get("isMetro"):
            tax_input.is_metro = True
        if profile.get("parentsAreSenior"):
            tax_input.parents_are_senior = True
        if profile.get("isNRI"):
            tax_input.is_nri = True
        if profile.get("foreignAssets"):
            tax_input.has_foreign_assets = True
        if profile.get("isDirector"):
            tax_input.is_director = True
        if profile.get("hasUnlistedEquity"):
            tax_input.has_unlisted_equity = True
        if profile.get("entityType"):
            tax_input.entity_type = profile["entityType"]

        result = compare_regimes(tax_input)

        data = {
            "old_regime": asdict(result.old_regime),
            "new_regime": asdict(result.new_regime),
            "recommended_regime": result.recommended_regime,
            "savings": result.savings,
            "breakeven_deductions": result.breakeven_deductions,
            "itr_form": result.itr_form,
            "audit": {
                "errors": result.audit_errors,
                "warnings": result.audit_warnings,
            },
            "advance_tax_schedule": result.advance_tax_schedule,
            "recommendations": result.recommendations,
        }

        _audit(
            db, request,
            action="tax_computed",
            resource_type="tax_computation",
            resource_id=str(user.id),
            status_code=200,
            user=user,
        )

        return success_response(request, data, message="Tax computed successfully")

    except Exception as exc:
        logger.exception("Tax computation failed for user %s: %s", user.id, exc)
        return error_response(
            request,
            message="Tax computation failed",
            code="COMPUTATION_ERROR",
            http_status=500,
        )


@router.get("/compute/{uid}")
def compute_from_saved_data(
    request: Request,
    uid: str,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compute tax from the user's saved ITR data in the database.
    This uses the data previously saved via POST /itr-data/{uid}.
    """
    record = db.query(ITRData).filter(ITRData.user_id == user.id).first()
    if not record:
        return error_response(
            request,
            message="No ITR data found. Please save your data first.",
            code="NOT_FOUND",
            http_status=404,
        )

    try:
        tax_input = build_tax_input_from_itr_data(
            record.income_data,
            record.deductions_data,
            record.filing_details,
        )

        result = compare_regimes(tax_input)
        data = {
            "old_regime": asdict(result.old_regime),
            "new_regime": asdict(result.new_regime),
            "recommended_regime": result.recommended_regime,
            "savings": result.savings,
            "breakeven_deductions": result.breakeven_deductions,
            "itr_form": result.itr_form,
            "audit": {
                "errors": result.audit_errors,
                "warnings": result.audit_warnings,
            },
            "advance_tax_schedule": result.advance_tax_schedule,
            "recommendations": result.recommendations,
            "saved_regime": record.tax_regime,
        }

        _audit(
            db, request,
            action="tax_computed_from_saved",
            resource_type="tax_computation",
            resource_id=str(user.id),
            status_code=200,
            user=user,
        )

        return success_response(request, data, message="Tax computed from saved data")

    except Exception as exc:
        logger.exception("Tax computation from saved data failed: %s", exc)
        return error_response(
            request,
            message="Tax computation failed",
            code="COMPUTATION_ERROR",
            http_status=500,
        )


@router.post("/itr-form")
def get_itr_form(
    request: Request,
    payload: ITRFormRequest,
    user: UserContext = Depends(get_current_user),
):
    """Determine the appropriate ITR form based on income profile."""
    tax_input = build_tax_input_from_itr_data(payload.income_data, None, None)

    profile = payload.profile
    if profile.get("isPresumptive"):
        tax_input.is_presumptive = True
    if profile.get("foreignAssets"):
        tax_input.has_foreign_assets = True
    if profile.get("isDirector"):
        tax_input.is_director = True
    if profile.get("hasUnlistedEquity"):
        tax_input.has_unlisted_equity = True
    if profile.get("entityType"):
        tax_input.entity_type = profile["entityType"]

    itr_form = determine_itr_form(tax_input)
    return success_response(request, itr_form, message="ITR form determined")


@router.post("/audit")
def run_audit_endpoint(
    request: Request,
    payload: TaxComputeRequest,
    user: UserContext = Depends(get_current_user),
):
    """Run pre-filing audit checks on the provided data."""
    tax_input = build_tax_input_from_itr_data(
        payload.income_data,
        payload.deductions_data,
        payload.filing_details,
    )
    errors, warnings = run_audit_checks(tax_input)
    return success_response(
        request,
        {"errors": errors, "warnings": warnings, "error_count": len(errors), "warning_count": len(warnings)},
        message="Audit completed",
    )
