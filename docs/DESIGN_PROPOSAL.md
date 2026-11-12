# Design proposal: repair-refund-escrow v2

Status: Phase 1 proposal, 2026-11-12. Nothing here is built, committed, or deployed yet.
Phase 2 needs design confirmation first. Reviewed baseline: repo HEAD `a964f47`. The deployed
source is commit `2e03cc0`; the later commits change only docs and deployment records.

## 1. Why the 2026-09-28 judgment finalized UNDETERMINED

Transaction `0x2151aa10…6cc7` (`submit_defects`, contract `0xbb0DD15b…E079`, StudioNet):
leader SUCCESS (it returned `REPAIR_REQUIRED` with 2 open defects), `MAJORITY_DISAGREE`, 4 rounds,
votes DISAGREE 3 / IDLE 2. Nothing changed in state: phase stayed `AWAITING_CLAIMS`, and both
criteria stayed `UNREVIEWED`.

**Root cause (deterministic): the evidence bytes change on every request, so the snapshot digest
can never match.**

- The leader computes `snapshot_digest = sha256(canonical({...base, evidence}))`, where `evidence`
  holds the **full fetched text** of each URL (`contracts/repair_refund_escrow.py:375-377`).
- The validator refetches (`_snapshot_for_defects`, `:415-423`). It then requires
  `raw["snapshot_digest"] == snapshot["snapshot_digest"]` (`_defect_candidate`, `:161`). A mismatch
  raises `ValueError`, and `validator_fn` returns `False` (`:410`).
- Both the deliverable URL and the weatherproofing evidence URL were the same Open-Meteo archive
  query. Its JSON includes `generationtime_ms`, which changes on each request. I checked this on
  2026-11-12 with two back-to-back anonymous fetches:

| Fetch | HTTP | `size_download` | SHA-256 | `generationtime_ms` |
|---|---|---|---|---|
| recorded 2026-09-28 | 200 | 286 | (not recorded) | (not recorded) |
| 2026-11-12 #1 | 200 | 287 | `a9433d81…5536` | `0.08046627044677734` |
| 2026-11-12 #2 | 200 | 287 | `55167812…05bb` | `0.03707408905029297` |

  Even the byte count drifts (286 vs 287), because the number of digits varies. The DFRobot `.ino`
  (HTTP 200, 1,876 bytes, `2c37a1bc…bcf8`) was stable. One varying source is enough to break the
  match. So every validator in every one of the 4 rotations disagreed, whatever the LLM said.

**Secondary defects (they would have caused disagreement even with stable bytes):**

1. The comparison included the LLM's free-form `citations` list (`_result_vector`, `:227-230`). Each
   validator could choose 0, 1 or 2 allowed URLs, in any order. That is high-variance output inside
   an exact match.
2. The validator uses `self` (`self._snapshot_for_defects`) and fetches every URL **twice**: once
   for the snapshot and once inside `leader_fn()`. That doubles the web work and the variance
   exposure. The leader closure also reads `self.terms_digest`/`self.brief` through `base`, built
   from `self` within the same call.
3. The evidence was not literal. The "deliverable" was a precipitation API response, and the
   calibration "evidence" was a vendor sample sketch that never contains the alleged 1,520 µS/cm
   reading. The defects existed only in the buyer's narrative text. A determinate label therefore
   depended on how much each model trusted that narrative.
4. Judgment ran inside the buyer's `submit_defects`. A failed consensus discarded the claims too,
   so there was nothing to retry from (self-review blocker #3).
5. The constructor strings were double-encoded (`25Â°C`, `Â±2%`, `Âµ` in the readback). This is
   mojibake from the Windows harness, visible on-chain. It did not cause the disagreement, but it
   damages the record.

**IDLE 2:** the receipts do not attribute them. A plausible contributor is the long validator path
(4 fetches plus a large-prompt LLM call per validator). I mark this as unverified.

## 2. Participants and actions

| Actor | Action | Gate |
|---|---|---|
| Buyer (deployer) | `__init__` freezes terms | allocations sum to total; deadlines ordered |
| Supplier | `accept_terms(digest)` / `reject_terms()` | before `delivery_deadline` |
| Supplier | `submit_delivery(url, summary)`: version 1 | pinned URL; before `delivery_deadline` |
| Buyer | `file_claims(claims_json)`: one batch, at most `MAX_CRITERIA` | before `claim_deadline`; frozen afterwards |
| Anyone | `judge_defects()`: round 1 | inputs frozen; before `judgment_deadline` |
| Supplier | `submit_repair(url, summary)`: version 2, one only | same repo/path, new commit; before `repair_deadline` |
| Anyone | `judge_repair()`: round 2 | inputs frozen; before `final_deadline` |
| Anyone | `finalize()`: applies deadline defaults, settles | after the relevant deadline |

Triggers are permissionless because every input to them is frozen in state before they run.
No method after `file_claims` accepts a criterion, allegation, quoted line, or amount.

Frozen deadlines: `delivery < claim < judgment < repair < final`. All five go into `terms_digest`.

## 3. Inputs

- **Deliverable URL** must match
  `^https://raw\.githubusercontent\.com/[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}/[0-9a-f]{40}/[A-Za-z0-9._/-]{1,200}$`,
  with no `..` segment. The repair URL must have the same owner, repo and path, and a different
  commit.
- **Claim** = `{criterion_id, allegation (12–300 chars), quoted_line (8–200 chars, one line)}`.
  The `quoted_line` is the buyer's verbatim line from version 1. It replaces the old separate
  `evidence_url`, so the deliverable itself is the evidence.
- ASCII-only fixture text for the demo, which avoids the mojibake.

## 4. States and transitions

Contract phase:

```
AWAITING_ACCEPTANCE -> AWAITING_DELIVERY -> AWAITING_CLAIMS -> ROUND1_PENDING
  -> REPAIR_REQUIRED -> ROUND2_PENDING -> SETTLED
AWAITING_ACCEPTANCE --reject / delivery deadline--> CANCELLED (full refund)
AWAITING_DELIVERY --delivery deadline--> REFUNDED_NO_DELIVERY (full refund)
AWAITING_CLAIMS --no claims by claim deadline / empty batch--> SETTLED (all released)
ROUND1_PENDING --no SUPPORTED left--> SETTLED
```

Per criterion (code derives every transition; the LLM only labels):

| From | Event | To | Money |
|---|---|---|---|
| UNCLAIMED | round 1 begins | RELEASED | supplier |
| CLAIMED | R1 `SUPPORTED` | SUPPORTED | none yet |
| CLAIMED | R1 `UNSUPPORTED` | RELEASED | supplier |
| CLAIMED | R1 `UNCLEAR` | CLAIMED (retry) | **none** |
| CLAIMED | `judgment_deadline` passes | RELEASED (default, see Q1) | supplier |
| SUPPORTED | no repair by `repair_deadline` | REFUNDED | buyer |
| SUPPORTED | R2 `REMEDIED` | RELEASED | supplier |
| SUPPORTED | R2 `UNREMEDIED` | REFUNDED | buyer |
| SUPPORTED | R2 `UNCLEAR` | SUPPORTED (retry) | **none** |
| SUPPORTED | `final_deadline` passes | REFUNDED (default) | buyer |

The deadline defaults put the burden on the party asserting a change. The buyer must establish a
defect. The supplier must establish a remedy. A label that is determinate is locked; only the
remaining `UNCLEAR` items are re-judged, for at most `MAX_ATTEMPTS = 3` per round.

## 5. One judgment round (both rounds share this shape)

```
write method (deterministic):
  snap = {round, terms_digest, criteria_subset, claims, urls, prior labels}  # ordinary locals
  snap["input_digest"] = digest(snap)
  leader_fn():   return evaluate(snap)          # no self
  validator_fn(r): return canonical(valid(r, snap)) == canonical(evaluate(snap))  # no self, one refetch
evaluate(snap):
  sources = [fetch(u) for u in snap.urls]       # v1 for round 1; v1 + v2 for round 2
  if any source.status != "fetched": labels = all UNCLEAR   # no LLM call
  else: labels = parse(exec_prompt(...))
  apply code guards
  return {input_digest, sources:[{url,status,byte_count,sha256}], labels:{id: LABEL}}
```

- **fetch** is fail-closed. It returns `fetched` only for HTTP 200 with `bytes`, 0 < `len(body)` ≤
  5000, strict UTF-8 decode, and non-blank text. Anything else is `unavailable`, and an oversized
  body is `unavailable` (no truncation). Raw bytes are measured on `response.body`, which matches
  `curl -w "%{size_download}"`.
- **parse**: the model returns `{"labels": {"<criterion_id>": "<LABEL>"}}`. Extra or unknown IDs and
  labels outside the round's allowlist (R1 `SUPPORTED|UNSUPPORTED|UNCLEAR`, R2
  `REMEDIED|UNREMEDIED|UNCLEAR`, matched after `strip().upper()`) make the result invalid
  (`[LLM_ERROR]`, no state change, retryable). Any ID that is missing becomes `UNCLEAR`.
- **Code guards**: in R1, if `quoted_line` is not a verbatim substring of v1, the label becomes
  `UNSUPPORTED` (the buyer's frozen quote is false). In R2, `REMEDIED` while `quoted_line` is still
  verbatim in v2 becomes `UNCLEAR` (see Q5).
- **Comparison** is the full canonical stored result: digest, every source record, every label. It
  holds no free-form text, citations or quotes. Pinned commits make the bytes immutable, and the
  labels come from a closed set, so exact equality is achievable. There is no "close enough".
- The stored round result is exactly the compared object, which keeps the audit trail
  (`url/status/bytes/sha256`) the old version lacked.

## 6. Invariants

1. `sum(allocation) == total_units`; `escrow + released + refunded == total_units` at all times.
2. Each criterion reaches `RELEASED` or `REFUNDED` exactly once; settled criteria never change.
3. The claim set is frozen at `file_claims`. Round 2 covers exactly the `SUPPORTED` criteria.
4. `UNCLEAR` never moves money; only the documented deadline defaults do.
5. A source that is not `fetched` can never produce `SUPPORTED`, `UNSUPPORTED`, `REMEDIED` or
   `UNREMEDIED`.
6. Closures read only locals; no `self` inside `leader_fn`/`validator_fn`.
7. Bounds: ≤ 4 criteria, ≤ 4 claims, 2 versions, 2 URLs per round, ≤ 5000 bytes per source,
   ≤ 3 attempts per round, bounded strings.

## 7. Changes from the deployed source

| Rule | Deployed `2e03cc0` | Proposed |
|---|---|---|
| Evidence | any HTTPS; Open-Meteo varies per request | `raw.githubusercontent.com/<40-hex commit>/` only |
| Compare | digest over full text + LLM citations | canonical labels + source records; no citations |
| Validator | uses `self`, fetches twice | locals only, one refetch |
| Uncertainty label | `UNCERTAIN` carried as `DEFECT_UNCERTAIN`, refunded at end | `UNCLEAR` retried, deadline default (**conflicts with approved behavior: Q2**) |
| Judgment trigger | inside buyer's `submit_defects` | claims stored first; permissionless `judge_defects` |
| Repair versions | 1–3 | exactly 1 (**conflict: Q3**) |
| Claim evidence | separate `evidence_url` per claim | `quoted_line` in the deliverable itself |
| Cancellation | request/confirm mutual cancel | removed (**Q4**); `reject_terms` kept |
| Truncation/size | > 5000 → unavailable | unchanged |

Any source change needs a fresh StudioNet deployment and new live evidence. The old address stays
historical only.

## 8. Demo evidence (proposed; not yet published)

There are no suitable public files. The existing public `JWattjr/genlayer-demo-evidence` holds no
two-version deliverable. The proposed new public repo is `JWattjr/repair-refund-escrow-evidence`
(**awaiting approval**), with one file `handover.md` in two commits. It is ASCII and LF only, with
`.gitattributes: * text eol=lf`, so the committed bytes match the hashes below.

Criteria (frozen at deploy, total 100):

- `cutoff` (60): "The handover states a low-water cutoff of at least 15 cm."
- `contact` (40): "The handover states an emergency contact phone number."

| Version | URL (after publish) | HTTP | Raw bytes | SHA-256 | Supporting line |
|---|---|---|---|---|---|
| v1 | `https://raw.githubusercontent.com/JWattjr/repair-refund-escrow-evidence/<commit1>/handover.md` | pending | 198 (local) | `517533f968fec6f83fa11a06c8f7fb6240d77558fc0d68bc47cd117b95d70037` | L7 `Low-water cutoff: 5 cm`; L12 `Emergency contact: TBD` |
| v2 | `…/<commit2>/handover.md` | pending | 199 (local) | `41bf06ac4f027ff393e1516b28ebd7909be3e0cc644efa53131c848ec604409c` | L7 `Low-water cutoff: 20 cm`; L12 `Emergency contact: TBD` |

v1 text (v2 differs only in `version 2` on line 1 and `20 cm` on line 7):

```
# Pump controller handover - version 1

Fictional demonstration fixture. No real device, site or person.

## Settings

Low-water cutoff: 5 cm
Restart delay: 30 s

## Support

Emergency contact: TBD
```

Buyer claims on v1:

- `cutoff`: allegation "The stated low-water cutoff is 5 cm, below the required 15 cm.",
  quoted line `Low-water cutoff: 5 cm`.
- `contact`: allegation "No emergency contact phone number is given; the field says TBD.",
  quoted line `Emergency contact: TBD`.

Intended outcome:

- R1: `cutoff` SUPPORTED, `contact` SUPPORTED.
- R2: `cutoff` REMEDIED (20 ≥ 15, and the quoted line is gone), `contact` UNREMEDIED (the line is
  unchanged, with no number anywhere).
- Settlement: supplier 60 released, buyer 40 refunded.

Each claim is checkable against the exact text: 5 < 15, 20 ≥ 15, and the file contains no digits
after "Emergency contact:". After publishing, record the real HTTP status and
`curl -s -o f -w "%{size_download}"` for each URL, and confirm the SHA-256 equals the table above.

Expected-failure transactions for the record:

- A second `file_claims` with a new criterion after round 1 is rejected.
- `finalize()` after settlement is rejected.

## 9. Comparison with close mechanisms

| Mechanism | Judgment | Participants | State changes | What this contract adds |
|---|---|---|---|---|
| **parametric-coverage-pool** (own, deployed `92e7800`, under review) | Does a status-page incident qualify? The model extracts severity/start/end with verbatim quotes; code derives QUALIFYING. | LPs (deposit/withdraw shares), policyholder (buy, claim) | policy OPEN → PAID / DENIED / EXPIRED; capital and exposure accounting | Two parties in opposition, two different judgments in sequence on two versions of one artifact, and a per-criterion split. Shared: fetch, fail-closed and full-compare plumbing only. |
| **calibrated-forecast-pool** (own, deployed `32bcc75`) | Each source is labeled HOLDS / CONTRADICTED / UNCLEAR for one question; code derives YES/NO/UNRESOLVABLE. | Forecasters (commit/reveal probabilities), anyone resolves | question OPEN → RESOLVED; Brier-scored pot allocation | The second round is conditioned on the first, scoped to established defects, on a new version. Honest overlap: the closed-label + UNCLEAR + code-derived-outcome pattern is the same design idiom. |
| **Semantic Milestone Matrix Oracle** | Each frozen criterion is labeled SATISFIED / NOT_SATISFIED / INCONCLUSIVE once; weighted score → PASS/FAIL. | Owner (adds/locks evidence), anyone resolves | OPEN → PASS / FAIL / INCONCLUSIVE | **Closest.** Round 1 alone plus a per-criterion payout would be a superficial variant of it. The difference rests entirely on round 2: a buyer-scoped allegation, a supplier response, a remedy judgment that compares v2 against a specific v1 defect, and the claim set frozen between rounds. The demo must show round 2, or the distinction is not demonstrated. |
| **QuestChain** | Each milestone is labeled ACHIEVED / FAILED / PENDING; a frozen DAG, bitmask and points; PENDING retries. | Owner (claims rewards), anyone resolves | OPEN → WAIT / CONTESTED / RESOLVED / VOID; one-time claim | No counterparty, no versions, no refunds. Similar: retry-on-unclear until a deadline. |
| **funded-change-order** (own) | Judges the scope impact of an amendment; all parties approve funding deltas. | Agreement parties | Baseline version changes prospectively | It changes the criteria; this contract forbids any change after round 1 and judges remedy against fixed criteria. |

**Verdict:** the plumbing is shared with every one of these projects. The distinct part is the
remedy judgment in round 2, scoped to the frozen round-1 findings, together with per-criterion
release or refund. It is not superficial, provided the live demo reaches round 2.

## 10. Open questions (need decisions before Phase 2)

1. **R1 UNCLEAR deadline default:** release to the supplier (proposed; the buyer must establish the
   defect), or refund to the buyer?
2. **Conflict with the approved behavior:** today, a round-1 `UNCERTAIN` is carried into repair and
   refunded if still open. The proposal changes this to retry, then the deadline default. Confirm?
3. **Conflict:** reduce repair versions from 1–3 to exactly one?
4. Remove the mutual cancellation (`request_cancellation`/`confirm_cancellation`) and the
   per-claim `evidence_url`?
5. Keep the R2 guard (`REMEDIED` → `UNCLEAR` if the quoted defect line is still present)? It is
   conservative: a supplier who fixes the issue but leaves the old line gets a refund at the
   deadline.
6. **Evidence host:** a new public repo `JWattjr/repair-refund-escrow-evidence` (proposed), or a
   `repair-refund-escrow/` folder in the existing public `genlayer-demo-evidence`?
7. The `repair-refund-escrow` repo is private. The workspace preference is to make it public for
   submission after a secret scan. Confirm for Phase 2.
