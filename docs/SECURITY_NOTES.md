# Security notes

## Terms and permissions

- The constructor sender is the buyer and names one different supplier. Brief, criteria, allocations and five ordered deadlines are frozen and hashed. The supplier must accept the exact digest before delivering; `reject_terms` refunds in full.
- Only the supplier may deliver and repair; only the buyer may file claims, and only once. `judge_defects`, `judge_repair` and `finalize` are permissionless because every input is already frozen in state.
- No method after `file_claims` accepts a criterion, allegation, quoted line or amount.

## Consensus and evidence

- Evidence must be a `raw.githubusercontent.com` URL pinned to a 40-hex commit; a repair must keep the owner, repo and path and change the commit. Anything else reverts at submission.
- A fetch is valid only for HTTP 200, 1 to 5000 raw bytes, strict UTF-8 and non-blank text. Otherwise the source is unavailable and every label is `UNCLEAR` with no model call.
- The model returns only labels from a frozen allowlist per round. Unknown IDs or labels, extra fields and non-JSON revert. Code overrides the model: a quoted line that is not in version 1 forces `UNSUPPORTED`; `REMEDIED` while the line is still in version 2 becomes `UNCLEAR`.
- Leader and validator functions are module-level and never touch contract state. The validator normalizes the leader result, re-runs the whole evaluation and requires the full canonical result (digest, per-source status, bytes, SHA-256, every label) to match exactly.
- Fetched text, claims and criteria are untrusted prompt data. Pinning proves content stability, not publisher identity.

## Accounting and limits

- Allocations are positive integers summing to the budget; `_close` moves each allocation out of escrow once and reverts on a settled criterion. `get_accounting().conserved` must hold.
- `UNCLEAR` never pays. Deadline defaults: an unresolved round-1 claim releases to the supplier; an unresolved defect refunds the buyer. Each round allows at most 3 attempts; reverted judgments are not counted.
- Bounds: 4 criteria and claims, 2 versions, 5000 bytes per source, bounded text and JSON.
- A short `quoted_line` matches as a substring (`5 cm` also matches `25 cm`). Units are synthetic with no custody. Direct tests use mocks; one live honest-network run is recorded in `docs/LIVE_RELEASE.md`.
