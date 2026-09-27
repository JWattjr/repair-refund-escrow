# Mechanism differentiation

## Nearest comparison

The nearest local comparison is Semantic Milestone Matrix Oracle, which evaluates predefined milestones, and QuestChain, which tracks milestone progress. This project instead carries defects identified on one deliverable version into later supplier repair versions. Each criterion keeps its own frozen allocation and defect history through that version lifecycle.

## New state transition

The defining transition is `version N → criterion-bound supported defect → supplier repair version N+1 → per-defect remedied/unresolved judgment → release/refund of that criterion's fixed allocation`. The buyer gets one bounded initial claim batch tied to the current deliverable. Later assessments can close those defects but cannot introduce a new criterion, allegation, or payment amount.

The supplier accepts the hashed terms before work starts. Payment allocations must sum to the escrow budget at formation. Deterministic settlement releases each accepted or remedied allocation once and refunds the full allocation for each still-open defect when the repair limit or final deadline is reached.

## Limits

The escrow and payouts are internal demonstration units rather than real custody. Model judgments do not prove work quality, source authenticity, or objective defect facts. The local comparison does not establish ecosystem-wide originality or Portal outcomes.
