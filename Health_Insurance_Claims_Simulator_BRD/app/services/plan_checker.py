"""
========================================================================================
AUTOMATED PLAN SATISFACTION GATEKEEPER & POLICY COMPLIANCE ENGINE
========================================================================================
Project     : Health Insurance Claims Processing Simulator (BRD Benchmark)
Component   : Policy Compliance Verification (`app/services/plan_checker.py`)
========================================================================================
Description:
    Evaluates whether an incoming claim meets the selected health insurance plan's
    specific contractual constraints (such as OPD/Dental exclusion rules, room rent caps,
    consumables riders, and annual sum insured limits).
    Determines whether a claim automatically advances to the Claims Officer Review Queue
    or remains in Draft with an audit warning.
========================================================================================
"""

from typing import Tuple, List
from app.models import Policy


def evaluate_plan_satisfaction(
    policy: Policy,
    claim_category: str,
    treatment_type: str,
    requested_amount: float,
    includes_consumables: bool
) -> Tuple[bool, str, str]:
    """
    Evaluates an incoming claim against the exact policy terms of the subscribed plan.

    Validation Rules:
        1. OPD / Dental Check:
           If category is 'opd' or 'dental', checks whether `plan.opd_dental_cover` is 'Yes'
           (e.g. Star Health Super Star or Aditya Birla Activ One). Rejects if plan excludes OPD.
        2. Treatment Type Check:
           Ensures treatment type ('inpatient', 'daycare', 'ayush') is listed in `plan.covered_treatment_types`.
        3. Consumables Advisory:
           Flags if non-medical consumables are included but plan only covers them via optional rider.
        4. Annual Sum Insured Ceiling:
           Ensures the requested bill does not exceed the annual sum insured limit of the plan.
        5. Policy Standards Notation:
           Appends policy metadata (Room rent cap, AYUSH coverage, Pre/Post days) for officer records.

    Args:
        policy (Policy): The Policy entity under which the claim is being filed.
        claim_category (str): Selected category ('inpatient', 'daycare', 'opd', 'dental', 'ayush').
        treatment_type (str): Medical treatment format ('inpatient', 'daycare', 'ayush').
        requested_amount (float): Total bill amount in INR.
        includes_consumables (bool): True if hospital bill includes non-medical consumables.

    Returns:
        Tuple[bool, str, str]:
            - is_satisfied (bool): True if all mandatory policy rules pass; False otherwise.
            - status (str): 'passed' (routes to Claims Officer queue) or 'failed_plan_check' (held in draft).
            - summary_text (str): Multiline diagnostic explanation of all verified checks.
    """
    plan = policy.plan
    notes = []
    failed = False

    # ----------------------------------------------------------------------------------
    # Rule 1: OPD / Dental Coverage Verification
    # ----------------------------------------------------------------------------------
    if claim_category in ("opd", "dental"):
        if "yes" in plan.opd_dental_cover.lower():
            notes.append(f"✓ OPD/Dental Check Passed: {plan.insurer} {plan.name} covers Outpatient & Dental care.")
        else:
            failed = True
            notes.append(
                f"✗ OPD/Dental Violation: {plan.insurer} {plan.name} explicitly excludes Outpatient/Dental claims ({plan.opd_dental_cover})."
            )

    # ----------------------------------------------------------------------------------
    # Rule 2: Treatment Type Compatibility Check
    # ----------------------------------------------------------------------------------
    if not plan.covers_treatment(treatment_type):
        failed = True
        notes.append(
            f"✗ Treatment Type Mismatch: '{treatment_type}' is not covered under {plan.name}. Allowed types: {plan.covered_treatment_types}."
        )
    else:
        notes.append(f"✓ Treatment Type Verified: '{treatment_type}' is an eligible treatment.")

    # ----------------------------------------------------------------------------------
    # Rule 3: Non-Medical Consumables Advisory
    # ----------------------------------------------------------------------------------
    if includes_consumables:
        if "included" in plan.consumables_cover.lower() and "add-on" not in plan.consumables_cover.lower():
            notes.append(f"✓ Consumables Check: Covered as a built-in feature under {plan.name} ({plan.consumables_cover}).")
        else:
            notes.append(f"⚠ Consumables Advisory: Non-medical consumables are {plan.consumables_cover}. May face non-payable deductions.")

    # ----------------------------------------------------------------------------------
    # Rule 4: Annual Limit Ceiling Check
    # ----------------------------------------------------------------------------------
    if float(requested_amount) > float(plan.annual_limit_inr):
        failed = True
        notes.append(
            f"✗ Annual Limit Exceeded: Bill amount (₹{requested_amount:,.2f}) exceeds the plan's annual base limit of ₹{float(plan.annual_limit_inr):,.2f}."
        )
    else:
        notes.append(f"✓ Sum Insured Limit Check: Requested amount is within the ₹{float(plan.annual_limit_inr):,.2f} threshold.")

    # ----------------------------------------------------------------------------------
    # Rule 5: Summary of Policy Standards
    # ----------------------------------------------------------------------------------
    notes.append(
        f"ℹ Policy Standards: Room Rent = {plan.room_rent_limit} | AYUSH = {plan.ayush_cover} | Pre/Post = {plan.pre_hospitalization_days}/{plan.post_hospitalization_days} days."
    )

    status = "passed" if not failed else "failed_plan_check"
    summary_text = "\n".join(notes)
    return (not failed), status, summary_text
