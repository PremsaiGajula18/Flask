import csv
import datetime
from decimal import Decimal
import os
import sys

from werkzeug.security import generate_password_hash

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

DATASET_DIR = os.path.join(os.path.dirname(__file__), "health_claims_synthetic_dataset")
DEFAULT_PASSWORD = "password123"


def parse_date(date_str: str) -> datetime.date:
    if not date_str or not date_str.strip():
        return None
    return datetime.datetime.strptime(date_str.strip(), "%Y-%m-%d").date()


def parse_decimal(val_str: str) -> Decimal:
    if not val_str or not val_str.strip():
        return None
    return Decimal(val_str.strip())


def parse_int(val_str: str) -> int:
    if not val_str or not val_str.strip():
        return None
    return int(float(val_str.strip()))


def ensure_mysql_database():
    from config import Config
    import pymysql
    try:
        conn = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            port=int(Config.DB_PORT),
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.commit()
        conn.close()
        print(f"Verified MySQL Server connection: database `{Config.DB_NAME}` is ready.")
    except Exception as e:
        print(f"ERROR connecting to MySQL Server ({Config.DB_HOST}:{Config.DB_PORT}): {e}")
        print("Please ensure MySQL service is running ('net start MYSQL80').")
        raise


def seed_database():
    ensure_mysql_database()
    app = create_app()
    with app.app_context():
        print("Dropping existing tables and recreating schema...")
        db.drop_all()
        db.create_all()

        print(f"Loading synthetic data from: {DATASET_DIR}")

        # 1. Hospitals
        print("Importing hospitals.csv...")
        with open(os.path.join(DATASET_DIR, "hospitals.csv"), "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                hospital = Hospital(
                    id=parse_int(row["hospital_id"]),
                    name=row["name"].strip(),
                    city=row["city"].strip(),
                    network_status=bool(parse_int(row["network_status"])),
                )
                db.session.add(hospital)
        db.session.commit()

        # 2. Plans
        print("Importing plans.csv...")
        with open(os.path.join(DATASET_DIR, "plans.csv"), "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                plan = Plan(
                    id=parse_int(row["plan_id"]),
                    name=row["plan_name"].strip(),
                    covered_treatment_types=row["covered_treatment_types"].strip(),
                    annual_limit_inr=parse_decimal(row["annual_limit_inr"]),
                    deductible_inr=parse_decimal(row["deductible_inr"]),
                    copay_percent=parse_decimal(row["copay_percent"]),
                )
                db.session.add(plan)
        db.session.commit()

        # 3. Users
        print(f"Importing users.csv (Hashing all passwords to '{DEFAULT_PASSWORD}')...")
        hashed_pw = generate_password_hash(DEFAULT_PASSWORD)
        with open(os.path.join(DATASET_DIR, "users.csv"), "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                user = User(
                    id=parse_int(row["user_id"]),
                    username=row["username"].strip(),
                    password_hash=hashed_pw,
                    display_name=row["display_name"].strip(),
                    role=row["role"].strip(),
                    hospital_id=parse_int(row["hospital_id"]) if row.get("hospital_id") else None,
                )
                db.session.add(user)
        db.session.commit()

        # 4. Policies
        print("Importing policies.csv...")
        with open(os.path.join(DATASET_DIR, "policies.csv"), "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                policy = Policy(
                    id=parse_int(row["policy_id"]),
                    holder_user_id=parse_int(row["holder_user_id"]),
                    plan_id=parse_int(row["plan_id"]),
                    start_date=parse_date(row["start_date"]),
                    end_date=parse_date(row["end_date"]),
                    status=row["status"].strip(),
                )
                db.session.add(policy)
        db.session.commit()

        # 5. Members
        print("Importing members.csv...")
        with open(os.path.join(DATASET_DIR, "members.csv"), "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                member = Member(
                    id=parse_int(row["member_id"]),
                    policy_id=parse_int(row["policy_id"]),
                    display_name=row["display_name"].strip(),
                    relationship=row["relationship"].strip(),
                )
                db.session.add(member)
        db.session.commit()

        # 6. Claims
        print("Importing claims.csv...")
        with open(os.path.join(DATASET_DIR, "claims.csv"), "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                claim = Claim(
                    id=parse_int(row["claim_id"]),
                    policy_id=parse_int(row["policy_id"]),
                    member_id=parse_int(row["member_id"]),
                    hospital_id=parse_int(row["hospital_id"]),
                    claim_type=row["claim_type"].strip(),
                    treatment_type=row["treatment_type"].strip(),
                    admission_date=parse_date(row["admission_date"]),
                    discharge_date=parse_date(row["discharge_date"]),
                    requested_amount_inr=parse_decimal(row["requested_amount_inr"]),
                    status=row["status"].strip(),
                    eligible_amount_inr=parse_decimal(row.get("eligible_amount_inr")),
                    officer_user_id=parse_int(row.get("officer_user_id")),
                    payment_recorded_date=parse_date(row.get("payment_recorded_date")),
                )
                db.session.add(claim)
        db.session.commit()

        # 7. Claim Documents
        print("Importing claim_documents.csv...")
        with open(os.path.join(DATASET_DIR, "claim_documents.csv"), "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                doc = ClaimDocument(
                    claim_id=parse_int(row["claim_id"]),
                    document_type=row["document_type"].strip(),
                    checklist_status=row["checklist_status"].strip(),
                )
                db.session.add(doc)
        db.session.commit()

        # 8. Claim History
        print("Importing claim_history.csv...")
        with open(os.path.join(DATASET_DIR, "claim_history.csv"), "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                hist = ClaimHistory(
                    claim_id=parse_int(row["claim_id"]),
                    sequence_no=parse_int(row["sequence_no"]),
                    from_status=row["from_status"].strip() if row.get("from_status") else None,
                    to_status=row["to_status"].strip(),
                    actor_user_id=parse_int(row.get("actor_user_id")),
                    note=row["note"].strip() if row.get("note") else None,
                    event_date=parse_date(row.get("event_date")),
                    timestamp=datetime.datetime.combine(
                        parse_date(row.get("event_date")) or datetime.date.today(),
                        datetime.time(12, 0)
                    ),
                )
                db.session.add(hist)
        db.session.commit()

        # 9. Settlements
        print("Importing settlements.csv...")
        with open(os.path.join(DATASET_DIR, "settlements.csv"), "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                settlement = Settlement(
                    claim_id=parse_int(row["claim_id"]),
                    payee_type=row["payee_type"].strip(),
                    amount_inr=parse_decimal(row["amount_inr"]),
                    recorded_by_user_id=parse_int(row["recorded_by_user_id"]),
                    recorded_date=parse_date(row["recorded_date"]),
                )
                db.session.add(settlement)
        db.session.commit()

        print("\nAll 9 dataset tables imported successfully!")
        print(f"Users imported: {User.query.count()}")
        print(f"Hospitals imported: {Hospital.query.count()}")
        print(f"Plans imported: {Plan.query.count()}")
        print(f"Policies imported: {Policy.query.count()}")
        print(f"Claims imported: {Claim.query.count()}")
        print(f"Settlements imported: {Settlement.query.count()}")


if __name__ == "__main__":
    seed_database()
