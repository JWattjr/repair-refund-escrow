# Submission draft (not submitted)

`RepairRefundEscrow` judges two different things on one versioned deliverable. Round 1: validators decide whether each buyer defect on version 1 is supported. Round 2: validators decide whether each established defect is remedied in the supplier's repair version. Each criterion's fixed allocation is then released or refunded exactly once, and nothing new can enter after round 1. Units are synthetic.

## Evidence entries

1. **GenLayer Explorer Contract (StudioNet):** https://explorer-studio.genlayer.com/address/0xB838F846aA1141F396Dbeb2c8c4b70273d363560
2. **Source repository:** https://github.com/JWattjr/repair-refund-escrow (deployed source: commit `0fbde3d4ee9cdab8227ec9740cf9d2d56b595d72`, `contracts/repair_refund_escrow.py`, 30,381 bytes, on-chain code matches)
3. **Live release record:** https://github.com/JWattjr/repair-refund-escrow/blob/master/docs/LIVE_RELEASE.md
4. **Demo evidence (commit-pinned):** https://github.com/JWattjr/repair-refund-escrow-evidence
5. **Round 1 judgment tx:** https://explorer-studio.genlayer.com/tx/0x44714caa5831969e31d1d77f20f63803f83fabd2209c19215d9e80054f9450ef
6. **Round 2 judgment tx:** https://explorer-studio.genlayer.com/tx/0x60ef35e634642d2ec6878b18724fa4e1a95be3d6c0c206170cfb02f78763d623

## Live result

Nine transactions finalized. Both judgments reached MAJORITY_AGREE (3 agree, 2 idle). Round 1 labeled both defects SUPPORTED. Round 2 labeled `cutoff` REMEDIED and `contact` UNREMEDIED. 60 units were released and 40 refunded; phase SETTLED; conservation holds. Two intentional rollbacks (a second claim batch, a finalize after settlement) were recorded.

## Comparison with the author's same-week projects

| Project | What validators judge | How it settles |
|---|---|---|
| parametric-coverage-pool | Literal incident facts from frozen status pages | Code checks severity, duration and overlap, then pays policyholders from underwriter collateral |
| calibrated-forecast-pool | One yes/no question from frozen sources | Committed probabilities are revealed, and Brier scores divide the pot |
| **repair-refund-escrow** | Round 1: is each buyer defect supported on v1? Round 2: is each established defect remedied in v2? | Each criterion's allocation is released or refunded once from its two-round state |

All three share the same plumbing: closed label sets, UNCLEAR never pays, code-derived outcomes and full canonical validator comparison. The distinct part here is round 2, a remedy judgment between two pinned versions against frozen round-1 findings. Neither of the other two projects has a versioned deliverable or a repair step. Against outside comparators, round 1 alone resembles Semantic Milestone Matrix Oracle (see `docs/MECHANISM_DIFFERENTIATION.md`).

## This does not prove

Adversarial consensus security, real validator behavior beyond one honest-network run, deadline-default paths or retry limits on StudioNet (covered only by local mocked tests), independent parties (both keys belong to one operator), real work quality, or real asset custody. No Portal submission or score is claimed.
