import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship as sa_relationship

from app.extensions import db


class User(db.Model):
    """
    User entity supporting 4 distinct roles:
    - policyholder: owns policies and submits reimbursement claims
    - hospital: linked to one hospital and submits cashless claims
    - claims_officer: reviews, queries, approves/rejects claims
    - admin: records settlement and manages system reference data
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)  # policyholder, hospital, claims_officer, admin
    hospital_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("hospitals.id"), nullable=True)

    # Relationships
    hospital: Mapped[Optional["Hospital"]] = sa_relationship("Hospital", back_populates="staff_users")
    policies: Mapped[List["Policy"]] = sa_relationship("Policy", back_populates="holder")
    assigned_claims: Mapped[List["Claim"]] = sa_relationship("Claim", back_populates="officer")

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"


class Hospital(db.Model):
    """
    Hospital directory record.
    network_status=True indicates empanelled network hospital eligible for cashless claims.
    """
    __tablename__ = "hospitals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    network_status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    staff_users: Mapped[List["User"]] = sa_relationship("User", back_populates="hospital")
    claims: Mapped[List["Claim"]] = sa_relationship("Claim", back_populates="hospital")

    def __repr__(self) -> str:
        status_str = "Network" if self.network_status else "Non-Network"
        return f"<Hospital {self.name} ({self.city}) - {status_str}>"


class Plan(db.Model):
    """
    Fictional health insurance plan terms:
    - covered_treatment_types: e.g. 'inpatient' or 'inpatient|daycare'
    - annual_limit_inr: max annual coverage per policy year
    - deductible_inr: deductible per claim
    - copay_percent: percentage patient co-pay
    """
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    insurer: Mapped[str] = mapped_column(String(100), default="National Health", nullable=False)
    covered_treatment_types: Mapped[str] = mapped_column(String(100), nullable=False)
    annual_limit_inr: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    deductible_inr: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    copay_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    sum_insured_display: Mapped[str] = mapped_column(String(100), default="₹5 L – ₹1 Crore", nullable=False)
    restoration_benefit: Mapped[str] = mapped_column(String(150), default="100% Unlimited", nullable=False)
    pre_hospitalization_days: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    post_hospitalization_days: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    room_rent_limit: Mapped[str] = mapped_column(String(100), default="No Cap", nullable=False)
    ayush_cover: Mapped[str] = mapped_column(String(100), default="Included up to SI", nullable=False)
    consumables_cover: Mapped[str] = mapped_column(String(100), default="Included", nullable=False)
    opd_dental_cover: Mapped[str] = mapped_column(String(100), default="No", nullable=False)
    age_freeze: Mapped[str] = mapped_column(String(100), default="No", nullable=False)
    bonus_multiplier: Mapped[str] = mapped_column(String(150), default="Up to 100%", nullable=False)
    waiting_period_ped: Mapped[str] = mapped_column(String(150), default="3 Years", nullable=False)

    policies: Mapped[List["Policy"]] = sa_relationship("Policy", back_populates="plan")

    def covers_treatment(self, treatment_type: str) -> bool:
        """Check if treatment_type is allowed under this plan."""
        allowed = [t.strip().lower() for t in self.covered_treatment_types.split("|")]
        return treatment_type.strip().lower() in allowed

    def __repr__(self) -> str:
        return f"<Plan {self.name} (Limit: {self.annual_limit_inr})>"


class Policy(db.Model):
    """
    Policy issued to a policyholder under a specific plan.
    """
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    holder_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)

    holder: Mapped["User"] = sa_relationship("User", back_populates="policies")
    plan: Mapped["Plan"] = sa_relationship("Plan", back_populates="policies")
    members: Mapped[List["Member"]] = sa_relationship("Member", back_populates="policy", cascade="all, delete-orphan")
    claims: Mapped[List["Claim"]] = sa_relationship("Claim", back_populates="policy")

    def is_active_on(self, check_date: datetime.date) -> bool:
        """Check if policy is active and check_date falls between start and end date inclusive."""
        return self.status.lower() == "active" and (self.start_date <= check_date <= self.end_date)

    def __repr__(self) -> str:
        return f"<Policy #{self.id} (Holder: {self.holder_user_id}, Status: {self.status})>"


class Member(db.Model):
    """
    Covered family member under a policy.
    """
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    policy_id: Mapped[int] = mapped_column(Integer, ForeignKey("policies.id"), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    relationship: Mapped[str] = mapped_column(String(50), nullable=False)

    policy: Mapped["Policy"] = sa_relationship("Policy", back_populates="members")
    claims: Mapped[List["Claim"]] = sa_relationship("Claim", back_populates="member")

    def __repr__(self) -> str:
        return f"<Member {self.display_name} ({self.relationship}) - Policy #{self.policy_id}>"


class Claim(db.Model):
    """
    Health Insurance Claim entity.
    Transitions through:
    draft -> submitted -> in_review -> more_info -> submitted
                       -> approved -> paid
                       -> rejected
    """
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    policy_id: Mapped[int] = mapped_column(Integer, ForeignKey("policies.id"), nullable=False, index=True)
    member_id: Mapped[int] = mapped_column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    hospital_id: Mapped[int] = mapped_column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)
    claim_type: Mapped[str] = mapped_column(String(20), nullable=False)  # cashless, reimbursement
    treatment_type: Mapped[str] = mapped_column(String(20), nullable=False)  # inpatient, daycare
    admission_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    discharge_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    requested_amount_inr: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False, index=True)
    eligible_amount_inr: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    officer_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    payment_recorded_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    claim_category: Mapped[str] = mapped_column(String(50), default="inpatient", nullable=False)
    includes_consumables: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    satisfaction_status: Mapped[str] = mapped_column(String(50), default="passed", nullable=False)
    satisfaction_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False
    )

    # Relationships
    policy: Mapped["Policy"] = sa_relationship("Policy", back_populates="claims")
    member: Mapped["Member"] = sa_relationship("Member", back_populates="claims")
    hospital: Mapped["Hospital"] = sa_relationship("Hospital", back_populates="claims")
    officer: Mapped[Optional["User"]] = sa_relationship("User", back_populates="assigned_claims")
    documents: Mapped[List["ClaimDocument"]] = sa_relationship(
        "ClaimDocument", back_populates="claim", cascade="all, delete-orphan"
    )
    history: Mapped[List["ClaimHistory"]] = sa_relationship(
        "ClaimHistory",
        back_populates="claim",
        cascade="all, delete-orphan",
        order_by="ClaimHistory.sequence_no",
    )
    settlement: Mapped[Optional["Settlement"]] = sa_relationship(
        "Settlement", back_populates="claim", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_claims_policy_status", "policy_id", "status"),
        Index("idx_claims_officer_status", "officer_user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Claim #{self.id} ({self.claim_type}, Status: {self.status}, Req: {self.requested_amount_inr})>"


class ClaimDocument(db.Model):
    """
    Checklist metadata indicating received vs missing documents.
    No physical file required.
    """
    __tablename__ = "claim_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(Integer, ForeignKey("claims.id"), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)  # hospital_bill, discharge_summary
    checklist_status: Mapped[str] = mapped_column(String(30), default="missing", nullable=False)  # received, missing

    claim: Mapped["Claim"] = sa_relationship("Claim", back_populates="documents")

    def __repr__(self) -> str:
        return f"<ClaimDocument #{self.id} Claim #{self.claim_id}: {self.document_type} ({self.checklist_status})>"


class ClaimHistory(db.Model):
    """
    Immutable chronological audit trail of all state transitions and notes.
    """
    __tablename__ = "claim_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(Integer, ForeignKey("claims.id"), nullable=False, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    from_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    event_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)

    claim: Mapped["Claim"] = sa_relationship("Claim", back_populates="history")
    actor: Mapped[Optional["User"]] = sa_relationship("User")

    __table_args__ = (
        Index("idx_claim_history_claim_time", "claim_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<ClaimHistory #{self.id} Claim #{self.claim_id} [{self.from_status} -> {self.to_status}]>"


class Settlement(db.Model):
    """
    Simulated settlement recorded by Administrator.
    payee_type:
    - 'hospital' for cashless
    - 'policyholder' for reimbursement
    """
    __tablename__ = "settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    claim_id: Mapped[int] = mapped_column(Integer, ForeignKey("claims.id"), unique=True, nullable=False)
    payee_type: Mapped[str] = mapped_column(String(30), nullable=False)  # hospital, policyholder
    amount_inr: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    recorded_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    recorded_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)

    claim: Mapped["Claim"] = sa_relationship("Claim", back_populates="settlement")
    recorded_by: Mapped["User"] = sa_relationship("User")

    def __repr__(self) -> str:
        return f"<Settlement Claim #{self.claim_id}: ₹{self.amount_inr} to {self.payee_type}>"
