# Submission draft (not submitted)

`RepairRefundEscrow` judges two different things on one versioned deliverable. Round 1: validators decide whether each buyer defect on version 1 is supported. Round 2: validators decide whether each established defect is remedied in the supplier's repair version. Each criterion's fixed allocation is then released or refunded exactly once, and nothing new can enter after round 1. Units are synthetic.

**Evidence entries**
- GenLayer Explorer Contract (StudioNet): https://explorer-studio.genlayer.com/address/0xB838F846aA1141F396Dbeb2c8c4b70273d363560
- Source: the public contract repository, commit recorded in `docs/LIVE_RELEASE.md`
- Demo evidence: two commit-pinned files in https://github.com/JWattjr/repair-refund-escrow-evidence
- Transactions and receipts: `deployments/studionet-live-run.json` and `docs/LIVE_RELEASE.md`

**Live result:** nine transactions finalized. Both judgments reached MAJORITY_AGREE. Round 1 labeled both defects SUPPORTED; round 2 labeled `cutoff` REMEDIED and `contact` UNREMEDIED; 60 units released and 40 refunded; phase SETTLED, conserved. Two intentional rollbacks (a second claim batch, a finalize after settlement) were recorded.

**This does not prove:** adversarial consensus security, real validator behavior beyond one honest-network run, deadline-default paths on StudioNet (covered only by local mocked tests), real work quality, or real asset custody. No Portal submission or score is claimed.
