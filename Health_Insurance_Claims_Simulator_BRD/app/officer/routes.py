"""
========================================================================================
CLAIMS OFFICER ADJUDICATION & REVIEW QUEUE CONTROLLER
========================================================================================
Project     : Health Insurance Claims Processing Simulator (BRD Benchmark)
Component   : Claims Officer Controller (`app/officer/routes.py`)
========================================================================================
Description:
    Provides triage and decision workflows for insurance claims officers:
    - Review Queue: Displays unassigned and in-review claims across the portfolio.
    - Race-Condition Protected Assignment: Locks a submitted claim to an officer.
    - Information Request: Puts claim in 'more_info' status with query notes.
    - Formal Adjudication: Assesses admissible eligible amount, executes financial
      deduction math (deductible, co-pay), checks remaining sum insured, and approves/rejects.
========================================================================================
"""

import datetime
from decimal import Decimal
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.auth.decorators import get_current_user, role_required
from app.extensions import db
from app.models import Claim, ClaimDocument, ClaimHistory, User
from app.services.calculator import (
    calculate_payout,
    get_calculation_breakdown,
    get_remaining_cover,
)
from app.services.rules import check_potential_duplicates, record_history_event

# Officer Blueprint mounted at URL prefix /officer
officer_bp = Blueprint("officer", __name__, url_prefix="/officer")


@officer_bp.route("/queue")
@role_required("claims_officer", "admin")
def review_queue():
    """
    Claims Officer Adjudication Queue Route.

    Filters active claims across three operational view modes:
        - 'all'        : All claims currently in 'submitted', 'in_review', or 'more_info'.
        - 'mine'       : Claims explicitly assigned to the currently logged-in officer.
        - 'unassigned' : Freshly submitted claims awaiting triage and assignment.

    Returns:
        Rendered queue template with ordered claims and active filter metadata.
    """
    user = get_current_user()
    filter_mode = request.args.get("view", "all")  # 'all', 'mine', 'unassigned'

    query = Claim.query.filter(Claim.status.in_(["submitted", "in_review", "more_info"]))

    if filter_mode == "mine":
        query = query.filter(Claim.officer_user_id == user.id)
    elif filter_mode == "unassigned":
        query = query.filter(Claim.status == "submitted", Claim.officer_user_id == None)

    # Sort FIFO (oldest submitted claims first) to uphold Service Level Agreements (SLA)
    claims = query.order_by(Claim.created_at.asc()).all()

    return render_template(
        "officer/queue.html",
        claims=claims,
        user=user,
        filter_mode=filter_mode,
    )


@officer_bp.route("/claim/<int:claim_id>/assign", methods=["POST"])
@role_required("claims_officer", "admin")
def assign_claim(claim_id: int):
    """
    Concurrency-Protected Claim Assignment Route.

    Assigns a 'submitted' claim to the logged-in officer and transitions its lifecycle
    state to 'in_review'. Implements race-condition checks to prevent two officers
    from locking the same claim simultaneously.

    Args:
        claim_id (int): Primary key ID of the claim to assign.
    """
    user = get_current_user()
    claim = Claim.query.get_or_404(claim_id)

    # Concurrency guard: Must be in 'submitted' state
    if claim.status != "submitted":
        flash(f"Claim #{claim.id} is already in state '{claim.status}' and cannot be claimed from queue.", "warning")
        return redirect(url_for("claims.claim_detail", claim_id=claim.id))

    # Race-condition guard: Ensure no other officer already locked it
    if claim.officer_user_id and claim.officer_user_id != user.id:
        assigned_officer = User.query.get(claim.officer_user_id)
        flash(
            f"Claim #{claim.id} has already been assigned to officer {assigned_officer.display_name if assigned_officer else 'another officer'}.",
            "danger",
        )
        return redirect(url_for("officer.review_queue"))

    # Lock claim to officer and move to IN REVIEW
    claim.officer_user_id = user.id
    claim.status = "in_review"

    # Append immutable event log
    record_history_event(
        claim=claim,
        from_status="submitted",
        to_status="in_review",
        actor_user_id=user.id,
        note=f"Claim assigned to officer {user.display_name} for review.",
    )
    db.session.commit()
    flash(f"Claim #{claim.id} assigned to you and moved to IN REVIEW.", "success")
    return redirect(url_for("claims.claim_detail", claim_id=claim.id))


@officer_bp.route("/claim/<int:claim_id>/request-info", methods=["POST"])
@role_required("claims_officer", "admin")
def request_info(claim_id: int):
    """
    Document Query / Clarification Route.

    Transitions an 'in_review' claim into 'more_info' status and records the
    officer's explanation note (e.g. 'Discharge summary missing treating doctor stamp').

    Args:
        claim_id (int): Primary key ID of the claim.
    """
    user = get_current_user()
    claim = Claim.query.get_or_404(claim_id)

    if claim.status != "in_review":
        flash("Can only request information for claims currently in review.", "warning")
        return redirect(url_for("claims.claim_detail", claim_id=claim.id))

    reason = request.form.get("reason", "").strip()
    missing_item = request.form.get("missing_item", "").strip()

    if not reason:
        flash("A clear reason is required when requesting more information.", "danger")
        return redirect(url_for("claims.claim_detail", claim_id=claim.id))

    full_note = f"Information Requested: {reason}"
    if missing_item:
        full_note += f" | Checklist Item Needed: {missing_item}"

    claim.status = "more_info"
    record_history_event(
        claim=claim,
        from_status="in_review",
        to_status="more_info",
        actor_user_id=user.id,
        note=full_note,
    )
    db.session.commit()
    flash(f"Claim #{claim.id} moved to MORE_INFO. Submitter has been requested for details.", "info")
    return redirect(url_for("claims.claim_detail", claim_id=claim.id))


@officer_bp.route("/claim/<int:claim_id>/decide", methods=["POST"])
@role_required("claims_officer", "admin")
def decide_claim(claim_id: int):
    """
    Formal Adjudication Decision Route (Approval / Rejection).

    Validates:
        1. Current status must be 'in_review'.
        2. A written justification reason is mandatory.
        3. On Approval:
           - Eligible amount must be > 0 and <= requested bill amount.
           - Eligible amount cannot exceed the policy's remaining annual cover.
           - Treatment type must be covered under the plan.
           - Executes payout formula: Base = (Eligible - Deductible) * (1 - Copay).
           - Sets status to 'approved' and records event history.
        4. On Rejection:
           - Sets eligible amount to ₹0.00, status to 'rejected', and logs reason.

    Args:
        claim_id (int): Primary key ID of the claim being decided.
    """
    user = get_current_user()
    claim = Claim.query.get_or_404(claim_id)

    if claim.status != "in_review":
        flash("Only claims currently in review can be decided.", "danger")
        return redirect(url_for("claims.claim_detail", claim_id=claim.id))

    decision = request.form.get("decision", "").strip()  # 'approve' or 'reject'
    reason = request.form.get("reason", "").strip()

    if not reason:
        flash("A written reason is strictly required for claim decisions.", "danger")
        return redirect(url_for("claims.claim_detail", claim_id=claim.id))

    if decision == "approve":
        eligible_str = request.form.get("eligible_amount", "").strip()
        try:
            eligible_amount = Decimal(eligible_str)
        except (ValueError, TypeError):
            flash("Invalid eligible amount entered.", "danger")
            return redirect(url_for("claims.claim_detail", claim_id=claim.id))

        if eligible_amount <= Decimal("0.00"):
            flash("Eligible amount must be greater than ₹0 for approval.", "danger")
            return redirect(url_for("claims.claim_detail", claim_id=claim.id))

        if eligible_amount > claim.requested_amount_inr:
            flash(
                f"Eligible amount (₹{eligible_amount}) cannot exceed the requested amount (₹{claim.requested_amount_inr}).",
                "danger",
            )
            return redirect(url_for("claims.claim_detail", claim_id=claim.id))

        # Check remaining annual coverage boundary
        remaining_cover = get_remaining_cover(claim.policy, exclude_claim_id=claim.id)
        if eligible_amount > remaining_cover:
            flash(
                f"Eligible amount (₹{eligible_amount}) exceeds the available policy cover (₹{remaining_cover}).",
                "danger",
            )
            return redirect(url_for("claims.claim_detail", claim_id=claim.id))

        # Verify plan treatment type compatibility
        if not claim.policy.plan.covers_treatment(claim.treatment_type):
            flash(
                f"Cannot approve: Treatment type '{claim.treatment_type}' is outside '{claim.policy.plan.name}' coverage.",
                "danger",
            )
            return redirect(url_for("claims.claim_detail", claim_id=claim.id))

        # Calculate net payout after deductible and copay
        payout = calculate_payout(
            eligible_amount=eligible_amount,
            deductible=claim.policy.plan.deductible_inr,
            copay_percent=claim.policy.plan.copay_percent,
        )

        claim.status = "approved"
        claim.eligible_amount_inr = eligible_amount
        note = f"Approved for eligible ₹{eligible_amount} (Calculated simulated payout: ₹{payout}). Reason: {reason}"

        record_history_event(
            claim=claim,
            from_status="in_review",
            to_status="approved",
            actor_user_id=user.id,
            note=note,
        )
        db.session.commit()
        flash(f"Claim #{claim.id} approved successfully for ₹{eligible_amount}.", "success")

    elif decision == "reject":
        claim.status = "rejected"
        claim.eligible_amount_inr = Decimal("0.00")
        note = f"Claim Rejected. Reason: {reason}"

        record_history_event(
            claim=claim,
            from_status="in_review",
            to_status="rejected",
            actor_user_id=user.id,
            note=note,
        )
        db.session.commit()
        flash(f"Claim #{claim.id} rejected.", "warning")
    else:
        flash("Invalid decision action.", "danger")

    return redirect(url_for("claims.claim_detail", claim_id=claim.id))
