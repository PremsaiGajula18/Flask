-- =============================================================================
-- HEALTH INSURANCE CLAIMS PROCESSING SIMULATOR — MYSQL TRIGGERS SUITE
-- Database: health_claims_simulator
-- 
-- This script implements advanced enterprise MySQL triggers across 4 categories:
--   1. BEFORE INSERT  -> Clinical, Network & Financial Validation
--   2. BEFORE UPDATE  -> Immutability, Policy Limits & Expiration Automation
--   3. AFTER INSERT   -> State Synchronization & Automated Payout Marking
--   4. AFTER UPDATE   -> Audit Trail Logging & Compliance Tracking
-- =============================================================================

USE `health_claims_simulator`;

-- -----------------------------------------------------------------------------
-- 0. AUDIT TABLE: Security & Compliance Tracking for Claims
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `claims_security_audit` (
    `audit_id`             BIGINT AUTO_INCREMENT PRIMARY KEY,
    `claim_id`             INT NOT NULL,
    `event_type`           VARCHAR(20) NOT NULL COMMENT 'UPDATE, INSERT, DELETE',
    `old_status`           VARCHAR(30) NULL,
    `new_status`           VARCHAR(30) NULL,
    `old_requested_amount` DECIMAL(12, 2) NULL,
    `new_requested_amount` DECIMAL(12, 2) NULL,
    `old_eligible_amount`  DECIMAL(12, 2) NULL,
    `new_eligible_amount`  DECIMAL(12, 2) NULL,
    `officer_user_id`      INT NULL,
    `change_summary`       VARCHAR(255) NULL,
    `created_at`           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX `idx_audit_claim` (`claim_id`),
    INDEX `idx_audit_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


DELIMITER $$

-- -----------------------------------------------------------------------------
-- TRIGGER 1: BEFORE INSERT ON claims (Clinical & Network Integrity Gatekeeper)
-- Purpose:
--   - Rejects non-positive requested amounts (amount must be > 0).
--   - Enforces clinical timeline (admission date cannot be in the future).
--   - Rejects discharge dates earlier than admission date.
--   - Enforces Cashless Network Rule: Cashless claims can only be filed at
--     empanelled network hospitals (network_status = 1).
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS `trg_claims_before_insert`$$
CREATE TRIGGER `trg_claims_before_insert`
BEFORE INSERT ON `claims`
FOR EACH ROW
BEGIN
    DECLARE v_is_network TINYINT DEFAULT 0;

    -- 1. Amount validation
    IF NEW.requested_amount_inr <= 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Error: Requested claim amount must be strictly greater than 0.';
    END IF;

    -- 2. Admission date cannot be in the future
    IF NEW.admission_date > CURDATE() THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Error: Hospital admission date cannot be in the future.';
    END IF;

    -- 3. Discharge date sanity check
    IF NEW.discharge_date < NEW.admission_date THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Error: Discharge date cannot be earlier than admission date.';
    END IF;

    -- 4. Cashless Network Empanelment Validation
    IF NEW.claim_type = 'cashless' THEN
        SELECT `network_status` INTO v_is_network
          FROM `hospitals`
         WHERE `id` = NEW.hospital_id;

        IF v_is_network = 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Trigger Error: Cashless claims can only be filed at empanelled network hospitals.';
        END IF;
    END IF;
END$$


-- -----------------------------------------------------------------------------
-- TRIGGER 2: BEFORE UPDATE ON claims (Immutability & Coverage Limit Protection)
-- Purpose:
--   - Locks the requested claim amount once a claim has been approved or paid.
--   - Ensures the approved eligible amount never exceeds requested amount.
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS `trg_claims_before_update`$$
CREATE TRIGGER `trg_claims_before_update`
BEFORE UPDATE ON `claims`
FOR EACH ROW
BEGIN
    -- 1. Immutability of financial amounts after decision
    IF (OLD.status IN ('approved', 'paid')) AND (OLD.requested_amount_inr <> NEW.requested_amount_inr) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Error: Requested claim amount is locked and cannot be modified after approval or settlement.';
    END IF;

    -- 2. Eligible amount cannot exceed requested amount
    IF NEW.eligible_amount_inr IS NOT NULL AND NEW.eligible_amount_inr > NEW.requested_amount_inr THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Error: Approved eligible amount cannot exceed the requested claim amount.';
    END IF;
END$$


-- -----------------------------------------------------------------------------
-- TRIGGER 3: BEFORE INSERT & BEFORE UPDATE ON policies (Policy Lifecycle Automation)
-- Purpose:
--   - Validates that policy end date is after start date.
--   - Automatically transitions policy status to 'expired' if end_date has passed.
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS `trg_policies_before_insert`$$
CREATE TRIGGER `trg_policies_before_insert`
BEFORE INSERT ON `policies`
FOR EACH ROW
BEGIN
    IF NEW.end_date <= NEW.start_date THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Error: Policy expiration date must be strictly after the start date.';
    END IF;

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


-- -----------------------------------------------------------------------------
-- TRIGGER 4: BEFORE INSERT ON settlements (Disbursement Financial Protection)
-- Purpose:
--   - Rejects non-positive payout amounts.
--   - Verifies the parent claim is currently in 'approved' status.
--   - Ensures payout does not exceed the approved eligible coverage.
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS `trg_settlements_before_insert`$$
CREATE TRIGGER `trg_settlements_before_insert`
BEFORE INSERT ON `settlements`
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(30);
    DECLARE v_eligible DECIMAL(12, 2);

    IF NEW.amount_inr <= 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Error: Settlement payout amount must be strictly greater than 0.';
    END IF;

    SELECT `status`, `eligible_amount_inr`
      INTO v_status, v_eligible
      FROM `claims`
     WHERE `id` = NEW.claim_id;

    IF v_status <> 'approved' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Error: Settlement payout can only be generated for claims in approved status.';
    END IF;

    IF NEW.amount_inr > v_eligible THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trigger Error: Settlement payout exceeds the claim approved eligible amount.';
    END IF;
END$$


-- -----------------------------------------------------------------------------
-- TRIGGER 5: AFTER INSERT ON settlements (Automatic Claim Status Synchronization)
-- Purpose:
--   - Once a settlement payout is recorded, automatically updates the parent
--     claim's status to 'paid' and records payment_recorded_date.
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS `trg_settlements_after_insert_sync`$$
CREATE TRIGGER `trg_settlements_after_insert_sync`
AFTER INSERT ON `settlements`
FOR EACH ROW
BEGIN
    UPDATE `claims`
       SET `status` = 'paid',
           `payment_recorded_date` = NEW.recorded_date
     WHERE `id` = NEW.claim_id;
END$$


-- -----------------------------------------------------------------------------
-- TRIGGER 6: BEFORE INSERT ON claim_history (Auto-Sequencing Engine)
-- Purpose:
--   - Automatically calculates the next sequence_no for the claim's audit history
--     (1, 2, 3...) so developers don't have to manually count events.
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS `trg_claim_history_before_insert`$$
CREATE TRIGGER `trg_claim_history_before_insert`
BEFORE INSERT ON `claim_history`
FOR EACH ROW
BEGIN
    DECLARE v_max_seq INT DEFAULT 0;

    SELECT COALESCE(MAX(`sequence_no`), 0)
      INTO v_max_seq
      FROM `claim_history`
     WHERE `claim_id` = NEW.claim_id;

    SET NEW.sequence_no = v_max_seq + 1;
END$$


-- -----------------------------------------------------------------------------
-- TRIGGER 7: AFTER UPDATE ON claims (Security Audit Trail Logging)
-- Purpose:
--   - Logs every status transition or monetary amendment to `claims_security_audit`.
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS `trg_claims_after_update_audit`$$
CREATE TRIGGER `trg_claims_after_update_audit`
AFTER UPDATE ON `claims`
FOR EACH ROW
BEGIN
    IF (OLD.status <> NEW.status) OR 
       (OLD.requested_amount_inr <> NEW.requested_amount_inr) OR 
       (IFNULL(OLD.eligible_amount_inr, 0) <> IFNULL(NEW.eligible_amount_inr, 0)) THEN

        INSERT INTO `claims_security_audit` (
            `claim_id`,
            `event_type`,
            `old_status`,
            `new_status`,
            `old_requested_amount`,
            `new_requested_amount`,
            `old_eligible_amount`,
            `new_eligible_amount`,
            `officer_user_id`,
            `change_summary`,
            `created_at`
        ) VALUES (
            NEW.id,
            'UPDATE',
            OLD.status,
            NEW.status,
            OLD.requested_amount_inr,
            NEW.requested_amount_inr,
            OLD.eligible_amount_inr,
            NEW.eligible_amount_inr,
            NEW.officer_user_id,
            CONCAT('Transition from [', OLD.status, '] to [', NEW.status, ']'),
            NOW()
        );
    END IF;
END$$

DELIMITER ;

-- =============================================================================
-- VERIFICATION COMMAND:
-- SHOW TRIGGERS FROM `health_claims_simulator`;
-- =============================================================================
