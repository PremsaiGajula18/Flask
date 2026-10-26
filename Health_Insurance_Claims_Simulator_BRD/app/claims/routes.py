import datetime
from decimal import Decimal
from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy import or_

from app.auth.decorators import get_current_user, login_required
from app.extensions import db
from app.models import (
    Claim,
    ClaimDocument,
    ClaimHistory,
    Hospital,
    Member,
    Plan,
    Policy,
    Settlement,
    User,
)
from app.services.calculator import (
    calculate_payout,
    get_calculation_breakdown,
    get_prior_paid_payouts,
    get_remaining_cover,
)
from app.services.rules import (
    check_potential_duplicates,
    record_history_event,
    validate_claim_data,
)
from app.services.plan_checker import evaluate_plan_satisfaction

claims_bp = Blueprint("claims", __name__)


@claims_bp.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("claims.dashboard"))
    return redirect(url_for("auth.login"))


@claims_bp.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for("auth.login"))

    role = user.role
    context = {"user": user, "role": role}

    if role == "policyholder":
        policies = Policy.query.filter_by(holder_user_id=user.id).all()
        policy_ids = [p.id for p in policies]
        claims = (
            Claim.query.filter(Claim.policy_id.in_(policy_ids))
            .order_by(Claim.created_at.desc())
            .all()
            if policy_ids
            else []
        )
        context.update(
            {
                "policies": policies,
                "claims": claims,
                "draft_count": sum(1 for c in claims if c.status == "draft"),
                "in_review_count": sum(1 for c in claims if c.status in ("submitted", "in_review", "more_info")),
                "approved_count": sum(1 for c in claims if c.status == "approved"),
                "paid_count": sum(1 for c in claims if c.status == "paid"),
            }
        )

    elif role == "hospital":
        hospital = Hospital.query.get(user.hospital_id) if user.hospital_id else None
        claims = (
            Claim.query.filter_by(hospital_id=user.hospital_id)
            .order_by(Claim.created_at.desc())
            .all()
            if user.hospital_id
            else []
        )
        context.update(
            {
                "hospital": hospital,
                "claims": claims,
                "draft_count": sum(1 for c in claims if c.status == "draft"),
                "submitted_count": sum(1 for c in claims if c.status == "submitted"),
                "more_info_count": sum(1 for c in claims if c.status == "more_info"),
                "approved_count": sum(1 for c in claims if c.status == "approved"),
                "paid_count": sum(1 for c in claims if c.status == "paid"),
            }
        )

    elif role == "claims_officer":
        unassigned_count = Claim.query.filter_by(status="submitted", officer_user_id=None).count()
        my_review_count = Claim.query.filter_by(status="in_review", officer_user_id=user.id).count()
        more_info_count = Claim.query.filter_by(status="more_info", officer_user_id=user.id).count()
        my_total_decided = Claim.query.filter(
            Claim.officer_user_id == user.id, Claim.status.in_(["approved", "rejected", "paid"])
        ).count()
        recent_queue = (
            Claim.query.filter(Claim.status.in_(["submitted", "in_review", "more_info"]))
            .order_by(Claim.created_at.desc())
            .limit(10)
            .all()
        )
        context.update(
            {
                "unassigned_count": unassigned_count,
                "my_review_count": my_review_count,
                "more_info_count": more_info_count,
                "my_total_decided": my_total_decided,
                "recent_queue": recent_queue,
            }
        )

    elif role == "admin":
        pending_settlements = Claim.query.filter_by(status="approved").count()
        total_claims = Claim.query.count()
        total_settled_amount = db.session.query(
            db.func.coalesce(db.func.sum(Settlement.amount_inr), Decimal("0.00"))
        ).scalar()
        hospitals_count = Hospital.query.count()
        users_count = User.query.count()
        context.update(
            {
                "pending_settlements": pending_settlements,
                "total_claims": total_claims,
                "total_settled_amount": total_settled_amount,
                "hospitals_count": hospitals_count,
                "users_count": users_count,
            }
        )

    return render_template("claims/dashboard.html", **context)


@claims_bp.route("/policies")
@login_required
def my_policies():
    user = get_current_user()
    if user.role != "policyholder":
        flash("Policy view is reserved for policyholders.", "warning")
        return redirect(url_for("claims.dashboard"))

    policies = Policy.query.filter_by(holder_user_id=user.id).all()
    policy_data = []
    for pol in policies:
        rem_cover = get_remaining_cover(pol)
        prior_paid = get_prior_paid_payouts(pol.id)
        policy_data.append({"policy": pol, "remaining_cover": rem_cover, "prior_paid": prior_paid})

    return render_template("claims/my_policies.html", policies=policy_data, user=user)


@claims_bp.route("/claims")
@login_required
def claim_list():
    user = get_current_user()
    query = Claim.query

    # Role-based scoping
    if user.role == "policyholder":
        user_policy_ids = [p.id for p in Policy.query.filter_by(holder_user_id=user.id).all()]
        query = query.filter(Claim.policy_id.in_(user_policy_ids)) if user_policy_ids else query.filter(Claim.id == -1)
    elif user.role == "hospital":
        if not user.hospital_id:
            query = query.filter(Claim.id == -1)
        else:
            query = query.filter(Claim.hospital_id == user.hospital_id, Claim.claim_type == "cashless")

    # Search filter (Claim ID or Member Name)
    q = request.args.get("q", "").strip()
    if q:
        if q.isdigit():
            query = query.filter(or_(Claim.id == int(q), Claim.member.has(Member.display_name.ilike(f"%{q}%"))))
        else:
            query = query.filter(Claim.member.has(Member.display_name.ilike(f"%{q}%")))

    # Status filter
    status = request.args.get("status", "").strip()
    if status:
        query = query.filter(Claim.status == status)

    # Claim type filter
    claim_type = request.args.get("claim_type", "").strip()
    if claim_type:
        query = query.filter(Claim.claim_type == claim_type)

    # Hospital filter
    hospital_id = request.args.get("hospital_id", "").strip()
    if hospital_id and hospital_id.isdigit():
        query = query.filter(Claim.hospital_id == int(hospital_id))

    claims = query.order_by(Claim.created_at.desc()).all()
    hospitals = Hospital.query.order_by(Hospital.name).all()

    return render_template(
        "claims/claim_list.html",
        claims=claims,
        hospitals=hospitals,
        current_user=user,
        filters={
            "q": q,
            "status": status,
            "claim_type": claim_type,
            "hospital_id": hospital_id,
        },
    )


@claims_bp.route("/claims/new", methods=["GET", "POST"])
@login_required
def create_claim():
    user = get_current_user()
    if user.role not in ("policyholder", "hospital"):
        flash("Only policyholders and hospital desks can create claims.", "danger")
        return redirect(url_for("claims.dashboard"))

    if request.method == "POST":
        action = request.form.get("action", "draft")  # 'draft' or 'submit'
        is_submit = action == "submit"

        policy_id_raw = request.form.get("policy_id", "")
        policy_id = None
        if policy_id_raw:
            import re
            m = re.search(r'\d+', str(policy_id_raw))
            if m:
                policy_id = int(m.group(0))
        member_id = request.form.get("member_id", type=int)
        treatment_type = request.form.get("treatment_type", "").strip()
        admission_date_str = request.form.get("admission_date", "").strip()
        discharge_date_str = request.form.get("discharge_date", "").strip()
        requested_amount_str = request.form.get("requested_amount", "").strip()
        description = request.form.get("description", "").strip()
        claim_category = request.form.get("claim_category", "inpatient").strip()
        includes_consumables = request.form.get("includes_consumables") == "1"

        # Determine claim type and hospital
        if user.role == "hospital":
            claim_type = "cashless"
            hospital_id = user.hospital_id
        else:
            claim_type = "reimbursement"
            hospital_id = request.form.get("hospital_id", type=int)

        # Parse dates and amount
        try:
            admission_date = datetime.datetime.strptime(admission_date_str, "%Y-%m-%d").date()
            discharge_date = datetime.datetime.strptime(discharge_date_str, "%Y-%m-%d").date()
            requested_amount = Decimal(requested_amount_str)
        except (ValueError, TypeError):
            flash("Invalid date or monetary amount format.", "danger")
            return redirect(url_for("claims.create_claim"))

        policy = Policy.query.get(policy_id)
        member = Member.query.get(member_id)
        hospital = Hospital.query.get(hospital_id)

        if not policy or not member or not hospital:
            flash("Invalid policy, member, or hospital selection.", "danger")
            return redirect(url_for("claims.create_claim"))

        # Validate business rules
        valid, errors = validate_claim_data(
            policy=policy,
            member=member,
            hospital=hospital,
            user=user,
            claim_type=claim_type,
            treatment_type=treatment_type,
            admission_date=admission_date,
            discharge_date=discharge_date,
            requested_amount=requested_amount,
            is_submission=is_submit,
        )

        if not valid:
            for err in errors:
                flash(err, "danger")
            return redirect(url_for("claims.create_claim"))

        # Run Plan Satisfaction Check
        is_satisfied, satisfaction_status, satisfaction_notes = evaluate_plan_satisfaction(
            policy=policy,
            claim_category=claim_category,
            treatment_type=treatment_type,
            requested_amount=float(requested_amount),
            includes_consumables=includes_consumables
        )

        # Routing decision: If is_submit, determine if it passes to Claims Officer queue
        if is_submit:
            if is_satisfied:
                status = "submitted"  # Eligible -> Enters Claims Officer review queue!
            else:
                status = "draft"  # Plan Satisfaction Failed -> Stays in draft with audit flag!
                flash("Plan Satisfaction Check Alert: One or more plan policy constraints failed. Please review the details.", "warning")
        else:
            status = "draft"

        claim = Claim(
            policy_id=policy.id,
            member_id=member.id,
            hospital_id=hospital.id,
            claim_type=claim_type,
            treatment_type=treatment_type,
            claim_category=claim_category,
            includes_consumables=includes_consumables,
            satisfaction_status=satisfaction_status,
            satisfaction_notes=satisfaction_notes,
            admission_date=admission_date,
            discharge_date=discharge_date,
            requested_amount_inr=requested_amount,
            status=status,
        )
        db.session.add(claim)
        db.session.flush()

        # Create standard document checklist metadata
        doc_bill = ClaimDocument(
            claim_id=claim.id,
            document_type="hospital_bill",
            checklist_status=request.form.get("doc_bill", "missing"),
        )
        doc_discharge = ClaimDocument(
            claim_id=claim.id,
            document_type="discharge_summary",
            checklist_status=request.form.get("doc_discharge", "missing"),
        )
        db.session.add_all([doc_bill, doc_discharge])

        # Record audit history event
        note = description or (f"Claim {status} by {user.display_name}")
        record_history_event(
            claim=claim,
            from_status=None,
            to_status=status,
            actor_user_id=user.id,
            note=note,
        )

        db.session.commit()
        flash(f"Claim #{claim.id} created successfully as {status.upper()}.", "success")
        return redirect(url_for("claims.claim_detail", claim_id=claim.id))

    # GET request - load forms
    if user.role == "policyholder":
        policies = Policy.query.filter_by(holder_user_id=user.id, status="active").all()
        hospitals = Hospital.query.order_by(Hospital.name).all()
        default_hospital = None
    else:
        # Hospital desk can enter any active policy for a patient admitted to their hospital
        policies = Policy.query.filter_by(status="active").all()
        hospitals = Hospital.query.filter_by(id=user.hospital_id).all()
        default_hospital = hospitals[0] if hospitals else None

    return render_template(
        "claims/create_claim.html",
        user=user,
        policies=policies,
        hospitals=hospitals,
        default_hospital=default_hospital,
        today=datetime.date.today(),
    )


@claims_bp.route("/claims/<int:claim_id>")
@login_required
def claim_detail(claim_id: int):
    user = get_current_user()
    claim = Claim.query.get_or_404(claim_id)

    # Authorization Check
    if user.role == "policyholder" and claim.policy.holder_user_id != user.id:
        abort(403)
    elif user.role == "hospital" and (claim.hospital_id != user.hospital_id or claim.claim_type != "cashless"):
        abort(403)

    # Check for potential duplicates
    duplicates = check_potential_duplicates(
        member_id=claim.member_id,
        hospital_id=claim.hospital_id,
        admission_date=claim.admission_date,
        discharge_date=claim.discharge_date,
        claim_type=claim.claim_type,
        exclude_claim_id=claim.id,
    )

    # Calculate remaining cover
    remaining_cover = get_remaining_cover(claim.policy, exclude_claim_id=claim.id)

    # Calculation breakdown if eligible amount is present
    breakdown = None
    if claim.eligible_amount_inr is not None:
        breakdown = get_calculation_breakdown(
            requested_amount=claim.requested_amount_inr,
            eligible_amount=claim.eligible_amount_inr,
            deductible=claim.policy.plan.deductible_inr,
            copay_percent=claim.policy.plan.copay_percent,
        )

    return render_template(
        "claims/claim_detail.html",
        claim=claim,
        duplicates=duplicates,
        remaining_cover=remaining_cover,
        breakdown=breakdown,
        current_user=user,
    )


@claims_bp.route("/claims/<int:claim_id>/submit", methods=["POST"])
@login_required
def submit_draft(claim_id: int):
    user = get_current_user()
    claim = Claim.query.get_or_404(claim_id)

    # Only creator can submit draft
    if claim.status != "draft":
        flash("Only draft claims can be submitted.", "warning")
        return redirect(url_for("claims.claim_detail", claim_id=claim.id))

    if user.role == "policyholder" and claim.policy.holder_user_id != user.id:
        abort(403)
    if user.role == "hospital" and claim.hospital_id != user.hospital_id:
        abort(403)

    valid, errors = validate_claim_data(
        policy=claim.policy,
        member=claim.member,
        hospital=claim.hospital,
        user=user,
        claim_type=claim.claim_type,
        treatment_type=claim.treatment_type,
        admission_date=claim.admission_date,
        discharge_date=claim.discharge_date,
        requested_amount=claim.requested_amount_inr,
        is_submission=True,
    )

    if not valid:
        for err in errors:
            flash(err, "danger")
        return redirect(url_for("claims.claim_detail", claim_id=claim.id))

    claim.status = "submitted"
    record_history_event(
        claim=claim,
        from_status="draft",
        to_status="submitted",
        actor_user_id=user.id,
        note="Claim submitted for insurance evaluation.",
    )
    db.session.commit()
    flash(f"Claim #{claim.id} submitted successfully.", "success")
    return redirect(url_for("claims.claim_detail", claim_id=claim.id))


@claims_bp.route("/claims/<int:claim_id>/respond", methods=["POST"])
@login_required
def respond_more_info(claim_id: int):
    user = get_current_user()
    claim = Claim.query.get_or_404(claim_id)

    if claim.status != "more_info":
        flash("This claim is not awaiting more information.", "warning")
        return redirect(url_for("claims.claim_detail", claim_id=claim.id))

    if user.role == "policyholder" and claim.policy.holder_user_id != user.id:
        abort(403)
    if user.role == "hospital" and claim.hospital_id != user.hospital_id:
        abort(403)

    response_note = request.form.get("response_note", "").strip()
    if not response_note:
        flash("Please provide a response explanation.", "danger")
        return redirect(url_for("claims.claim_detail", claim_id=claim.id))

    # Update checklist metadata if provided
    for doc in claim.documents:
        status_val = request.form.get(f"doc_{doc.id}")
        if status_val in ("received", "missing"):
            doc.checklist_status = status_val

    claim.status = "submitted"
    record_history_event(
        claim=claim,
        from_status="more_info",
        to_status="submitted",
        actor_user_id=user.id,
        note=f"Information submitted by {user.display_name}: {response_note}",
    )
    db.session.commit()
    flash(f"Response recorded for Claim #{claim.id}. It is now back in the claims queue.", "success")
    return redirect(url_for("claims.claim_detail", claim_id=claim.id))


@claims_bp.route("/api/policies/<int:policy_id>/members")
@login_required
def api_policy_members(policy_id: int):
    policy = Policy.query.get_or_404(policy_id)
    members_data = [
        {"id": m.id, "display_name": m.display_name, "relationship": m.relationship}
        for m in policy.members
    ]
    plan = policy.plan
    return jsonify({
        "policy_id": policy.id,
        "holder_name": policy.holder.display_name if policy.holder else "",
        "plan_name": plan.name,
        "insurer": plan.insurer,
        "annual_limit_inr": float(plan.annual_limit_inr),
        "sum_insured_display": plan.sum_insured_display,
        "restoration_benefit": plan.restoration_benefit,
        "pre_hospitalization_days": plan.pre_hospitalization_days,
        "post_hospitalization_days": plan.post_hospitalization_days,
        "room_rent_limit": plan.room_rent_limit,
        "ayush_cover": plan.ayush_cover,
        "consumables_cover": plan.consumables_cover,
        "opd_dental_cover": plan.opd_dental_cover,
        "age_freeze": plan.age_freeze,
        "bonus_multiplier": plan.bonus_multiplier,
        "waiting_period_ped": plan.waiting_period_ped,
        "members": members_data
    })
