# Live StudioNet release, 2026-11-12

Source commit `0fbde3d4ee9cdab8227ec9740cf9d2d56b595d72`; contract file Git blob `83dc7a5af1c839dde8db3fcb597f67afa450ada1`; 30,381 bytes. The driver deployed `git show HEAD:contracts/repair_refund_escrow.py` from a clean `contracts/` tree. Record: [deployments/studionet-live-run.json](../deployments/studionet-live-run.json) (script: `scripts/live_run.mjs`; final readbacks by `scripts/readback.mjs`, read-only, after a transient RPC reset interrupted the in-script reads; no write was repeated).

## Separate Explorer contract evidence

**Evidence type: GenLayer Explorer Contract.** [Repair refund escrow](https://explorer-studio.genlayer.com/address/0xB838F846aA1141F396Dbeb2c8c4b70273d363560), StudioNet, address `0xB838F846aA1141F396Dbeb2c8c4b70273d363560`. The rendered page was checked: creator `0xdB433f...f79c92`, deploy tx `0xb80f4281...4c071de2`, 9 transactions. Transaction and source links are additional, not replacements.

## Demo evidence (public, commit-pinned, anonymous HTTP 200)

| Version | URL | Raw bytes | SHA-256 |
|---|---|---|---|
| v1 | `https://raw.githubusercontent.com/JWattjr/repair-refund-escrow-evidence/3286314dd6492df572823a454e8a777640f9026f/handover.md` | 198 | `517533f968fec6f83fa11a06c8f7fb6240d77558fc0d68bc47cd117b95d70037` |
| v2 | `https://raw.githubusercontent.com/JWattjr/repair-refund-escrow-evidence/50bbb9ebb65ed37394f84f8ed60c4351f19b381c/handover.md` | 199 | `41bf06ac4f027ff393e1516b28ebd7909be3e0cc644efa53131c848ec604409c` |

Sizes are curl `size_download`. The on-chain judgment records the same byte counts and SHA-256 values, so validators fetched identical bytes.

## Result

- Round 1 (`judge_defects`): `cutoff` SUPPORTED (line `Low-water cutoff: 5 cm`), `contact` SUPPORTED (line `Emergency contact: TBD`). Input digest `sha256:9cac6fb0...a544`.
- Round 2 (`judge_repair`): `cutoff` REMEDIED (`Low-water cutoff: 20 cm`), `contact` UNREMEDIED (line unchanged). Input digest `sha256:2ab43377...8604`.
- Final: `cutoff` RELEASED 60, `contact` REFUNDED 40; phase SETTLED; escrow 0, released 60, refunded 40, conserved true; one attempt per round.
- The deployed bytes equal the committed source (SHA-256 match).

## Transactions (all FINALIZED, consensus MAJORITY_AGREE)

| Step | Hash | Leader execution |
|---|---|---|
| deploy | [0xb80f4281...1de2](https://explorer-studio.genlayer.com/tx/0xb80f42818edb60bf03970b75d6ca89d8bf71cdeb5ef88ef259b239564c071de2) | SUCCESS |
| accept_terms | [0x25226904...b540](https://explorer-studio.genlayer.com/tx/0x252269041ef38693a45fa81ad8280a23bc0bacc0a78d49f776eaf246d61db540) | SUCCESS |
| submit_delivery (v1) | [0xae9622c0...1f72](https://explorer-studio.genlayer.com/tx/0xae9622c09e383fc45a201c965971f1dcc3d326f49796689003289996ab471f72) | SUCCESS |
| file_claims | [0x52db68f7...5d5d](https://explorer-studio.genlayer.com/tx/0x52db68f78c4e1730f819acd209e1a9a546540a995c5384a91f2b3ed7f02f5d5d) | SUCCESS |
| judge_defects (round 1) | [0x44714caa...50ef](https://explorer-studio.genlayer.com/tx/0x44714caa5831969e31d1d77f20f63803f83fabd2209c19215d9e80054f9450ef) | SUCCESS |
| submit_repair (v2) | [0xe3008bd4...b7d1](https://explorer-studio.genlayer.com/tx/0xe3008bd461d3a02d1d99bec3ecf44c83e9e8a057fd87ffbfc3fb17cdcf5ab7d1) | SUCCESS |
| judge_repair (round 2) | [0x60ef35e6...d623](https://explorer-studio.genlayer.com/tx/0x60ef35e634642d2ec6878b18724fa4e1a95be3d6c0c206170cfb02f78763d623) | SUCCESS |
| expected rollback: second claim batch | [0x72ce699e...3379](https://explorer-studio.genlayer.com/tx/0x72ce699e241a7e2b8051251f141573b8c72871274333157ff2573735fae83379) | ERROR (expected) |
| expected rollback: finalize after settlement | [0x6b68a2fb...4c39](https://explorer-studio.genlayer.com/tx/0x6b68a2fb9f9996a50b55515e1d7f717ed11f19724bc957ed191d5ec86f364c39) | ERROR (expected) |

Vote splits per transaction (some validators IDLE) are in the JSON record. The two judgment transactions had 3 AGREE and 2 IDLE each.

## Not demonstrated

One honest-network run only. Deadline-default paths, retry limits and adversarial leaders are covered by local mocked tests, not on StudioNet. Both parties' keys belong to the same operator, so this does not show independent parties. The previous deployment `0xbb0DD15b1E0C0b747332063E38A3a1356d44E079` is a different, superseded source and is not evidence for this revision. Units are synthetic.
