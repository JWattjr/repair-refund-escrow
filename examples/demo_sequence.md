# Demo sequence (local direct mode)

```powershell
python -m pytest tests/test_repair_escrow.py::test_full_lifecycle_releases_remedied_and_refunds_unremedied
```

Planned live evidence (not yet published): `handover.md` in a public repo, v1 and v2 as two pinned commits
(198 and 199 bytes; SHA-256 `517533f9...70037` and `41bf06ac...4409c`; see `docs/DESIGN_PROPOSAL.md` section 8).

1. Buyer deploys: `cutoff` 60 units ("at least 15 cm") and `contact` 40 units ("emergency contact phone number").
2. Supplier accepts the terms digest and submits v1 (`Low-water cutoff: 5 cm`, `Emergency contact: TBD`).
3. Buyer files two claims, each with a verbatim quoted line. Anyone calls `judge_defects`: both `SUPPORTED`.
4. Supplier submits v2 (`Low-water cutoff: 20 cm`, contact unchanged). Anyone calls `judge_repair`:
   `cutoff` `REMEDIED` (released 60), `contact` `UNREMEDIED` (refunded 40). Phase `SETTLED`.
5. Replays (`judge_repair`, `finalize`, `file_claims`) revert. A new allegation after round 1 is rejected.
