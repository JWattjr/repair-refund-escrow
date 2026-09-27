# Complete demo sequence

Run the executable direct-mode scenario:

```powershell
python -m pytest tests/test_escrow.py::test_one_defect_is_repaired_and_the_other_allocation_is_refunded
```

1. The buyer deploys with two criteria allocated 60 and 40 demo units. The full 100-unit example escrow is reserved, and the terms digest includes the exact remedy policy.
2. The named supplier accepts that digest, then submits deliverable version 1.
3. The buyer alleges one rain-seal defect and one calibration defect against their named criteria. GenLayer finds both supported. The allocations remain held and the phase becomes `REPAIR_REQUIRED`.
4. The supplier submits repair version 2. Validators independently assess only those two existing defects.
5. The rain seal is found remedied; calibration remains unresolved. The contract releases 60 units to the supplier and refunds 40 to the buyer.
6. The claim history remains queryable with each repair finding, and replaying review cannot settle again.

Tests use mocks and synthetic units. They demonstrate the contract transition, not real work quality or asset transfer.
