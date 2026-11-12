# Repair Refund Escrow

`RepairRefundEscrow` is a two-round escrow on one versioned deliverable. **Round 1:** the buyer raises
criterion-linked defects on version 1 and validators judge whether each is supported. **Round 2:** the
supplier submits one repair version and validators judge whether each established defect is remedied.
Each criterion's fixed allocation is then released to the supplier or refunded to the buyer exactly once.
No new criterion, allegation or amount can enter after round 1.

The model only labels. Round 1: `SUPPORTED` / `UNSUPPORTED` / `UNCLEAR`. Round 2: `REMEDIED` / `UNREMEDIED` /
`UNCLEAR`. Code derives every state, release and refund. `UNCLEAR` never pays; deadlines end retries with a
documented default. See [docs/DESIGN.md](docs/DESIGN.md) for states, invariants and consensus details.

**Status:** deployed and verified on StudioNet on 2026-11-12. The source and evidence repositories are public. [Live release record](docs/LIVE_RELEASE.md) documents all nine finalized transactions, including two expected rollbacks. The current [Explorer contract](https://explorer-studio.genlayer.com/address/0xB838F846aA1141F396Dbeb2c8c4b70273d363560) settles 60 synthetic units to the supplier and refunds 40 to the buyer, with conservation verified. Deployed source commit `0fbde3d4ee9cdab8227ec9740cf9d2d56b595d72` matches the on-chain bytes (SHA-256 `e42917605024012f09a64f82adf9b881542b68c86ad06f67f8524df055c6e333`). Lint passes and all 107 mocked direct tests pass. Later documentation commits do not change the deployed source. The 2026-09-28 deployment (`0xbb0DD15b...E079`) is superseded and is not evidence for this revision. See [SUBMISSION_DRAFT.md](SUBMISSION_DRAFT.md) for evidence and limitations. No Portal submission is claimed.

## Evidence rules

Deliverables must be small files on `raw.githubusercontent.com`, pinned to a 40-hex commit
(`https://raw.githubusercontent.com/<owner>/<repo>/<commit>/<path>`), at most 5000 raw bytes. The repair must
be the same owner, repo and path at a different commit. A fetch counts only for HTTP 200, 1 to 5000 raw bytes,
strict UTF-8 and non-blank text. Anything else is unavailable and forces every label to `UNCLEAR` without a model call.

## Lifecycle

1. Buyer deploys with a named supplier, brief, 1-4 criteria whose allocations sum to the budget, and five strictly
   ordered deadlines: delivery < claim < judgment < repair < final. Terms are hashed.
2. Supplier `accept_terms(digest)` (or `reject_terms`), then `submit_delivery(url, summary)` with the pinned v1 URL.
3. Buyer `file_claims` once: each claim is `{criterion_id, allegation, quoted_line}` where `quoted_line` is a verbatim
   line of v1. Unclaimed criteria are released immediately. An empty batch settles everything to the supplier.
4. Anyone calls `judge_defects` (max 3 attempts). `SUPPORTED` stays open, `UNSUPPORTED` releases, `UNCLEAR` is retried.
   A quoted line that is not in v1 forces `UNSUPPORTED`.
5. Supplier `submit_repair(url, summary)` (one repair only), then anyone calls `judge_repair` (max 3 attempts).
   `REMEDIED` releases, `UNREMEDIED` refunds. `REMEDIED` while the quoted line is still in v2 becomes `UNCLEAR`.
6. Anyone calls `finalize()` after a deadline: unresolved round-1 claims release to the supplier; unresolved
   defects (no repair, or still `UNCLEAR`) refund the buyer; missed acceptance cancels, missed delivery refunds.

## API

Writes: `accept_terms`, `reject_terms`, `submit_delivery`, `file_claims`, `judge_defects`, `submit_repair`,
`judge_repair`, `finalize`. Views: `get_terms`, `get_submission`, `get_claims`, `get_criterion_state`,
`get_judgment`, `get_accounting`. ABI: [contracts/abi.json](contracts/abi.json). Constructor example:
[examples/constructor.json](examples/constructor.json). Demo: [examples/demo_sequence.md](examples/demo_sequence.md).

## Verify

```powershell
..\.venv\Scripts\Activate.ps1
$env:GENVM_VERSION = "v0.6.0-rc5"
genvm-lint check contracts/repair_refund_escrow.py
python -m pytest
```

Direct tests mock web and model responses. They do not establish live consensus or network finality. Units are
demonstration bookkeeping; no asset is held or transferred. Fetching does not prove publisher identity, and the
model can misread evidence. See [docs/TEST_MATRIX.md](docs/TEST_MATRIX.md).
