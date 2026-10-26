-- ===================================================================================
-- CAREPULSE HEALTH INSURANCE CLAIMS SYSTEM - MYSQL TRIGGERS SUITE
-- Database: health_claims_simulator
-- 
-- This script implements enterprise MySQL Trigger concepts:
-- 1. BEFORE INSERT triggers (Data Integrity & Validation)
-- 2. BEFORE UPDATE triggers (Business Rules & Immutability Enforcement)
-- 3. AFTER INSERT triggers  (State Synchronization & Workflow Escalation)
-- 4. AFTER UPDATE triggers  (Automated Compliance Audit Logging)
-- ===================================================================================

USE health_claims_simulator;

-- -----------------------------------------------------------------------------------
-- STEP 1: Create Dedicated Audit Table for Trigger-based Activity Tracking
-- -----------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `claims_audit_log` (
    `audit_id` INT AUTO_INCREMENT PRIMARY KEY,
    `claim_id` INT NOT NULL,
    `action_event` VARCHAR(30) NOT NULL COMMENT 'INSERT, UPDATE, DELETE',
    `old_status` VARCHAR(40) NULL,
    `new_status` VARCHAR(40) NULL,
    `old_requested_amount` DECIMAL(12, 2) NULL,
    `new_requested_amount` DECIMAL(12, 2) NULL,
    `old_eligible_amount` DECIMAL(12, 2) NULL,
    `new_eligible_amount` DECIMAL(12, 2) NULL,
    `actor_user_id` INT NULL,
    `notes` VARCHAR(500) NULL,
    `logged_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_audit_claim` (`claim_id`),
    INDEX `idx_audit_logged_at` (`logged_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER $$

-- -----------------------------------------------------------------------------------
-- TRIGGER 1: BEFORE INSERT ON claims (Clinical & Financial Data Integrity)
-- Purpose:
--   - Rejects negative or zero requested claim amounts.
--   - Rejects future admission dates.
--   - Rejects discharge dates earlier than admission date.
-- -----------------------------------------------------------------------------------
DROP TRIGGER IF EXISTS `trg_claims_before_insert`$$
CREATE TRIGGER `trg_claims_before_insert`
BEFORE INSERT ON `claims`
FOR EACH ROW
BEGIN
    -- 1. Validate Requested Amount
    IF NEW.requested_amount_inr <= 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Violation: Requested claim amount must be strictly greater than 0.';
    END IF;

    -- 2. Validate Admission Date (Cannot be in the future)
    IF NEW.admission_date > CURDATE() THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Violation: Hospital admission date cannot be in the future.';
    END IF;

    -- 3. Validate Discharge Date (Cannot be earlier than admission date)
    IF NEW.discharge_date < NEW.admission_date THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Violation: Hospital discharge date cannot precede admission date.';
    END IF;
END$$

-- -----------------------------------------------------------------------------------
-- TRIGGER 2: BEFORE UPDATE ON claims (Workflow Integrity & Immutability Rules)
-- Purpose:
--   - Prevents altering requested claim amount once a claim has been approved or paid.
--   - Ensures eligible approved amount cannot exceed the requested amount.
-- -----------------------------------------------------------------------------------
DROP TRIGGER IF EXISTS `trg_claims_before_update`$$
CREATE TRIGGER `trg_claims_before_update`
BEFORE UPDATE ON `claims`
FOR EACH ROW
BEGIN
    -- 1. Financial immutability: Amount cannot be changed once claim is approved or paid
    IF (OLD.status IN ('approved', 'paid')) AND (OLD.requested_amount_inr <> NEW.requested_amount_inr) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Violation: Requested claim amount is locked and cannot be modified after approval or settlement.';
    END IF;

    -- 2. Eligible amount sanity check
    IF NEW.eligible_amount_inr IS NOT NULL AND NEW.eligible_amount_inr > NEW.requested_amount_inr THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Violation: Approved eligible amount cannot exceed the requested claim amount.';
    END IF;
END$$

-- -----------------------------------------------------------------------------------
-- TRIGGER 3: BEFORE INSERT & BEFORE UPDATE ON policies (Policy Lifecycle Automation)
-- Purpose:
--   - Automatically marks policy status as 'expired' if end_date has passed.
--   - Validates that policy end date is after start date.
-- -----------------------------------------------------------------------------------
DROP TRIGGER IF EXISTS `trg_policies_before_insert`$$
CREATE TRIGGER `trg_policies_before_insert`
BEFORE INSERT ON `policies`
FOR EACH ROW
BEGIN
    -- 1. Date range consistency
    IF NEW.end_date <= NEW.start_date THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Violation: Policy end date must be strictly after the start date.';
    END IF;

    -- 2. Auto-expire if end date is in the past
    IF NEW.end_date < CURDATE() THEN
        SET NEW.status = 'expired';
    END IF;
END$$

DROP TRIGGER IF EXISTS `trg_policies_before_update`$$
CREATE TRIGGER `trg_policies_before_update`
BEFORE UPDATE ON `policies`
FOR EACH ROW
BEGIN
    IF NEW.end_date < CURDATE() AND NEW.status = 'active' THEN
        SET NEW.status = 'expired';
    END IF;
END$$

-- -----------------------------------------------------------------------------------
-- TRIGGER 4: BEFORE INSERT ON settlements (Financial Payout Protection)
-- Purpose:
--   - Validates that settlement payout amount is positive.
--   - Ensures payout does not exceed the approved eligible amount of the claim.
--   - Ensures payout can only be generated for claims in 'approved' status.
-- -----------------------------------------------------------------------------------
DROP TRIGGER IF EXISTS `trg_settlements_before_insert`$$
CREATE TRIGGER `trg_settlements_before_insert`
BEFORE INSERT ON `settlements`
FOR EACH ROW
BEGIN
    DECLARE v_claim_status VARCHAR(40);
    DECLARE v_eligible_amount DECIMAL(12, 2);

    -- 1. Positive amount check
    IF NEW.amount_inr <= 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Violation: Settlement disbursement amount must be positive.';
    END IF;

    -- 2. Fetch parent claim status and approved eligible amount
    SELECT `status`, `eligible_amount_inr`
      INTO v_claim_status, v_eligible_amount
      FROM `claims`
     WHERE `id` = NEW.claim_id;

    -- 3. Verify claim is currently approved
    IF v_claim_status != 'approved' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Violation: Payout cannot be recorded for a claim that is not in approved status.';
    END IF;

    -- 4. Payout cannot exceed approved coverage
    IF NEW.amount_inr > v_eligible_amount THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Violation: Settlement payout exceeds the approved eligible coverage limit.';
    END IF;
END$$

-- -----------------------------------------------------------------------------------
-- TRIGGER 5: AFTER UPDATE ON claims (Automated Compliance & Audit Trail Logging)
-- Purpose:
--   - Automatically logs an entry into `claims_audit_log` whenever status, requested
--     amount, or eligible amount is modified.
-- -----------------------------------------------------------------------------------
DROP TRIGGER IF EXISTS `trg_claims_after_update_audit`$$
CREATE TRIGGER `trg_claims_after_update_audit`
AFTER UPDATE ON `claims`
FOR EACH ROW
BEGIN
    -- Check if status, requested amount, or eligible amount changed
    IF (OLD.status <> NEW.status) OR 
       (OLD.requested_amount_inr <> NEW.requested_amount_inr) OR 
       (IFNULL(OLD.eligible_amount_inr, 0) <> IFNULL(NEW.eligible_amount_inr, 0)) THEN

        INSERT INTO `claims_audit_log` (
            `claim_id`,
            `action_event`,
            `old_status`,
            `new_status`,
            `old_requested_amount`,
            `new_requested_amount`,
            `old_eligible_amount`,
            `new_eligible_amount`,
            `actor_user_id`,
            `notes`,
            `logged_at`
        ) VALUES (
            NEW.id,
            'UPDATE',
            OLD.status,
            NEW.status,
            OLD.requested_amount_inr,
            NEW.requested_amount_inr,
            OLD.eligible_amount_inr,
            NEW.eligible_amount_inr,
            COALESCE(NEW.officer_user_id, NEW.created_by_user_id),
            CONCAT('Status updated from [', OLD.status, '] to [', NEW.status, ']'),
            NOW()
        );
    END IF;
END$$

-- -----------------------------------------------------------------------------------
-- TRIGGER 6: AFTER INSERT ON settlements (Automatic State Synchronization)
-- Purpose:
--   - Once a financial settlement disbursement is inserted, automatically updates
--     the corresponding claim status to 'paid'.
-- -----------------------------------------------------------------------------------
DROP TRIGGER IF EXISTS `trg_settlements_after_insert_sync`$$
CREATE TRIGGER `trg_settlements_after_insert_sync`
AFTER INSERT ON `settlements`
FOR EACH ROW
BEGIN
    UPDATE `claims`
       SET `status` = 'paid'
     WHERE `id` = NEW.claim_id;
END$$

DELIMITER ;

-- ===================================================================================
-- VERIFICATION COMMAND:
-- Execute this query to inspect all active triggers created in this database:
-- SHOW TRIGGERS FROM `health_claims_simulator`;
-- ===================================================================================
