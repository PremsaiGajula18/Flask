import datetime
from decimal import Decimal
import os
import unittest

from werkzeug.security import check_password_hash, generate_password_hash

from app import create_app
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
    get_remaining_cover,
)
from app.services.rules import check_potential_duplicates, validate_claim_data


class HealthClaimsSimulatorTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()

    def test_01_financial_calculator_formula(self):
        """Verify BRD Section 8 exact financial payout arithmetic."""
        # Example from BRD: eligible ₹20,000; deductible ₹2,000; co-pay 10% -> ₹16,200
        payout = calculate_payout(
            eligible_amount=Decimal("20000.00"),
            deductible=Decimal("2000.00"),
            copay_percent=Decimal("10.00"),
        )
        self.assertEqual(payout, Decimal("16200.00"))

        # Breakdown test
        breakdown = get_calculation_breakdown(
            requested_amount=Decimal("28000.00"),
            eligible_amount=Decimal("26000.00"),
            deductible=Decimal("2000.00"),
            copay_percent=Decimal("10.00"),
        )
        self.assertEqual(breakdown["disallowed_amount"], Decimal("2000.00"))
        self.assertEqual(breakdown["deductible_applied"], Decimal("2000.00"))
        self.assertEqual(breakdown["copay_share"], Decimal("2400.00"))
        self.assertEqual(breakdown["simulated_payout"], Decimal("21600.00"))

    def test_02_password_hashing(self):
        """Verify passwords are salted and hashed."""
        with self.app.app_context():
            user = User.query.filter_by(username="aasha").first()
            self.assertIsNotNone(user)
            self.assertTrue(user.password_hash.startswith("scrypt:") or user.password_hash.startswith("pbkdf2:"))
            self.assertTrue(check_password_hash(user.password_hash, "password123"))

    def test_03_role_authorization_and_cross_user_isolation(self):
        """Verify unauthorized access is blocked (FR01, FR02)."""
        with self.client:
            # Login as Aasha (policyholder)
            resp = self.client.post("/login", data={"username": "aasha", "password": "password123"})
            self.assertEqual(resp.status_code, 302)

            # Aasha tries to access Claims Officer Review Queue -> MUST BE 403 Forbidden
            officer_resp = self.client.get("/officer/queue")
            self.assertEqual(officer_resp.status_code, 403)

            # Aasha tries to access Admin Settlements -> MUST BE 403 Forbidden
            admin_resp = self.client.get("/admin/settlements")
            self.assertEqual(admin_resp.status_code, 403)

            # Aasha tries to view Bilal Khan's claim (#1003) -> MUST BE 403 Forbidden
            cross_claim_resp = self.client.get("/claims/1003")
            self.assertEqual(cross_claim_resp.status_code, 403)

    def test_04_future_admission_validation(self):
        """Verify future admission is rejected on submission (Case 1013 rule)."""
        with self.app.app_context():
            policy = db.session.get(Policy, 101)
            member = db.session.get(Member, 201)
            hospital = db.session.get(Hospital, 1)
            user = db.session.get(User, 1)

            future_date = datetime.date.today() + datetime.timedelta(days=10)
            valid, errors = validate_claim_data(
                policy=policy,
                member=member,
                hospital=hospital,
                user=user,
                claim_type="reimbursement",
                treatment_type="inpatient",
                admission_date=future_date,
                discharge_date=future_date,
                requested_amount=Decimal("15000.00"),
                is_submission=True,
            )
            self.assertFalse(valid)
            self.assertTrue(any("future" in err.lower() for err in errors))

    def test_05_treatment_type_plan_coverage_validation(self):
        """Verify plan without daycare rejects daycare claim (Case 1002 rule)."""
        with self.app.app_context():
            # Create a test plan strictly covering only 'inpatient'
            strict_plan = Plan(
                name="Strict Inpatient Plan",
                covered_treatment_types="inpatient",
                annual_limit_inr=Decimal("500000.00"),
                deductible_inr=Decimal("0.00"),
                copay_percent=Decimal("0.00"),
            )
            db.session.add(strict_plan)
            db.session.flush()

            self.assertEqual(strict_plan.covered_treatment_types, "inpatient")
            self.assertTrue(strict_plan.covers_treatment("inpatient"))
            self.assertFalse(strict_plan.covers_treatment("daycare"))

    def test_06_duplicate_detection(self):
        """Verify duplicate detection for matching member, hospital, and dates (Cases 1011 & 1012)."""
        with self.app.app_context():
            duplicates = check_potential_duplicates(
                member_id=211,
                hospital_id=5,
                admission_date=datetime.date(2026, 9, 25),
                discharge_date=datetime.date(2026, 9, 27),
                claim_type="reimbursement",
                exclude_claim_id=1011,
            )
            # Should find claim 1012
            self.assertGreaterEqual(len(duplicates), 1)
            self.assertEqual(duplicates[0].id, 1012)

    def test_07_officer_assignment_and_conflict_prevention(self):
        """Verify two officers cannot silently overwrite claim assignment (FR05)."""
        with self.client:
            # Login as Officer Meera
            self.client.post("/login", data={"username": "officer_meera", "password": "password123"})

            # Assign unassigned submitted claim #1007 to Meera
            resp = self.client.post("/officer/claim/1007/assign")
            self.assertEqual(resp.status_code, 302)

            with self.app.app_context():
                claim = db.session.get(Claim, 1007)
                self.assertEqual(claim.status, "in_review")
                self.assertEqual(claim.officer_user_id, 12)  # Officer Meera

            # Officer Rahul tries to re-assign claim #1007 -> Must be blocked
            self.client.get("/logout")
            self.client.post("/login", data={"username": "officer_rahul", "password": "password123"})
            conflict_resp = self.client.post("/officer/claim/1007/assign")
            self.assertEqual(conflict_resp.status_code, 302)

            with self.app.app_context():
                claim = db.session.get(Claim, 1007)
                # Officer MUST still be Meera (12), not Rahul (13)
                self.assertEqual(claim.officer_user_id, 12)

    def test_08_admin_settlement_and_terminal_state(self):
        """Verify admin simulated settlement and terminal state enforcement (FR07)."""
        with self.client:
            # Login as Administrator
            self.client.post("/login", data={"username": "admin_demo", "password": "password123"})

            # Settle approved claim #1003
            resp = self.client.post("/admin/settlements/1003/pay")
            self.assertEqual(resp.status_code, 302)

            with self.app.app_context():
                claim = db.session.get(Claim, 1003)
                self.assertEqual(claim.status, "paid")
                self.assertIsNotNone(claim.settlement)
                self.assertEqual(claim.settlement.payee_type, "hospital")  # Cashless -> hospital

            # Try to transition a paid claim back to draft or in_review -> not allowed
            reopen_resp = self.client.post("/claims/1003/submit")
            self.assertEqual(reopen_resp.status_code, 302)
            with self.app.app_context():
                claim = db.session.get(Claim, 1003)
                self.assertEqual(claim.status, "paid")  # Remains terminal


if __name__ == "__main__":
    unittest.main()

