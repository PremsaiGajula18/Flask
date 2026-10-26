-- =============================================================================
-- Health Insurance Claims Processing Simulator — Complete SQL Practice Script
-- Includes: Full Database Creation, 9 Table Schemas, Sample/Practice Data,
-- and Verification Queries for Hands-on Learning.
-- =============================================================================

CREATE DATABASE IF NOT EXISTS `health_claims_simulator`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `health_claims_simulator`;

-- Disable Foreign Key checks while dropping existing tables
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS `settlements`;
DROP TABLE IF EXISTS `claim_history`;
DROP TABLE IF EXISTS `claim_documents`;
DROP TABLE IF EXISTS `claims`;
DROP TABLE IF EXISTS `members`;
DROP TABLE IF EXISTS `policies`;
DROP TABLE IF EXISTS `users`;
DROP TABLE IF EXISTS `plans`;
DROP TABLE IF EXISTS `hospitals`;
SET FOREIGN_KEY_CHECKS = 1;


-- =============================================================================
-- 1. TABLE: hospitals
-- Purpose: Hospital directory. network_status=1 allows Cashless claims.
-- =============================================================================
CREATE TABLE `hospitals` (
    `id`             INT AUTO_INCREMENT PRIMARY KEY,
    `name`           VARCHAR(150) NOT NULL,
    `city`           VARCHAR(100) NOT NULL,
    `network_status` TINYINT(1) NOT NULL DEFAULT 0,
    `created_at`     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sample / Practice Data for hospitals
INSERT INTO `hospitals` (`id`, `name`, `city`, `network_status`) VALUES
(1, 'CityCare Hospital', 'Puttaparthi', 1),   -- Empanelled Network Hospital
(2, 'Lotus Medical Centre', 'Anantapur', 1),    -- Empanelled Network Hospital
(3, 'Green Valley Hospital', 'Kadiri', 0),      -- Non-Network Hospital (Reimbursement only)
(4, 'Sunrise Multispeciality', 'Dharmavaram', 1), -- Empanelled Network Hospital
(5, 'Apex Healthcare', 'Hindupur', 0);          -- Non-Network Hospital


-- =============================================================================
-- 2. TABLE: plans
-- Purpose: Master insurance products defining financial limits and coverage rules.
-- =============================================================================
CREATE TABLE `plans` (
    `id`                      INT AUTO_INCREMENT PRIMARY KEY,
    `name`                    VARCHAR(100) NOT NULL,
    `covered_treatment_types` VARCHAR(100) NOT NULL,
    `annual_limit_inr`        DECIMAL(12, 2) NOT NULL,
    `deductible_inr`          DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    `copay_percent`           DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
    `created_at`              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sample / Practice Data for plans
INSERT INTO `plans` (`id`, `name`, `covered_treatment_types`, `annual_limit_inr`, `deductible_inr`, `copay_percent`) VALUES
(1, 'Essential Care', 'inpatient', 100000.00, 2000.00, 10.00),         -- Only inpatient, 10% copay
(2, 'Plus Care', 'inpatient|daycare', 200000.00, 1000.00, 5.00),        -- Both inpatient & daycare, 5% copay
(3, 'Family Care', 'inpatient|daycare', 300000.00, 1500.00, 10.00);     -- High limit, 10% copay


-- =============================================================================
-- 3. TABLE: users
-- Purpose: System accounts with 4 roles (policyholder, hospital, claims_officer, admin).
-- Note: Password hash below corresponds to 'password123'
-- =============================================================================
CREATE TABLE `users` (
    `id`            INT AUTO_INCREMENT PRIMARY KEY,
    `username`      VARCHAR(80) NOT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `display_name`  VARCHAR(120) NOT NULL,
    `role`          VARCHAR(30) NOT NULL,
    `hospital_id`   INT NULL,
    `created_at`    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `uq_users_username` UNIQUE (`username`),
    CONSTRAINT `fk_users_hospital` FOREIGN KEY (`hospital_id`)
        REFERENCES `hospitals` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sample / Practice Data for users (password: 'password123' hashed with Werkzeug scrypt)
INSERT INTO `users` (`id`, `username`, `password_hash`, `display_name`, `role`, `hospital_id`) VALUES
-- Policyholders (Customers)
(1, 'aasha', 'scrypt:32768:8:1$0iJqP1p7aJt6mK8p$9b9963e6f98c8c4a45f949c8148b6f378d3886532d84db57e514f7bdfce29eb3a59599525c34e0084511d15db62208170c0c6d70ef24559c5d1e679a6d96ff61', 'Aasha Rao', 'policyholder', NULL),
(2, 'bilal', 'scrypt:32768:8:1$0iJqP1p7aJt6mK8p$9b9963e6f98c8c4a45f949c8148b6f378d3886532d84db57e514f7bdfce29eb3a59599525c34e0084511d15db62208170c0c6d70ef24559c5d1e679a6d96ff61', 'Bilal Khan', 'policyholder', NULL),
(3, 'chitra', 'scrypt:32768:8:1$0iJqP1p7aJt6mK8p$9b9963e6f98c8c4a45f949c8148b6f378d3886532d84db57e514f7bdfce29eb3a59599525c34e0084511d15db62208170c0c6d70ef24559c5d1e679a6d96ff61', 'Chitra Devi', 'policyholder', NULL),
(4, 'dev', 'scrypt:32768:8:1$0iJqP1p7aJt6mK8p$9b9963e6f98c8c4a45f949c8148b6f378d3886532d84db57e514f7bdfce29eb3a59599525c34e0084511d15db62208170c0c6d70ef24559c5d1e679a6d96ff61', 'Dev Kumar', 'policyholder', NULL),

-- Hospital Desks (Linked to specific hospitals)
(9, 'city_hospital', 'scrypt:32768:8:1$0iJqP1p7aJt6mK8p$9b9963e6f98c8c4a45f949c8148b6f378d3886532d84db57e514f7bdfce29eb3a59599525c34e0084511d15db62208170c0c6d70ef24559c5d1e679a6d96ff61', 'CityCare Desk', 'hospital', 1),
(10, 'lotus_hospital', 'scrypt:32768:8:1$0iJqP1p7aJt6mK8p$9b9963e6f98c8c4a45f949c8148b6f378d3886532d84db57e514f7bdfce29eb3a59599525c34e0084511d15db62208170c0c6d70ef24559c5d1e679a6d96ff61', 'Lotus Desk', 'hospital', 2),

-- Claims Officers (Insurance Adjudicators)
(12, 'officer_meera', 'scrypt:32768:8:1$0iJqP1p7aJt6mK8p$9b9963e6f98c8c4a45f949c8148b6f378d3886532d84db57e514f7bdfce29eb3a59599525c34e0084511d15db62208170c0c6d70ef24559c5d1e679a6d96ff61', 'Meera Shah', 'claims_officer', NULL),
(13, 'officer_rahul', 'scrypt:32768:8:1$0iJqP1p7aJt6mK8p$9b9963e6f98c8c4a45f949c8148b6f378d3886532d84db57e514f7bdfce29eb3a59599525c34e0084511d15db62208170c0c6d70ef24559c5d1e679a6d96ff61', 'Rahul Sen', 'claims_officer', NULL),

-- Administrator
(14, 'admin_demo', 'scrypt:32768:8:1$0iJqP1p7aJt6mK8p$9b9963e6f98c8c4a45f949c8148b6f378d3886532d84db57e514f7bdfce29eb3a59599525c34e0084511d15db62208170c0c6d70ef24559c5d1e679a6d96ff61', 'Demo Administrator', 'admin', NULL);


-- =============================================================================
-- 4. TABLE: policies
-- Purpose: Policy contracts issued to policyholders under specific plans.
-- =============================================================================
CREATE TABLE `policies` (
    `id`             INT AUTO_INCREMENT PRIMARY KEY,
    `holder_user_id` INT NOT NULL,
    `plan_id`        INT NOT NULL,
    `start_date`     DATE NOT NULL,
    `end_date`       DATE NOT NULL,
    `status`         VARCHAR(30) NOT NULL DEFAULT 'active',
    `created_at`     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_policies_holder` FOREIGN KEY (`holder_user_id`)
        REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_policies_plan` FOREIGN KEY (`plan_id`)
        REFERENCES `plans` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX `idx_policies_holder` (`holder_user_id`),
    INDEX `idx_policies_plan` (`plan_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sample / Practice Data for policies
INSERT INTO `policies` (`id`, `holder_user_id`, `plan_id`, `start_date`, `end_date`, `status`) VALUES
(101, 1, 1, '2026-01-01', '2026-12-31', 'active'), -- Aasha Rao, Essential Care
(102, 2, 2, '2026-04-01', '2027-03-31', 'active'), -- Bilal Khan, Plus Care
(103, 3, 3, '2026-01-01', '2026-12-31', 'active'), -- Chitra Devi, Family Care
(104, 4, 1, '2025-01-01', '2025-12-31', 'expired'); -- Dev Kumar, Expired Policy (for testing Case 1006)


-- =============================================================================
-- 5. TABLE: members
-- Purpose: Covered family members under each policy.
-- =============================================================================
CREATE TABLE `members` (
    `id`           INT AUTO_INCREMENT PRIMARY KEY,
    `policy_id`    INT NOT NULL,
    `display_name` VARCHAR(120) NOT NULL,
    `relationship` VARCHAR(50) NOT NULL,
    `created_at`   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_members_policy` FOREIGN KEY (`policy_id`)
        REFERENCES `policies` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX `idx_members_policy` (`policy_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sample / Practice Data for members
INSERT INTO `members` (`id`, `policy_id`, `display_name`, `relationship`) VALUES
(201, 101, 'Aasha Rao', 'self'),
(202, 101, 'Nikhil Rao', 'spouse'),
(203, 102, 'Bilal Khan', 'self'),
(204, 103, 'Chitra Devi', 'self'),
(205, 103, 'Arun Devi', 'child'),
(206, 104, 'Dev Kumar', 'self');


-- =============================================================================
-- 6. TABLE: claims
-- Purpose: The central claim records tracking status lifecycle and amounts.
-- Includes: Approved, Paid, In Review, Rejected, More Info, and Duplicate examples.
-- =============================================================================
CREATE TABLE `claims` (
    `id`                    INT AUTO_INCREMENT PRIMARY KEY,
    `policy_id`             INT NOT NULL,
    `member_id`             INT NOT NULL,
    `hospital_id`           INT NOT NULL,
    `claim_type`            VARCHAR(20) NOT NULL, -- 'cashless', 'reimbursement'
    `treatment_type`        VARCHAR(20) NOT NULL, -- 'inpatient', 'daycare'
    `admission_date`        DATE NOT NULL,
    `discharge_date`        DATE NOT NULL,
    `requested_amount_inr`  DECIMAL(12, 2) NOT NULL,
    `status`                VARCHAR(30) NOT NULL DEFAULT 'draft',
    `eligible_amount_inr`   DECIMAL(12, 2) NULL,
    `officer_user_id`       INT NULL,
    `payment_recorded_date` DATE NULL,
    `created_at`            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT `fk_claims_policy` FOREIGN KEY (`policy_id`)
        REFERENCES `policies` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_claims_member` FOREIGN KEY (`member_id`)
        REFERENCES `members` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_claims_hospital` FOREIGN KEY (`hospital_id`)
        REFERENCES `hospitals` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_claims_officer` FOREIGN KEY (`officer_user_id`)
        REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX `idx_claims_policy_status` (`policy_id`, `status`),
    INDEX `idx_claims_officer_status` (`officer_user_id`, `status`),
    INDEX `idx_claims_hospital` (`hospital_id`),
    INDEX `idx_claims_member` (`member_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sample / Practice Data for claims (Includes all special BRD edge cases)
INSERT INTO `claims` (`id`, `policy_id`, `member_id`, `hospital_id`, `claim_type`, `treatment_type`, `admission_date`, `discharge_date`, `requested_amount_inr`, `status`, `eligible_amount_inr`, `officer_user_id`, `payment_recorded_date`) VALUES
-- Case 1001: Paid cashless claim baseline
(1001, 101, 201, 1, 'cashless', 'inpatient', '2026-08-10', '2026-08-13', 28000.00, 'paid', 26000.00, 12, '2026-08-14'),

-- Case 1002: Rejected claim (Daycare requested on Essential Care which only covers inpatient)
(1002, 101, 202, 3, 'reimbursement', 'daycare', '2026-09-12', '2026-09-12', 14000.00, 'rejected', 0.00, 12, NULL),

-- Case 1003: Approved cashless claim (Awaiting Admin simulated settlement)
(1003, 102, 203, 2, 'cashless', 'daycare', '2026-09-20', '2026-09-20', 18000.00, 'approved', 16000.00, 13, NULL),

-- Case 1004: In review by Officer Meera
(1004, 103, 204, 1, 'cashless', 'inpatient', '2026-10-02', '2026-10-05', 42000.00, 'in_review', NULL, 12, NULL),

-- Case 1005: More info requested (Missing discharge summary)
(1005, 103, 205, 2, 'reimbursement', 'inpatient', '2026-10-03', '2026-10-06', 35000.00, 'more_info', NULL, 13, NULL),

-- Case 1006: Rejected claim (Treatment during expired policy date window)
(1006, 104, 206, 1, 'reimbursement', 'inpatient', '2026-07-01', '2026-07-03', 22000.00, 'rejected', 0.00, 12, NULL),

-- Case 1007: Submitted & Unassigned claim (Ready for officer assignment)
(1007, 101, 201, 1, 'cashless', 'inpatient', '2026-10-10', '2026-10-14', 85000.00, 'submitted', NULL, NULL, NULL),

-- Case 1011 & 1012: Intentional Duplicate Event Pair (Same member, hospital, and dates!)
(1011, 102, 203, 2, 'reimbursement', 'inpatient', '2026-09-25', '2026-09-27', 60000.00, 'more_info', NULL, 12, NULL),
(1012, 102, 203, 2, 'reimbursement', 'inpatient', '2026-09-25', '2026-09-27', 60000.00, 'submitted', NULL, NULL, NULL),

-- Case 1013: Draft with future admission date (submission blocked until date is valid)
(1013, 102, 203, 1, 'cashless', 'inpatient', '2026-10-25', '2026-10-28', 45000.00, 'draft', NULL, NULL, NULL);


-- =============================================================================
-- 7. TABLE: claim_documents
-- Purpose: Verification checklist metadata (hospital_bill, discharge_summary).
-- =============================================================================
CREATE TABLE `claim_documents` (
    `id`               INT AUTO_INCREMENT PRIMARY KEY,
    `claim_id`         INT NOT NULL,
    `document_type`    VARCHAR(50) NOT NULL,
    `checklist_status` VARCHAR(30) NOT NULL DEFAULT 'missing',
    CONSTRAINT `fk_claim_docs_claim` FOREIGN KEY (`claim_id`)
        REFERENCES `claims` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX `idx_claim_docs_claim` (`claim_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sample / Practice Data for claim_documents
INSERT INTO `claim_documents` (`id`, `claim_id`, `document_type`, `checklist_status`) VALUES
-- Claim 1001: All documents received
(1, 1001, 'hospital_bill', 'received'),
(2, 1001, 'discharge_summary', 'received'),

-- Claim 1003: Bill received, summary received
(3, 1003, 'hospital_bill', 'received'),
(4, 1003, 'discharge_summary', 'received'),

-- Claim 1004: In review, bill received
(5, 1004, 'hospital_bill', 'received'),
(6, 1004, 'discharge_summary', 'missing'),

-- Claim 1005: Missing discharge summary (triggers more_info status)
(7, 1005, 'hospital_bill', 'received'),
(8, 1005, 'discharge_summary', 'missing');


-- =============================================================================
-- 8. TABLE: claim_history
-- Purpose: Immutable chronological audit trail of all actions and notes.
-- =============================================================================
CREATE TABLE `claim_history` (
    `id`            INT AUTO_INCREMENT PRIMARY KEY,
    `claim_id`      INT NOT NULL,
    `sequence_no`   INT NOT NULL DEFAULT 1,
    `from_status`   VARCHAR(30) NULL,
    `to_status`     VARCHAR(30) NOT NULL,
    `actor_user_id` INT NULL,
    `note`          TEXT NULL,
    `timestamp`     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `event_date`    DATE NULL,
    CONSTRAINT `fk_claim_hist_claim` FOREIGN KEY (`claim_id`)
        REFERENCES `claims` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_claim_hist_actor` FOREIGN KEY (`actor_user_id`)
        REFERENCES `users` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX `idx_claim_history_claim_time` (`claim_id`, `timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sample / Practice Data for claim_history
INSERT INTO `claim_history` (`id`, `claim_id`, `sequence_no`, `from_status`, `to_status`, `actor_user_id`, `note`, `event_date`) VALUES
-- Claim 1001 full lifecycle history
(1, 1001, 1, 'draft', 'submitted', 9, 'Initial cashless pre-auth submitted by CityCare desk.', '2026-08-11'),
(2, 1001, 2, 'submitted', 'in_review', 12, 'Assigned to Officer Meera for clinical review.', '2026-08-12'),
(3, 1001, 3, 'in_review', 'approved', 12, 'Approved ₹26,000 eligible charges. ₹2,000 non-medical fees deducted.', '2026-08-13'),
(4, 1001, 4, 'approved', 'paid', 14, 'Simulated settlement of ₹21,600 paid to CityCare Hospital.', '2026-08-14'),

-- Claim 1002 rejection history
(5, 1002, 1, 'draft', 'submitted', 1, 'Submitted reimbursement claim for daycare.', '2026-09-12'),
(6, 1002, 2, 'submitted', 'in_review', 12, 'Assigned to Officer Meera.', '2026-09-12'),
(7, 1002, 3, 'in_review', 'rejected', 12, 'Rejected: Daycare is not covered under Essential Care plan.', '2026-09-13'),

-- Claim 1003 approval history
(8, 1003, 1, 'draft', 'submitted', 10, 'Cashless request submitted by Lotus desk.', '2026-09-20'),
(9, 1003, 2, 'submitted', 'in_review', 13, 'Assigned to Officer Rahul.', '2026-09-20'),
(10, 1003, 3, 'in_review', 'approved', 13, 'Approved for eligible amount ₹16,000.', '2026-09-21'),

-- Claim 1005 more_info cycle history
(11, 1005, 1, 'draft', 'submitted', 3, 'Reimbursement claim submitted by Chitra.', '2026-10-03'),
(12, 1005, 2, 'submitted', 'in_review', 13, 'Assigned to Officer Rahul.', '2026-10-04'),
(13, 1005, 3, 'in_review', 'more_info', 13, 'Discharge summary missing. Please provide procedure notes.', '2026-10-05');


-- =============================================================================
-- 9. TABLE: settlements
-- Purpose: Final simulated payout records (at most 1 settlement per claim).
-- =============================================================================
CREATE TABLE `settlements` (
    `id`                  INT AUTO_INCREMENT PRIMARY KEY,
    `claim_id`            INT NOT NULL,
    `payee_type`          VARCHAR(30) NOT NULL,
    `amount_inr`          DECIMAL(12, 2) NOT NULL,
    `recorded_by_user_id` INT NOT NULL,
    `recorded_date`       DATE NOT NULL,
    CONSTRAINT `uq_settlements_claim` UNIQUE (`claim_id`),
    CONSTRAINT `fk_settlements_claim` FOREIGN KEY (`claim_id`)
        REFERENCES `claims` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_settlements_user` FOREIGN KEY (`recorded_by_user_id`)
        REFERENCES `users` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sample / Practice Data for settlements
INSERT INTO `settlements` (`id`, `claim_id`, `payee_type`, `amount_inr`, `recorded_by_user_id`, `recorded_date`) VALUES
-- Claim 1001: Payout calculated as: (26000 - 2000 deductible) * (1 - 0.10 copay) = 21600.00
(1, 1001, 'hospital', 21600.00, 14, '2026-08-14');
