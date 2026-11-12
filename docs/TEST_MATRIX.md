# Test matrix

Run `python -m pytest` from the repository root (107 tests). Direct-mode tests mock web and model responses and do
not establish live consensus or network finality. Every scenario calls `check()`, which asserts
`escrow + released + refunded == total` and that those totals equal the sum of criterion states.

| Requirement | Tests (`tests/test_repair_escrow.py`) |
|---|---|
| Full two-round lifecycle: 60 released, 40 refunded, stored sources with byte count and SHA-256 | `test_full_lifecycle_releases_remedied_and_refunds_unremedied`, `test_recorded_source_hash_matches_the_raw_bytes` |
| Other outcomes: unclaimed released, all unsupported, empty batch | `test_unclaimed_criterion_*`, `test_all_unsupported_*`, `test_empty_claim_batch_*` |
| Code outranks the model: false quote, remedied-with-line-present, label normalization, missing IDs | `test_model_label_cannot_outrank_a_false_quote`, `test_remedied_with_defect_line_*`, `test_labels_are_normalised_*` |
| Unknown IDs and labels, extra fields, non-JSON (8 cases) revert with no state change | `test_invalid_model_output_reverts_without_state_change` |
| New or unclaimed IDs in round 2 rejected | `test_round_two_rejects_unknown_ids_and_unclaimed_criteria`, `test_validator_rejects_a_new_allegation_row_in_round_two` |
| Adversarial leader with the same headline: forged label, SHA, byte count, citations, extra row, wrong ID/label set, unavailable-but-positive, reorder, digest (17 forgeries in round 1, 5 in round 2) | `test_validator_rejects_forged_round_one_leader`, `test_validator_rejects_forged_round_two_leader` |
| Honest-but-different validator disagrees; leader error matched | `test_validator_with_a_different_honest_model_disagrees`, `test_validator_matches_leader_error_*` |
| Unauthorized callers in every phase; permissionless triggers | `test_unauthorized_callers_are_rejected_in_every_phase`, `test_permissionless_triggers_work_for_any_caller` |
| Replay after settlement, frozen claims, no second repair | `test_replays_and_late_actions_*`, `test_claims_are_frozen_*`, `test_second_repair_*` |
| Evidence failures (404, 500, empty, blank, 5001 bytes, invalid UTF-8) in both rounds never pay; exactly 5000 bytes accepted | `test_round_one_evidence_failure_*`, `test_round_two_evidence_failure_*`, `test_body_of_exactly_5000_bytes_*` |
| Deadline defaults: bounded attempts then release; unresolved-defect refund; no repair; no claims; no delivery; no acceptance; early finalize reverts | `test_unclear_attempts_are_bounded_*`, `test_round_one_deadline_default_*`, `test_round_two_unclear_*`, `test_no_repair_*`, `test_no_claims_*`, `test_no_delivery_*`, `test_no_acceptance_*`, `test_finalize_before_any_deadline_*` |
| Pinned-URL rules (9 bad deliverables, 4 bad repairs); constructor and claim validation | `test_deliverable_must_be_*`, `test_repair_must_be_*`, `test_constructor_rejects_*`, `test_claim_batch_validation` |
| No `self` in nondeterministic code; full canonical comparison; frozen allowlists | `test_nondeterministic_code_never_touches_contract_state`, `test_validator_compares_the_full_canonical_result`, `test_allowlists_and_bounds_*` |

A mutation check (validator comparing only the first label) was caught by 5 tests, so the forgery tests do bite.
Not covered: live consensus, real validator LLM behavior, and the GitHub raw host.
