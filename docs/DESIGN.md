# Design (implemented)

Implements [DESIGN_PROPOSAL.md](DESIGN_PROPOSAL.md). This revision replaces deployed commit `2e03cc0`, whose
consensus could never match because its snapshot digest covered full fetched text that changed per request.

## Participants and actions

| Actor | Action | Gate |
|---|---|---|
| Buyer (deployer) | constructor freezes terms | allocations sum to budget; five deadlines strictly ordered and future |
| Supplier | `accept_terms`, `reject_terms`, `submit_delivery`, `submit_repair` | exact caller; phase; deadline |
| Buyer | `file_claims` (once) | exact caller; `AWAITING_CLAIMS`; before claim deadline |
| Anyone | `judge_defects`, `judge_repair`, `finalize` | phase; deadline; at most 3 attempts per round |

Action deadlines are inclusive (`now <= deadline`); `finalize` requires `now > deadline`.

## States

Phase: `AWAITING_ACCEPTANCE` -> `AWAITING_DELIVERY` -> `AWAITING_CLAIMS` -> `ROUND1_PENDING` -> `REPAIR_REQUIRED`
-> `ROUND2_PENDING` -> `SETTLED`; terminal alternatives `CANCELLED` and `REFUNDED_NO_DELIVERY`.

Criterion: `UNCLAIMED` -> (`file_claims`) `CLAIMED` or `RELEASED`; `CLAIMED` -> `SUPPORTED` | `RELEASED` | stays;
`SUPPORTED` -> `RELEASED` | `REFUNDED` | stays. `RELEASED` and `REFUNDED` are final and cannot be closed twice.
Deadline defaults: `CLAIMED` at the judgment deadline -> `RELEASED`; `SUPPORTED` at the repair deadline (no repair)
or the final deadline -> `REFUNDED`.

## Judgment round

`_snapshot` copies state into a plain dict (round, contract address, terms digest, pinned URLs, claims with
criteria text, attempt) and digests it. `_consensus(snap)` is module-level, so `leader_fn` and `validator_fn` cannot
reach `self`. Both run `_evaluate`: fetch each URL, and only if all are `fetched`, one model call returning exactly
`{"labels": {"<criterion_id>": "<LABEL>"}}`. Unknown IDs, non-allowlisted labels, extra fields or non-JSON revert with
`[LLM_ERROR]` and change nothing; missing IDs become `UNCLEAR`. Code guards then apply (false quote -> `UNSUPPORTED`;
`REMEDIED` with the defect line still present -> `UNCLEAR`).

The result is `{input_digest, sources:[{url,status,byte_count,sha256}], labels:[{criterion_id,label}]}`. The validator
normalizes the leader result with `_candidate` (strict schema, allowlist, digest binding, unavailable source implies
all `UNCLEAR`), re-runs `_evaluate`, and requires `_canonical(leader) == _canonical(mine)`. The stored value is that
same object, kept under `get_judgment(round, attempt)`. There are no citations, quotes or free text in it.

## Invariants

1. `sum(allocation) == total`; `escrow + released + refunded == total` always (`get_accounting().conserved`).
2. Each allocation leaves escrow exactly once; `_close` reverts on a settled criterion.
3. The claim set is frozen at `file_claims`; round 2 judges exactly the `SUPPORTED` criteria.
4. `UNCLEAR` never moves money; only the documented deadline defaults do.
5. An unavailable source cannot yield a positive label.
6. No `self` in nondeterministic code (checked by an AST test).
7. Bounds: 4 criteria, 4 claims, 2 versions, 2 URLs, 5000 bytes per source, 3 attempts per round.

## Known limits

- `quoted_line` is matched as a substring, so a short quote such as `5 cm` would also match `25 cm`. Demo claims use
  full-line quotes.
- Failed (reverted) judgments do not count as attempts, so repeated invalid model output costs callers
  transactions but cannot change state.
- Mutual cancellation and per-claim evidence URLs from the previous revision were removed.
