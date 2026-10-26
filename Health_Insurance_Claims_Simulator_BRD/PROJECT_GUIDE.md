# Health Insurance Claims Processing Simulator

An individual full-stack educational simulator built exclusively with **Python, Flask, SQLAlchemy 2.0, Jinja2, Bootstrap 5, and MySQL Server 8.0** based on the Business Requirements Document (BRD v1.0).

---

## 1. Quick Start with MySQL Server

### Step 1: Ensure MySQL Service is Running
Start your local MySQL service (e.g. from an Administrator Command Prompt or `services.msc`):
```cmd
net start MYSQL80
```

### Step 2: Seed the MySQL Database
Run the database seed script to auto-create the `health_claims_simulator` database and import all 9 CSV files with hashed passwords:
```powershell
cd C:\Flask\Health_Insurance_Claims_Simulator_BRD
python seed_data.py
```

### Step 3: Start the Flask Application
```powershell
python run.py
```
Open your browser and navigate to: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 2. MySQL Configuration
Database settings in `config.py`:
* **Host:** `127.0.0.1:3306`
* **User:** `root`
* **Password:** `premsai444@123`
* **Database Name:** `health_claims_simulator`
* **Driver:** `PyMySQL` (`mysql+pymysql`)

---

## 3. Demo Accounts & Credentials
All demo accounts use the standard password: `password123`

| Role | Username | Display Name | Organization / Scope |
| :--- | :--- | :--- | :--- |
| **Policyholder** | `aasha` | Aasha Rao | Holds Policy #101 (Essential Care) |
| **Policyholder** | `bilal` | Bilal Khan | Holds Policy #102 (Plus Care) |
| **Policyholder** | `chitra` | Chitra Devi | Holds Policy #103 (Family Care) |
| **Hospital Desk** | `city_hospital` | CityCare Desk | Empanelled Network Hospital #1 |
| **Hospital Desk** | `lotus_hospital` | Lotus Desk | Empanelled Network Hospital #2 |
| **Hospital Desk** | `green_hospital` | Green Valley Desk | Non-Network Hospital #3 |
| **Claims Officer** | `officer_meera` | Meera Shah | Insurance Claims Adjudication |
| **Claims Officer** | `officer_rahul` | Rahul Sen | Insurance Claims Adjudication |
| **Administrator** | `admin_demo` | Demo Administrator | Settlement Payouts & Reference Data |

*(Tip: The login page includes quick-fill buttons for instant role switching during demonstrations!)*

---

## 4. Key Pre-Seeded Scenarios (BRD Section 16)

* **Claim #1001 (Paid):** Cashless claim at CityCare Hospital, ₹28,000 requested, ₹26,000 eligible, Paid ₹21,600 to Hospital.
* **Claim #1002 (Rejected):** Daycare procedure filed under Essential Care plan (covers only Inpatient) $\rightarrow$ Demonstrates treatment coverage rule.
* **Claim #1003 (Approved):** Cashless claim at Lotus Medical Centre for ₹16,000 eligible amount $\rightarrow$ Ready for Admin to click "Record Settlement".
* **Claim #1004 (In Review):** Currently in review by Officer Meera.
* **Claim #1005 (More Info):** Reimbursement claim with missing discharge summary $\rightarrow$ Submitter updates checklist and resubmits.
* **Claim #1006 (Rejected):** Admission date fell outside policy coverage dates $\rightarrow$ Demonstrates active policy date rule.
* **Claim #1007 (Submitted):** Unassigned claim in the Claims Officer work queue.
* **Claim #1011 & #1012 (Duplicate Warning):** Same member, hospital, and admission dates $\rightarrow$ Triggers visible amber review warning.
* **Claim #1013 (Future Admission Draft):** Draft with future admission date $\rightarrow$ Submission is blocked until date is valid.

---

## 5. Automated Test Suite
Run the test suite against MySQL to verify all business rules, role security boundaries, race condition prevention, and financial formulas:
```powershell
python test_app.py
```
Outputs:
```text
Ran 8 tests in 1.408s - OK
```
