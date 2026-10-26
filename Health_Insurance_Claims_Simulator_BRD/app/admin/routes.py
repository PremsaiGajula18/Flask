"""
========================================================================================
ADMINISTRATOR OPERATIONS, SETTLEMENT DISBURSEMENT & REPORTING CONTROLLER
========================================================================================
Project     : Health Insurance Claims Processing Simulator (BRD Benchmark)
Component   : Administrator Controller (`app/admin/routes.py`)
========================================================================================
Description:
    Provides system administration and financial settlement recording:
    - Settlement Recording: Executes simulated financial payment disbursements for
      approved claims (payee routed to Hospital for cashless, Policyholder for reimbursement).
    - Reference Data Management: Read-only master directories for hospitals, plans, and users.
    - Operational Portfolio Reports: Aggregates claim volume by status, total requested vs.
      settled funds, average processing turn-around-times, and duplicate alerts.
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
    url_for,
)
from sqlalchemy import func

from app.auth.decorators import get_current_user, role_required
from app.extensions import db
from app.models import Claim, Hospital, Plan, Policy, Settlement, User
from app.services.calculator import calculate_payout
from app.services.rules import record_history_event

# Administrator Blueprint mounted at URL prefix /admin
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/settlements")
@role_required("admin")
def settlements_list():
    """
    Settlement Management Dashboard.

    Renders two operational lists:
        1. Approved claims awaiting simulated financial disbursement.
        2. Historical settlements already recorded and marked as 'paid'.
    """
    approved_claims = Claim.query.filter_by(status="approved").order_by(Claim.created_at.asc()).all()
    settled_claims = Claim.query.filter_by(status="paid").order_by(Claim.payment_recorded_date.desc()).all()

    return render_template(
        "admin/settlements.html",
        approved_claims=approved_claims,
        settled_claims=settled_claims,
    )


@admin_bp.route("/settlements/<int:claim_id>/pay", methods=["POST"])
@role_required("admin")
def record_settlement(claim_id: int):
    """
    Financial Payment Settlement Execution Route.

    Records the simulated fund transfer for an approved claim:
        1. Verifies that the claim is in 'approved' status.
        2. Computes the final payout using `calculate_payout()`.
        3. Sets payee type: 'hospital' for cashless claims; 'policyholder' for reimbursement.
        4. Creates an immutable `Settlement` record with current date and admin user ID.
        5. Updates claim status to 'paid' and records `payment_recorded_date`.
        6. Appends an audit event to `claim_history`.
        7. Commits changes atomically or rolls back on exception.

    Args:
        claim_id (int): Primary key ID of the approved claim.
    """
    user = get_current_user()
    claim = Claim.query.get_or_404(claim_id)

    if claim.status != "approved":
        flash("Settlements can only be recorded for APPROVED claims.", "danger")
        return redirect(url_for("admin.settlements_list"))

    if not claim.eligible_amount_inr or claim.eligible_amount_inr <= Decimal("0.00"):
        flash("Cannot settle claim without an approved eligible amount.", "danger")
        return redirect(url_for("admin.settlements_list"))

    # Compute net insurer payout
    plan = claim.policy.plan
    payout = calculate_payout(
        eligible_amount=claim.eligible_amount_inr,
        deductible=plan.deductible_inr,
        copay_percent=plan.copay_percent,
    )

    payee_type = "hospital" if claim.claim_type == "cashless" else "policyholder"
    today = datetime.date.today()

    try:
        # Step 1: Create Settlement entity
        settlement = Settlement(
            claim_id=claim.id,
            payee_type=payee_type,
            amount_inr=payout,
            recorded_by_user_id=user.id,
            recorded_date=today,
        )
        db.session.add(settlement)

        # Step 2: Transition claim status to 'paid'
        claim.status = "paid"
        claim.payment_recorded_date = today

        # Step 3: Append immutable audit history log
        record_history_event(
            claim=claim,
            from_status="approved",
            to_status="paid",
            actor_user_id=user.id,
            note=f"Payment settlement of ₹{payout} recorded to {payee_type} by Admin {user.display_name}.",
            event_date=today,
        )

        # Commit all mutations atomically
        db.session.commit()
        flash(f"Settlement of ₹{payout:,.2f} recorded successfully for Claim #{claim.id}.", "success")

    except Exception as exc:
        db.session.rollback()
        flash(f"Error processing settlement: {exc}", "danger")

    return redirect(url_for("admin.settlements_list"))


@admin_bp.route("/reference-data")
@role_required("admin")
def reference_data():
    """
    Master Reference Data Inspection Route.

    Displays system-wide dictionaries:
        - Hospital network directory (names, cities, empanelment status)
        - Insurance plan terms (annual limits, copays, deductibles, room rent caps)
        - System users and their assigned operational roles
    """
    hospitals = Hospital.query.order_by(Hospital.name).all()
    plans = Plan.query.order_by(Plan.name).all()
    users = User.query.order_by(User.role, User.username).all()

    return render_template(
        "admin/reference.html",
        hospitals=hospitals,
        plans=plans,
        users=users,
    )


@admin_bp.route("/reports")
@role_required("admin")
def reports():
    """
    System Portfolio Analytics & Reports Route.

    Computes key performance indicators (KPIs) using SQL aggregations:
        - Total claims count and breakdown by lifecycle status
        - Total requested amount vs. total approved eligible amount vs. settled payouts
        - Cashless vs. Reimbursement distribution percentages
        - Empanelled hospital utilization metrics
    """
    total_claims = Claim.query.count()
    status_counts = (
        db.session.query(Claim.status, func.count(Claim.id))
        .group_by(Claim.status)
        .all()
    )

    total_requested = (
        db.session.query(func.coalesce(func.sum(Claim.requested_amount_inr), Decimal("0.00")))
        .scalar()
    )
    total_eligible = (
        db.session.query(func.coalesce(func.sum(Claim.eligible_amount_inr), Decimal("0.00")))
        .scalar()
    )
    total_settled = (
        db.session.query(func.coalesce(func.sum(Settlement.amount_inr), Decimal("0.00")))
        .scalar()
    )

    claims_by_hospital = (
        db.session.query(Hospital.name, func.count(Claim.id))
        .join(Claim, Hospital.id == Claim.hospital_id)
        .group_by(Hospital.name)
        .all()
    )

    return render_template(
        "admin/reports.html",
        total_claims=total_claims,
        status_counts=dict(status_counts),
        total_requested=total_requested,
        total_eligible=total_eligible,
        total_settled=total_settled,
        claims_by_hospital=claims_by_hospital,
    )
