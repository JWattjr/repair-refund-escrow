# Distinctiveness audit

Scope: contract source review against the other nine portfolio contracts, the named standalone contracts, and relevant local projects. This is a local comparison, not an ecosystem-wide originality claim.

**Disposition: KEEP.** This is a multi-round criterion-level repair and partial refund state machine, not a one-shot score followed by a payout.

| Closest comparator | Its judgment | Participants and actions | Its state changes | Capability or invariant implemented here |
|---|---|---|---|---|
| Standalone Semantic Milestone Matrix Oracle | Judges each fixed milestone criterion as satisfied, unsatisfied, or inconclusive and derives a threshold score. | An owner locks evidence and criteria; callers resolve after the deadline. | Stores one score/status and attempt count. | Buyer-submitted defects become persistent criterion states; a supplier may submit bounded repair versions, and each open criterion is independently marked remedied, unresolved, or uncertain before its allocation is released or refunded. |
| Standalone QuestChain | Judges a fixed list of milestone statuses and derives achievement masks and points. | A quest owner configures milestones; callers resolve and claim rewards. | Changes quest progress and deterministic points. | It does not preserve buyer claims against successive deliverable versions or split one escrow by criterion-level repair outcomes. |
| Local Faultline | Judges agent attempts against charter clauses and assigns responsibility; an attempt can be retried. | A requester escrows demo units and names agents; agents submit artifacts/evidence. | Settles the charter and bonds by attempt outcome and responsibility. | Faultline retries a group attempt with aggregate clause responsibility; this contract persists each buyer defect and appends a separate repair finding history for each criterion. |
| Local SlashCourt | Judges whether a respondent violated versioned rules for an opened case. | Claimant/respondent submit evidence; the court applies the bond vault result. | Resolves one case and applies penalty/award. | SlashCourt adjudicates rule breaches; this contract gives the supplier a repair path before criterion-specific refund/release settlement. |

The state machine is implemented in contracts/repair_refund_escrow.py (submit_defects, _open_defects, submit_repair_version, review_repair_version, _settle). Each criterion allocation is paid at most once, and the final sum must equal the remaining escrow.

**Evidence status:** implemented; the current direct suite passes 12 tests. Phase 3 still needs forged-result, validator-disagreement, evidence-failure, replay, and allocation-boundary coverage. The StudioNet runner probe passed, but this project has not had its own live demonstration yet.