"""
Autofill mapper.

Takes extracted Form16Data / BrokerStatementData / BankStatementData
and maps them to the ITR-1 JSON schema used by ITRForm (itr-form-feature).

Schema shape:
  ITR.ITR1.PersonalInfo.*
  ITR.ITR1.FilingStatus.*
  ITR.ITR1.ITR1_IncomeDeductions.*
  ITR.ITR1.ITR1_IncomeDeductions.UsrDeductUndChapVIA.*
  ITR.ITR1.TDSonSalaries[0].*
  ITR.ITR1.BankAccountDtls.AddtnlBankDetails[0].*
"""
from __future__ import annotations

from app.core.schemas import BankStatementData, BrokerStatementData, Form16Data


def _set(d: dict, path: str, value) -> None:
    """Set a nested key in dict using dot-path notation, creating dicts as needed."""
    keys = path.split(".")
    node = d
    for key in keys[:-1]:
        node = node.setdefault(key, {})
    node[keys[-1]] = value


def form16_to_autofill(data: Form16Data) -> dict:
    """Map Form16Data → ITR-1 JSON schema shape for ITRForm initialData."""
    result: dict = {}

    # ── PersonalInfo ─────────────────────────────────────────────────────────
    if data.employee_name:
        # AssesseeName = { SurNameOrOrgName, FirstName, MiddleName }
        parts = data.employee_name.strip().split()
        _set(result, "ITR.ITR1.PersonalInfo.AssesseeName.FirstName", parts[0] if parts else "")
        if len(parts) > 2:
            _set(result, "ITR.ITR1.PersonalInfo.AssesseeName.MiddleName", " ".join(parts[1:-1]))
        if len(parts) > 1:
            _set(result, "ITR.ITR1.PersonalInfo.AssesseeName.SurNameOrOrgName", parts[-1])

    if data.employee_pan:
        _set(result, "ITR.ITR1.PersonalInfo.PAN", data.employee_pan.upper())

    # ── FilingStatus ──────────────────────────────────────────────────────────
    if data.employer_name:
        _set(result, "ITR.ITR1.FilingStatus.EmployerCategory", data.employer_name)

    # ── Income from Salary ────────────────────────────────────────────────────
    if data.gross_salary is not None:
        _set(result, "ITR.ITR1.ITR1_IncomeDeductions.GrossSalary", int(data.gross_salary))
    if data.hra_received is not None:
        # HRA goes into AllwncExemptUs10 > TotalAllwncExemptUs10
        _set(result, "ITR.ITR1.ITR1_IncomeDeductions.AllwncExemptUs10.TotalAllwncExemptUs10", int(data.hra_received))
    if data.perquisites is not None:
        # Perquisites contribute to gross; no direct field — absorbed in GrossSalary
        pass

    # ── Deductions under Chapter VI-A (user-entered, editable) ───────────────
    usr = {}
    if data.deduction_80c is not None:
        usr["Section80C"] = int(data.deduction_80c)
    if data.deduction_80d is not None:
        usr["Section80D"] = int(data.deduction_80d)
    if data.deduction_nps_80ccd is not None:
        usr["Section80CCD1B"] = int(data.deduction_nps_80ccd)
    if data.deduction_employer_nps is not None:
        usr["Section80CCD2"] = int(data.deduction_employer_nps)
    if usr:
        _set(result, "ITR.ITR1.ITR1_IncomeDeductions.UsrDeductUndChapVIA", usr)

    # ── TDS on Salaries ───────────────────────────────────────────────────────
    if data.tds_deducted is not None or data.employer_tan:
        tds_entry: dict = {}
        if data.employer_tan:
            tds_entry["TAN"] = data.employer_tan.upper()
        if data.employer_name:
            tds_entry["NameOfDeductor"] = data.employer_name
        if data.tds_deducted is not None:
            tds_entry["TotalTDSSal"] = int(data.tds_deducted)
            tds_entry["TDSDeducted"] = int(data.tds_deducted)
        if tds_entry:
            _set(result, "ITR.ITR1.TDSonSalaries", [tds_entry])

    # ── House Property (home loan interest → Schedule 24B) ────────────────────
    if data.home_loan_interest is not None:
        _set(result, "ITR.ITR1.ITR1_IncomeDeductions.InterestPayable", int(data.home_loan_interest))
        _set(result, "ITR.ITR1.ITR1_IncomeDeductions.ScheduleUs24B", int(data.home_loan_interest))

    return result


def broker_to_autofill(data: BrokerStatementData) -> dict:
    """Map BrokerStatementData → ITR-1 capital gains fields."""
    result: dict = {}

    # LTCG 112A (listed equity > 1yr)
    if data.ltcg_equity is not None:
        _set(result, "ITR.ITR1.ITR1_IncomeDeductions.LTCG112A", int(data.ltcg_equity))

    # STCG on equity goes into OthersInc > Description (no dedicated STCG field in ITR-1)
    # ITR-1 only supports salary + HP + other sources; STCG 111A needs ITR-2.
    # We surface STCG as a note in IncomeOthSrc if present.
    others = 0
    if data.stcg_equity is not None:
        others += int(data.stcg_equity)
    if data.stcg_debt is not None:
        others += int(data.stcg_debt)
    if data.ltcg_debt is not None:
        others += int(data.ltcg_debt)
    if others:
        _set(result, "ITR.ITR1.ITR1_IncomeDeductions.IncomeOthSrc", others)

    return result


def bank_to_autofill(data: BankStatementData) -> dict:
    """Map BankStatementData → interest income + bank account details."""
    result: dict = {}

    # ── Other Income (savings/FD interest → OthersInc) ───────────────────────
    interest_total = 0
    if data.savings_interest is not None:
        interest_total += int(data.savings_interest)
    if data.fd_interest is not None:
        interest_total += int(data.fd_interest)
    if interest_total:
        _set(result, "ITR.ITR1.ITR1_IncomeDeductions.IncomeOthSrc", interest_total)

    # ── Bank Account Details (for refund) ─────────────────────────────────────
    bank_entry: dict = {}
    if data.account_number_masked:
        bank_entry["BankAccountNo"] = data.account_number_masked
    if data.ifsc:
        bank_entry["IFSCCode"] = data.ifsc
    if data.bank_name:
        bank_entry["BankName"] = data.bank_name
    if data.account_type:
        # ITR-1 expects "SB" / "CA" / "CC"
        atype = data.account_type.upper()
        if "SAVING" in atype:
            atype = "SB"
        elif "CURRENT" in atype:
            atype = "CA"
        bank_entry["AccountType"] = atype
        bank_entry["UseForRefund"] = True
    if bank_entry:
        _set(result, "ITR.ITR1.BankAccountDtls.AddtnlBankDetails", [bank_entry])

    return result
