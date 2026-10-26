-- =============================================================================
-- Health Insurance Claims Processing Simulator — Database Schema
-- Database: MySQL 8.0+ / utf8mb4
-- Version: 1.0 (Based on BRD Section 9)
-- =============================================================================

CREATE DATABASE IF NOT EXISTS `health_claims_simulator`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `health_claims_simulator`;

-- Disable foreign key checks during drop/recreate
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


-- -----------------------------------------------------------------------------
-- 1. HOSPITALS
-- Empanelled and non-empanelled hospital directory.
-- network_status: 1 = Network (Cashless Eligible), 0 = Non-Network
-- -----------------------------------------------------------------------------
CREATE TABLE `hospitals` (
    `id`             INT AUTO_INCREMENT PRIMARY KEY,
    `name`           VARCHAR(150) NOT NULL,
    `city`           VARCHAR(100) NOT NULL,
    `network_status` TINYINT(1) NOT NULL DEFAULT 0,
    `created_at`     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- -----------------------------------------------------------------------------
-- 2. PLANS
-- Fictional health insurance product terms and parameters.
-- covered_treatment_types: Pipe-separated values e.g. 'inpatient' or 'inpatient|daycare'
-- -----------------------------------------------------------------------------
CREATE TABLE `plans` (
    `id`                      INT AUTO_INCREMENT PRIMARY KEY,
    `name`                    VARCHAR(100) NOT NULL,
    `covered_treatment_types` VARCHAR(100) NOT NULL,
    `annual_limit_inr`        DECIMAL(12, 2) NOT NULL,
    `deductible_inr`          DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    `copay_percent`           DECIMAL(5, 2) NOT NULL DEFAULT 0.00,
    `created_at`              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- -----------------------------------------------------------------------------
-- 3. USERS
-- System accounts with role-based access control.
-- role ENUM: 'policyholder', 'hospital', 'claims_officer', 'admin'
-- hospital_id: Required for 'hospital' desk users, NULL for other roles.
-- -----------------------------------------------------------------------------
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


-- -----------------------------------------------------------------------------
-- 4. POLICIES
-- Master policy contracts owned by a policyholder user under an insurance plan.
-- -----------------------------------------------------------------------------
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


-- -----------------------------------------------------------------------------
-- 5. MEMBERS
-- Family members covered under a specific policy for whom claims may be filed.
-- -----------------------------------------------------------------------------
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


-- -----------------------------------------------------------------------------
-- 6. CLAIMS
-- Central claims table managing lifecycle states:
-- draft -> submitted -> in_review -> more_info -> submitted
--                    -> approved -> paid
--                    -> rejected
-- Indexes required by BRD: (policy_id, status), (officer_user_id, status)
-- -----------------------------------------------------------------------------
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


-- -----------------------------------------------------------------------------
-- 7. CLAIM_DOCUMENTS
-- Checklist metadata indicating whether required items are received or missing.
-- document_type: 'hospital_bill', 'discharge_summary'
-- checklist_status: 'received', 'missing'
-- -----------------------------------------------------------------------------
CREATE TABLE `claim_documents` (
    `id`               INT AUTO_INCREMENT PRIMARY KEY,
    `claim_id`         INT NOT NULL,
    `document_type`    VARCHAR(50) NOT NULL,
    `checklist_status` VARCHAR(30) NOT NULL DEFAULT 'missing',
    CONSTRAINT `fk_claim_docs_claim` FOREIGN KEY (`claim_id`)
        REFERENCES `claims` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX `idx_claim_docs_claim` (`claim_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- -----------------------------------------------------------------------------
-- 8. CLAIM_HISTORY
-- Immutable chronological audit trail of state transitions, actors, and notes.
-- Index required by BRD: (claim_id, timestamp)
-- -----------------------------------------------------------------------------
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


-- -----------------------------------------------------------------------------
-- 9. SETTLEMENTS
-- Simulated final payment records created by Administrator for approved claims.
-- claim_id is UNIQUE (at most one settlement per approved claim).
-- payee_type: 'hospital' (cashless) or 'policyholder' (reimbursement)
-- -----------------------------------------------------------------------------
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
