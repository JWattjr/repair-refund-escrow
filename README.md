# Repair Refund Escrow

`RepairRefundEscrow` stores a supplier's versioned deliverables and gives the supplier a fixed number of chances to repair buyer-claimed defects. At formation, the buyer names the supplier, freezes the brief, criterion-level payment allocations, deadlines, review window, and repair limit. The supplier must accept the exact terms digest before delivery.

The buyer may submit at most one claim per criterion against the current initial version. GenLayer compares each allegation with the frozen criterion, deliverable reference, and evidence reference. Unsupported claims accept that criterion; supported and uncertain findings stay open for repair. Validators independently fetch and assess the same snapshot. Later repair versions can close only those already established concerns, so the buyer cannot add late criteria or defects.

Independent model review is needed because whether prose in a deliverable and its cited evidence establishes a defect cannot be reduced to a numeric field or the parties' consent alone; deterministic code keeps criterion scope, version binding, and allocation arithmetic fixed. The example sets an explicit ±2% tolerance around the 1,413 µS/cm reference at 25°C.

At settlement, the full allocation for an accepted or remedied criterion is released to the supplier. The allocation for each defect still open after the repair limit or final deadline is refunded to the buyer. Deterministic accounting prevents any allocation from being released or refunded twice.

## Toolchain

The contract pins `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`, accepted by the installed GenVM linter. The fallback runner finalized a trivial StudioNet deployment and write/read-back probe; this project contract has not yet been deployed. `requirements.txt` pins the locally installed v0.6 RC test toolchain.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
genvm-lint lint contracts/repair_refund_escrow.py
genvm-lint validate contracts/repair_refund_escrow.py
genvm-lint schema contracts/repair_refund_escrow.py --output contracts/abi.json
python -m pytest
```

Direct tests mock web and model responses. They do not establish live consensus, network finality, or remote runner availability.

## Lifecycle

1. The buyer deploys with a named supplier, brief, criteria with positive allocations summing exactly to the escrow budget, an initial delivery deadline, a final resolution deadline, a bounded claim window, and a repair-version limit. These terms and the remedy rule are hashed.
2. The supplier accepts the exact `terms_digest`. The buyer and supplier can cancel together before delivery. If the supplier does not accept or deliver by the frozen deadline, anyone may close the escrow for a full buyer refund.
3. The supplier submits version 1 with a bounded HTTPS deliverable reference and summary. The contract opens a review window that cannot pass the final resolution deadline.
4. The buyer submits zero or more criterion-specific defect claims, each with an allegation and evidence reference. GenLayer independently assesses only the listed claims. Unsupported allegations accept their criteria; supported or uncertain claims stay open; unclaimed criteria are accepted.
5. For open claims, the supplier may submit up to the frozen number of complete repair versions. A permissionless review assesses each version against the exact established defects. It cannot create new defect claims.
6. Fully accepted or remedied work settles to the supplier. After the repair limit or final resolution deadline, accepted and remedied criterion allocations release to the supplier and each still-open criterion allocation returns to the buyer.

## API

Writes are `accept_terms`, `reject_terms`, `request_cancellation`, `confirm_cancellation`, `submit_initial_deliverable`, `submit_defects`, `close_review_without_claims`, `submit_repair_version`, `review_repair_version`, `expire_initial_delivery`, and `expire_final_resolution`. Views are `get_terms`, `get_submission`, `get_claim`, `get_criterion_state`, and `get_accounting`. The generated ABI is [contracts/abi.json](contracts/abi.json).

The constructor example is [examples/constructor.json](examples/constructor.json), and the focused full lifecycle is [examples/demo_sequence.md](examples/demo_sequence.md).

## Bounds and failure behavior

The contract supports up to 8 acceptance criteria and claims, at most 3 repair versions, bounded text and evidence, and HTTPS URLs with public-DNS hostname syntax. Model output must bind to the frozen terms, current submission, criterion IDs, and fetched evidence snapshot. Malformed output, invented citations, missing required evidence, or validator disagreement cannot authorize a settlement. Unavailable claim or repair evidence remains uncertain and keeps the allocation held until repair or final deadline.

The ledger uses demonstration units created in contract state; no real asset is transferred or held. Fetch does not prove publisher identity, signatures, redirect safety, DNS resolution, or freshness. The model can misread technical evidence. See [mechanism differentiation](docs/MECHANISM_DIFFERENTIATION.md), [test matrix](docs/TEST_MATRIX.md), [security notes](docs/SECURITY_NOTES.md), and the [undeployed submission draft](SUBMISSION_DRAFT.md).
