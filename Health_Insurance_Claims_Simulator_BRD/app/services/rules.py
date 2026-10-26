"""
========================================================================================
FINITE STATE MACHINE (FSM), FRAUD DETECTION & ADMISSION VALIDATION RULES
========================================================================================
Project     : Health Insurance Claims Processing Simulator (BRD Benchmark)
Component   : Business Rules & Workflow Enforcement (`app/services/rules.py`)
========================================================================================
Description:
    Enforces the core operational logic of health insurance claim lifecycles:
    1. Finite State Machine (FSM): Validates legal transitions across draft -> submitted ->
       in_review -> more_info -> approved -> paid / rejected.
    2. Audit Event Sourcing: Appends immutable sequential events into `claim_history`.
    3. Duplicate Claim Detection: Identifies potential duplicate hospital bill submissions.
    4. Multi-Constraint Data Validation: Enforces hospital network empanelment, active policy
       windows, member coverage ownership, and admission date integrity.
========================================================================================
"""

import datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from app.extensions import db
from app.models import Claim, ClaimDocument, ClaimHistory, Hospital, Member, Policy, User
from app.services.calculator import get_remaining_cover

# --------------------------------------------------------------------------------------
# Finite State Machine (FSM) Lifecycle Transition Map
# --------------------------------------------------------------------------------------
# Enforces legal status progressions. A status cannot jump directly (e.g. draft -> paid).
VALID_TRANSITIONS = {
    "draft": ["submitted"],
    "submitted": ["in_review"],
    "in_review": ["more_info", "approved", "rejected"],
    "more_info": ["submitted"],
    "approved": ["paid"],
    "rejected": [],
    "paid": [],
}


def can_transition(from_status: str, to_status: str) -> bool:
    """
    Checks if a lifecycle transition between two claim states is legally permitted.

    Args:
        from_status (str): Current status of the claim (e.g. 'submitted').
        to_status (str): Target status to transition into (e.g. 'in_review').

    Returns:
        bool: True if allowed by VALID_TRANSITIONS, False otherwise.
    """
    allowed = VALID_TRANSITIONS.get(from_status, [])
    return to_status in allowed


def record_history_event(
    claim: Claim,
    from_status: Optional[str],
    to_status: str,
    actor_user_id: Optional[int],
    note: str,
    event_date: Optional[datetime.date] = None
) -> ClaimHistory:
    """
    Appends an immutable event log to `claim_history` with an auto-incremented sequence number.

    Implements event-sourcing principles required for regulatory compliance in health insurance:
    every action, note, and status change is permanently audited and cannot be deleted or mutated.

    Args:
        claim (Claim): The Claim entity being updated.
        from_status (Optional[str]): Previous lifecycle status.
        to_status (str): New lifecycle status.
        actor_user_id (Optional[int]): User ID of the actor performing the action.
        note (str): Decision explanation, query description, or audit remark.
        event_date (Optional[datetime.date]): Calendar date of event (defaults to today).

    Returns:
        ClaimHistory: The newly created history entry added to the active session.
    """
    # Count existing historical events for this claim to determine the next sequential index
    seq = (
        db.session.query(db.func.coalesce(db.func.max(ClaimHistory.sequence_no), 0))
        .filter(ClaimHistory.claim_id == claim.id)
        .scalar()
    ) + 1

    today = event_date or datetime.date.today()
    history = ClaimHistory(
        claim_id=claim.id,
        sequence_no=seq,
        from_status=from_status,
        to_status=to_status,
        actor_user_id=actor_user_id,
        note=note,
        timestamp=datetime.datetime.utcnow(),
        event_date=today,
    )
    db.session.add(history)
    return history


def check_potential_duplicates(
    member_id: int,
    hospital_id: int,
    admission_date: datetime.date,
    discharge_date: datetime.date,
    claim_type: str,
    exclude_claim_id: Optional[int] = None
) -> List[Claim]:
    """
    Scans the database for duplicate claims submitted for the same hospitalization event.

    Heuristic Rule:
        Identical patient member, treating hospital, admission date, discharge date,
        and claim type indicates a potential duplicate or double-billing event.
        Flags the claim with a visual warning banner for Claims Officer scrutiny
        without auto-rejecting (allowing legitimate split billing review).

    Args:
        member_id (int): Patient member ID.
        hospital_id (int): Treating hospital ID.
        admission_date (datetime.date): Hospitalization admission date.
        discharge_date (datetime.date): Discharge date.
        claim_type (str): 'cashless' or 'reimbursement'.
        exclude_claim_id (Optional[int]): Current claim ID being evaluated (avoids self-matching).

    Returns:
        List[Claim]: Any existing claims that match all 5 duplicate criteria.
    """
    query = Claim.query.filter(
        Claim.member_id == member_id,
        Claim.hospital_id == hospital_id,
        Claim.admission_date == admission_date,
        Claim.discharge_date == discharge_date,
        Claim.claim_type == claim_type,
    )
    if exclude_claim_id:
        query = query.filter(Claim.id != exclude_claim_id)

    return query.all()


def validate_claim_data(
    policy: Policy,
    member: Member,
    hospital: Hospital,
    user: User,
    claim_type: str,
    treatment_type: str,
    admission_date: datetime.date,
    discharge_date: datetime.date,
    requested_amount: Decimal,
    is_submission: bool = False
) -> Tuple[bool, List[str]]:
    """
    Performs comprehensive business rule validation prior to creating or submitting a claim.

    Rules Verified:
        1. Member Ownership: The patient member must belong to the selected policy.
        2. Amount Integrity: Requested bill must be strictly greater than ₹0.00.
        3. Chronological Consistency: Discharge date cannot precede admission date.
        4. Future Admission Rule: Admission date cannot be in the future upon submission.
        5. Active Coverage Period: Policy must be in 'active' status on admission date.
        6. Plan Treatment Compatibility: Treatment type must be covered under plan terms.
        7. Cashless Hospital Authorization: Cashless claims require network empanelment
           and submission by authorized hospital desk staff.
        8. Reimbursement Scope: Only the policyholder can submit reimbursement claims.

    Args:
        policy (Policy): Selected policy.
        member (Member): Covered member/patient.
        hospital (Hospital): Treating medical facility.
        user (User): Authenticated actor submitting the request.
        claim_type (str): 'cashless' or 'reimbursement'.
        treatment_type (str): 'inpatient', 'daycare', etc.
        admission_date (datetime.date): Hospital admission date.
        discharge_date (datetime.date): Hospital discharge date.
        requested_amount (Decimal): Total bill amount.
        is_submission (bool): True if submitting for review; False if saving draft.

    Returns:
        Tuple[bool, List[str]]:
            - valid (bool): True if all checks passed, False otherwise.
            - errors (List[str]): List of error messages for each failed validation rule.
    """
    errors: List[str] = []
    today = datetime.date.today()

    # Rule 1: Member-Policy Relationship Integrity
    if member.policy_id != policy.id:
        errors.append(f"Member '{member.display_name}' does not belong to Policy #{policy.id}.")

    # Rule 2: Positive Financial Amount Check
    if requested_amount <= Decimal("0.00"):
        errors.append("Requested amount must be greater than ₹0.")

    # Rule 3: Date Chronology Check
    if discharge_date < admission_date:
        errors.append("Discharge date cannot be earlier than admission date.")

    # Rule 4: Future Admission Restriction on Formal Submission
    if is_submission and admission_date > today:
        errors.append(
            f"Admission date ({admission_date}) is in the future. Cannot submit claim until admission has occurred."
        )

    # Rule 5: Policy Active Period Validation
    if not policy.is_active_on(admission_date):
        errors.append(
            f"Policy #{policy.id} was not active on admission date ({admission_date}). "
            f"Valid policy period: {policy.start_date} to {policy.end_date} (Status: {policy.status})."
        )

    # Rule 6: Plan Treatment Compatibility
    if not policy.plan.covers_treatment(treatment_type):
        errors.append(
            f"Treatment type '{treatment_type}' is not covered under plan '{policy.plan.name}'. "
            f"Covered types: {policy.plan.covered_treatment_types}."
        )

    # Rule 7: Cashless Empanelment & Hospital User Scoping
    if claim_type == "cashless":
        if not hospital.network_status:
            errors.append(f"Hospital '{hospital.name}' is not an empanelled network hospital for cashless claims.")
        if user.role != "hospital" or user.hospital_id != hospital.id:
            errors.append(f"Cashless claims must be submitted by the authorized desk of '{hospital.name}'.")

    # Rule 8: Reimbursement Policyholder Ownership Check
    if claim_type == "reimbursement":
        if user.role != "policyholder" or policy.holder_user_id != user.id:
            errors.append("Reimbursement claims can only be submitted by the policyholder.")

    return len(errors) == 0, errors
