/**
 * ====================================================================================
 * CLIENT-SIDE JAVASCRIPT CONTROLLER: CLAIMS PROCESSING SIMULATOR
 * ====================================================================================
 * Project   : Health Insurance Claims Processing Simulator (BRD Benchmark)
 * Component : Client Dynamic UI Script (`app/static/js/app.js`)
 * ====================================================================================
 * Description:
 *   Handles client-side interactivity across the simulator:
 *   1. Dynamic Member & Plan Loading: Fetches covered members via JSON API when a
 *      policy dropdown changes.
 *   2. Adjudication Real-Time Math Calculator: Computes net insurer payout, deductible
 *      absorptions, and co-payment fractions live as the claims officer enters values.
 *   3. Auto-dismissing flash alerts and interactive UI toggles.
 * ====================================================================================
 */

document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    // --------------------------------------------------------------------------------
    // 1. Dynamic Member & Plan Specification Loader on Policy Selection
    // --------------------------------------------------------------------------------
    const policySelect = document.getElementById("policy_id");
    const memberSelect = document.getElementById("member_id");
    const planDetailsBadge = document.getElementById("plan_details_badge");

    if (policySelect && memberSelect) {
        policySelect.addEventListener("change", function () {
            const policyId = this.value;

            // Reset member options if user clears the policy selection
            if (!policyId) {
                memberSelect.innerHTML = '<option value="">-- First Select a Policy --</option>';
                if (planDetailsBadge) planDetailsBadge.textContent = "";
                return;
            }

            // Fetch policy members asynchronously from the Flask REST API endpoint
            fetch(`/api/policies/${policyId}/members`)
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(function (data) {
                    // Populate member dropdown with family members
                    memberSelect.innerHTML = '<option value="">-- Choose Covered Member --</option>';
                    data.members.forEach(function (member) {
                        const opt = document.createElement("option");
                        opt.value = member.id;
                        opt.textContent = `${member.display_name} (${member.relationship})`;
                        memberSelect.appendChild(opt);
                    });

                    // Update plan specification badge if container exists
                    if (planDetailsBadge) {
                        planDetailsBadge.innerHTML = `
                            <span class="badge bg-primary-subtle text-primary border me-1">Plan: ${data.insurer || ""} ${data.plan_name}</span>
                            <span class="badge bg-secondary-subtle text-secondary border">Covers: ${data.covered_treatment_types}</span>
                        `;
                    }
                })
                .catch(function (err) {
                    console.error("Failed to load policy members:", err);
                });
        });
    }

    // --------------------------------------------------------------------------------
    // 2. Claims Officer Adjudication Live Payout Preview
    // --------------------------------------------------------------------------------
    // As the officer adjusts the eligible amount, this calculates the simulated payout
    // instantly without requiring a page reload or round-trip server request.
    const eligibleInput = document.getElementById("officer_eligible_amount");
    const livePayoutPreview = document.getElementById("live_payout_preview");

    if (eligibleInput && livePayoutPreview) {
        const deductible = parseFloat(eligibleInput.getAttribute("data-deductible") || "0");
        const copayPercent = parseFloat(eligibleInput.getAttribute("data-copay") || "0");

        function updatePayoutPreview() {
            const eligible = parseFloat(eligibleInput.value) || 0;

            // Handle non-positive or blank inputs
            if (eligible <= 0) {
                livePayoutPreview.textContent = "₹0.00";
                return;
            }

            // Step 1: Deductible application
            const minDed = Math.min(eligible, deductible);
            const baseAmount = eligible - minDed;

            // Step 2: Patient co-pay calculation
            const insurerFactor = 1.0 - (copayPercent / 100.0);
            const payout = (baseAmount * insurerFactor).toFixed(2);

            // Step 3: Format in Indian Rupee locale (e.g. ₹25,000.00)
            livePayoutPreview.textContent = `₹${Number(payout).toLocaleString("en-IN", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            })}`;
        }

        // Bind to input and change events for real-time calculation
        eligibleInput.addEventListener("input", updatePayoutPreview);
        eligibleInput.addEventListener("change", updatePayoutPreview);
        updatePayoutPreview();
    }
});
