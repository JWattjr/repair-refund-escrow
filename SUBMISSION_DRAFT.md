# Submission draft — not deployed or submitted

**Status: local draft only. This contract is undeployed and has not been submitted to the GenLayer Portal.**

## Project

`RepairRefundEscrow` preserves a defect lifecycle across supplier deliverable versions. Buyer and supplier agree to a frozen brief, criterion-level allocations, deadlines, and a repair limit. The supplier accepts the terms digest before submitting version 1.

## Distinguishing mechanism

The buyer's bounded initial claims bind to exact criteria and the current deliverable. GenLayer assesses each claim. Later supplier versions are evaluated only against previously established defects; they cannot trigger new scope claims. A fixed allocation for a repaired or accepted criterion releases to the supplier, while an unresolved defect's full allocation returns to the buyer after the repair limit or final deadline.

## Local verification recorded

- GenVM lint: passed 3 checks.
- Contract validation: 16 methods (5 views, 11 writes).
- ABI schema extraction: succeeded to `contracts/abi.json`.
- Direct-mode tests: 12 passed, covering partial repair and settlement, unsupported and uncertain claims, validator disagreement, malformed output, exact-term acceptance, cancellation, delivery/review deadlines, and constructor bounds.
- Deployment, live consensus receipts, Portal review, and real payments or work verification: not performed.

## Limitations

Payment uses synthetic demo units. Web references do not prove publisher identity or freshness, and model decisions do not establish objective work quality. The pinned runner's availability on a target chain remains unverified. This draft makes no ecosystem originality or Portal-score claim.
