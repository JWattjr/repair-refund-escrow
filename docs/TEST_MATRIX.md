# Test matrix

Run `python -m pytest` from the repository root. Direct-mode tests mock web/model responses and do not establish live consensus or network finality.

| Invariant or behavior | Test |
|---|---|
| One repair remedies one criterion, leaves another open, then releases 60 and refunds 40 exactly once | `test_one_defect_is_repaired_and_the_other_allocation_is_refunded` |
| Unsupported allegations release their criterion allocation and cannot be replaced by a later claim batch | `test_unsupported_claim_releases_its_allocation_and_rejects_late_expansion` |
| Malformed model fields revert without moving funds; validator disagreement is rejected by the direct validator | `test_malformed_and_disagreeing_defect_assessments_do_not_change_claim_state` |
| Unavailable evidence stays uncertain and held until the final deadline refund | `test_unavailable_claim_evidence_remains_held_and_can_be_refunded_at_final_deadline` |
| Exact terms acceptance and mutual pre-delivery cancellation | `test_terms_require_supplier_acceptance_and_cancellation_is_mutual` |
| Missing initial delivery refunds after, but not at, the delivery deadline | `test_no_delivery_after_frozen_deadline_refunds_escrow` |
| Missing supplier acceptance also refunds after the delivery deadline | `test_no_supplier_acceptance_by_delivery_deadline_refunds_escrow` |
| No buyer claim by the review deadline accepts all criteria under frozen terms | `test_missed_review_deadline_accepts_all_criteria_without_claim_expansion` |
| Budget, allocation sum, review window, and repair limit are bounded | `test_constructor_rejects_unfunded_allocations_or_unbounded_policy` (4 parameter cases) |

The recorded direct-mode run passed 12 tests. GenVM lint passed 3 checks, SDK validation reported 16 methods (5 views and 11 writes), and schema extraction succeeded. No deployment was run.
