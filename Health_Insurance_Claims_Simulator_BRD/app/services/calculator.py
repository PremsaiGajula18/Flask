"""
========================================================================================
FINANCIAL ADJUDICATION CALCULATOR & DEDUCTION ENGINE
========================================================================================
Project     : Health Insurance Claims Processing Simulator (BRD Benchmark)
Component   : Pure Business Logic Layer (`app/services/calculator.py`)
========================================================================================
Description:
    Implements exact mathematical calculations for health insurance claims adjudication
    using Python's `decimal.Decimal` with `ROUND_HALF_UP` rounding.
    Guarantees zero floating-point penny discrepancies across:
    - Annual remaining coverage tracking
    - Per-claim deductible application
    - Patient copayment deductions
    - Non-medical / inadmissible expense disallowances
========================================================================================
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from sqlalchemy import func

from app.extensions import db
from app.models import Claim, Policy, Settlement


def get_prior_paid_payouts(policy_id: int, exclude_claim_id: Optional[int] = None) -> Decimal:
    """
    Calculates the cumulative sum of all prior settled payouts under a specific policy.

    Queries the `settlements` table for all claims belonging to the policy in 'paid' status.
    Optionally excludes a specific claim ID when performing re-adjudication calculations.

    Args:
        policy_id (int): Primary key ID of the Policy.
        exclude_claim_id (Optional[int]): Claim ID to exclude from sum (default None).

    Returns:
        Decimal: Total rupee amount paid out to date (e.g. Decimal('45000.00')).
    """
    query = (
        db.session.query(func.coalesce(func.sum(Settlement.amount_inr), Decimal("0.00")))
        .join(Claim, Settlement.claim_id == Claim.id)
        .filter(Claim.policy_id == policy_id, Claim.status == "paid")
    )
    if exclude_claim_id:
        query = query.filter(Claim.id != exclude_claim_id)

    total = query.scalar()
    return Decimal(str(total or "0.00"))


def get_remaining_cover(policy: Policy, exclude_claim_id: Optional[int] = None) -> Decimal:
    """
    Computes the remaining sum insured coverage available for new claims under a policy.

    Formula:
        Remaining Cover = max(₹0.00, Plan Annual Limit - Prior Paid Payouts)

    Args:
        policy (Policy): The Policy model instance.
        exclude_claim_id (Optional[int]): Optional claim ID to exclude from prior payouts.

    Returns:
        Decimal: Available balance in Rupees, guaranteed never to be negative.
    """
    annual_limit = Decimal(str(policy.plan.annual_limit_inr))
    prior_paid = get_prior_paid_payouts(policy.id, exclude_claim_id=exclude_claim_id)
    remaining = annual_limit - prior_paid
    return max(Decimal("0.00"), remaining)


def calculate_payout(
    eligible_amount: Decimal,
    deductible: Decimal,
    copay_percent: Decimal
) -> Decimal:
    """
    Calculates the net insurer payout based on standard health insurance BRD rules.

    Step-by-step logic:
        1. Base Amount = eligible_amount - min(eligible_amount, deductible)
        2. Insurer Factor = 1.00 - (copay_percent / 100.00)
        3. Net Payout = round(Base Amount * Insurer Factor, 2 decimal places)

    Uses strict Decimal arithmetic with ROUND_HALF_UP rounding.

    Args:
        eligible_amount (Decimal): Medical expense assessed as eligible after exclusions.
        deductible (Decimal): Per-claim policy deductible in INR.
        copay_percent (Decimal): Patient co-payment percentage (e.g. 10.00%).

    Returns:
        Decimal: The exact amount the insurer pays out.
    """
    eligible = Decimal(str(eligible_amount))
    ded = Decimal(str(deductible))
    copay = Decimal(str(copay_percent))

    # Base amount after absorbing the per-claim deductible
    min_deductible = min(eligible, ded)
    base_amount = eligible - min_deductible

    # Compute insurer liability factor after patient co-pay
    factor = Decimal("1.00") - (copay / Decimal("100.00"))
    raw_payout = base_amount * factor

    # Quantize to exact 2 decimal places (rupees and paise)
    payout = raw_payout.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return payout


def get_calculation_breakdown(
    requested_amount: Decimal,
    eligible_amount: Decimal,
    deductible: Decimal,
    copay_percent: Decimal
) -> dict:
    """
    Generates a transparent, detailed deduction breakdown dictionary for the Claims Officer review.

    Computes:
        - requested_amount: Original bill amount submitted by hospital or patient
        - eligible_amount: Amount deemed admissible by the claims officer
        - disallowed_amount: Inadmissible medical/non-medical charges (requested - eligible)
        - deductible_applied: Per-claim deductible absorbed by the patient
        - copay_share: Patient co-pay out-of-pocket share
        - simulated_payout: Net insurer payout amount

    Args:
        requested_amount (Decimal): Total hospital bill requested.
        eligible_amount (Decimal): Admissible treatment charges.
        deductible (Decimal): Policy deductible.
        copay_percent (Decimal): Co-pay percentage.

    Returns:
        dict: Key-value mapping of all financial components formatted for UI rendering.
    """
    req = Decimal(str(requested_amount))
    elig = Decimal(str(eligible_amount))
    ded = Decimal(str(deductible))
    copay = Decimal(str(copay_percent))

    # Inadmissible/non-medical deduction
    disallowed = max(Decimal("0.00"), req - elig)

    # Deductible applied
    min_ded = min(elig, ded)
    base_after_ded = elig - min_ded

    # Co-pay calculation
    copay_factor = copay / Decimal("100.00")
    copay_share = (base_after_ded * copay_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Net insurer payout
    payout = (base_after_ded - copay_share).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "requested_amount": req,
        "eligible_amount": elig,
        "disallowed_amount": disallowed,
        "deductible_applied": min_ded,
        "copay_percent": copay,
        "copay_share": copay_share,
        "simulated_payout": payout,
    }
