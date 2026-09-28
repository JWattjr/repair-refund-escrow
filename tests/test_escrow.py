import json

import pytest


SDK = "v0.6.0-rc5"
NOW = "2030-01-01T12:00:00Z"
DELIVERY_DEADLINE = "2030-01-05T00:00:00Z"
FINAL_DEADLINE = "2030-01-20T00:00:00Z"
DELIVERABLE_V1 = "https://supplier.example.org/station-v1"
REPAIR_V2 = "https://supplier.example.org/station-repair-v2"
EVIDENCE_QUALITY = "https://buyer.example.org/rain-test"
EVIDENCE_CALIBRATION = "https://buyer.example.org/calibration-check"
CRITERIA = [
    {"criterion_id": "weatherproofing", "description": "The enclosure withstands the documented outdoor rain exposure without water reaching electronics.", "allocation_units": 60},
    {"criterion_id": "calibration", "description": "The conductivity sensor readings at 25°C stay within ±2% of the 1,413 µS/cm calibration standard.", "allocation_units": 40},
]


def llm(value) -> str:
    """The direct mock decodes once; the v0.6 SDK then parses JSON text."""
    return json.dumps(json.dumps(value))


def deploy(direct_vm, direct_deploy, direct_buyer, direct_supplier, **overrides):
    args = {
        "supplier": direct_supplier,
        "brief": "Build and deliver a maintainable solar-powered water testing station for rural clinics, meeting the agreed safety and performance criteria.",
        "criteria_json": json.dumps(CRITERIA),
        "total_units": 100,
        "delivery_deadline_iso": DELIVERY_DEADLINE,
        "final_resolution_deadline_iso": FINAL_DEADLINE,
        "review_window_seconds": 86400,
        "max_repair_versions": 1,
    }
    args.update(overrides)
    direct_vm.sender = direct_buyer
    direct_vm.warp(NOW)
    return direct_deploy(
        "contracts/repair_refund_escrow.py",
        args["supplier"],
        args["brief"],
        args["criteria_json"],
        args["total_units"],
        args["delivery_deadline_iso"],
        args["final_resolution_deadline_iso"],
        args["review_window_seconds"],
        args["max_repair_versions"],
        sdk_version=SDK,
    )


def accept_terms(contract, direct_vm, supplier):
    digest = contract.get_terms()["terms_digest"]
    with direct_vm.prank(supplier):
        return contract.accept_terms(digest)


def submit_initial(contract, direct_vm, supplier, url=DELIVERABLE_V1):
    with direct_vm.prank(supplier):
        return contract.submit_initial_deliverable(
            url,
            "Versioned delivery page describing the assembled water station and test results.",
        )


def claims():
    return json.dumps([
        {"criterion_id": "weatherproofing", "allegation": "Water entered the enclosure during the agreed rain exposure test.", "evidence_url": EVIDENCE_QUALITY},
        {"criterion_id": "calibration", "allegation": "The conductivity sensor reading exceeded the agreed calibration tolerance.", "evidence_url": EVIDENCE_CALIBRATION},
    ])


def mock_web(direct_vm, body="The deliverable and evidence pages are available with dated test results."):
    direct_vm.mock_web(r".*", {"status": 200, "body": body})


def submit_two_defects(contract, direct_vm, direct_buyer, findings=None):
    if findings is None:
        findings = [
            {"criterion_id": "weatherproofing", "finding": "SUPPORTED", "citations": [DELIVERABLE_V1, EVIDENCE_QUALITY]},
            {"criterion_id": "calibration", "finding": "SUPPORTED", "citations": [DELIVERABLE_V1, EVIDENCE_CALIBRATION]},
        ]
    mock_web(direct_vm)
    direct_vm.mock_llm(r"DEFECT CLAIM REVIEW", llm({"results": findings}))
    with direct_vm.prank(direct_buyer):
        return contract.submit_defects(1, claims())


def test_one_defect_is_repaired_and_the_other_allocation_is_refunded(
    direct_vm, direct_deploy, direct_owner, direct_alice
):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    terms = contract.get_terms()
    assert terms["remedy_rule"].startswith("release accepted or remedied")
    assert contract.get_accounting()["escrow_units"] == 100
    with direct_vm.prank(direct_alice):
        accepted = contract.accept_terms(terms["terms_digest"])
    assert accepted["phase"] == "AWAITING_INITIAL_DELIVERY"
    submit_initial(contract, direct_vm, direct_alice)
    result = submit_two_defects(contract, direct_vm, direct_owner)
    assert result["phase"] == "REPAIR_REQUIRED"
    assert result["open_defect_count"] == 2
    assert direct_vm.run_validator()

    direct_vm.clear_mocks()
    with direct_vm.prank(direct_alice):
        repair = contract.submit_repair_version(
            REPAIR_V2,
            "Replaced the enclosure gasket and recalibrated the conductivity sensor.",
        )
    assert repair["deliverable_version"] == 2
    assert repair["repair_version"] == 1
    mock_web(direct_vm, "Repair page shows a sealed enclosure; calibration evidence remains outside tolerance.")
    direct_vm.mock_llm(r"REPAIR VERSION REVIEW", llm({"results": [
        {"criterion_id": "weatherproofing", "finding": "REMEDIED", "citations": [REPAIR_V2, EVIDENCE_QUALITY]},
        {"criterion_id": "calibration", "finding": "UNRESOLVED", "citations": [REPAIR_V2, EVIDENCE_CALIBRATION]},
    ]}))
    reviewed = contract.review_repair_version(2)
    assert reviewed["phase"] == "SETTLED_WITH_REFUND"
    assert reviewed["released_units"] == 60
    assert reviewed["refunded_units"] == 40
    assert direct_vm.run_validator()
    assert contract.get_criterion_state("weatherproofing")["state"] == "REMEDIED"
    assert contract.get_criterion_state("calibration")["state"] == "REFUNDED_UNRESOLVED"
    assert contract.get_claim("weatherproofing")["repair_history"][0]["finding"] == "REMEDIED"
    assert contract.get_claim("calibration")["repair_history"][0]["finding"] == "UNRESOLVED"
    assert contract.get_accounting() == {
        "total_units": 100,
        "escrow_units": 0,
        "released_units": 60,
        "refunded_units": 40,
        "conserved": True,
        "settlement_done": True,
    }
    with direct_vm.expect_revert("no matching repair version"):
        contract.review_repair_version(2)


def test_unsupported_claim_releases_its_allocation_and_rejects_late_expansion(
    direct_vm, direct_deploy, direct_owner, direct_alice
):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    accept_terms(contract, direct_vm, direct_alice)
    submit_initial(contract, direct_vm, direct_alice)
    findings = [
        {"criterion_id": "weatherproofing", "finding": "UNSUPPORTED", "citations": [DELIVERABLE_V1]},
        {"criterion_id": "calibration", "finding": "UNSUPPORTED", "citations": [DELIVERABLE_V1]},
    ]
    result = submit_two_defects(contract, direct_vm, direct_owner, findings)
    assert result["released_units"] == 100
    assert result["refunded_units"] == 0
    assert contract.get_accounting()["conserved"] is True
    with direct_vm.prank(direct_owner):
        with direct_vm.expect_revert("only the buyer may submit defects"):
            contract.submit_defects(1, claims())


def test_malformed_and_disagreeing_defect_assessments_do_not_change_claim_state(
    direct_vm, direct_deploy, direct_owner, direct_alice
):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    accept_terms(contract, direct_vm, direct_alice)
    submit_initial(contract, direct_vm, direct_alice)
    mock_web(direct_vm)
    direct_vm.mock_llm(r"DEFECT CLAIM REVIEW", llm({"results": [
        {"criterion_id": "weatherproofing", "finding": "SUPPORTED", "citations": [DELIVERABLE_V1]},
        {"criterion_id": "calibration", "finding": "SUPPORTED", "citations": [DELIVERABLE_V1]},
    ], "extra": "untrusted"}))
    with direct_vm.prank(direct_owner):
        with direct_vm.expect_revert("unknown or missing fields"):
            contract.submit_defects(1, claims())
    assert contract.get_terms()["phase"] == "AWAITING_CLAIMS"
    assert contract.get_accounting()["escrow_units"] == 100
    assert contract.get_criterion_state("weatherproofing")["state"] == "UNREVIEWED"

    direct_vm.clear_mocks()
    honest_rows = [
        {"criterion_id": "weatherproofing", "finding": "SUPPORTED", "citations": [DELIVERABLE_V1]},
        {"criterion_id": "calibration", "finding": "SUPPORTED", "citations": [DELIVERABLE_V1]},
    ]
    result = submit_two_defects(contract, direct_vm, direct_owner, honest_rows)
    assert result["phase"] == "REPAIR_REQUIRED"
    assert direct_vm.run_validator()
    disagreement = {
        "snapshot_digest": result["review_digest"],
        "results": json.loads(json.dumps(honest_rows)),
    }
    disagreement["results"][0]["finding"] = "UNSUPPORTED"
    assert direct_vm.run_validator(leader_result=disagreement) is False


@pytest.mark.parametrize("web_response", [
    pytest.param({"status": 503, "body": b"service unavailable"}, id="non-200"),
    pytest.param({"status": 200, "body": b""}, id="empty"),
    pytest.param({"status": 200, "body": b"x" * 5001}, id="oversized"),
    pytest.param({"status": 200, "body": b"\xff"}, id="invalid-utf8"),
])
def test_unavailable_claim_evidence_remains_held_and_can_be_refunded_at_final_deadline(
    direct_vm, direct_deploy, direct_owner, direct_alice, web_response
):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    accept_terms(contract, direct_vm, direct_alice)
    submit_initial(contract, direct_vm, direct_alice)
    direct_vm.mock_web(r".*", web_response)
    direct_vm.mock_llm(r"DEFECT CLAIM REVIEW", llm({"results": [
        {"criterion_id": "weatherproofing", "finding": "UNCERTAIN", "citations": []},
        {"criterion_id": "calibration", "finding": "UNCERTAIN", "citations": []},
    ]}))
    result = contract.submit_defects(1, claims())
    assert result["phase"] == "REPAIR_REQUIRED"
    assert contract.get_accounting()["escrow_units"] == 100
    with direct_vm.expect_revert("final resolution deadline has not passed"):
        contract.expire_final_resolution()
    direct_vm.warp(FINAL_DEADLINE)
    with direct_vm.expect_revert("final resolution deadline has not passed"):
        contract.expire_final_resolution()
    direct_vm.warp("2030-01-20T00:00:01Z")
    expired = contract.expire_final_resolution()
    assert expired["refunded_units"] == 100
    assert contract.get_accounting()["conserved"] is True


def test_terms_require_supplier_acceptance_and_cancellation_is_mutual(
    direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob
):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    digest = contract.get_terms()["terms_digest"]
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("only the named supplier"):
            contract.accept_terms(digest)
    with direct_vm.prank(direct_alice):
        with direct_vm.expect_revert("terms digest does not match"):
            contract.accept_terms("sha256:" + "0" * 64)
        contract.accept_terms(digest)
    contract.request_cancellation()
    with direct_vm.prank(direct_bob):
        with direct_vm.expect_revert("only the supplier"):
            contract.confirm_cancellation()
    with direct_vm.prank(direct_alice):
        cancelled = contract.confirm_cancellation()
    assert cancelled["phase"] == "CANCELLED"
    assert cancelled["refunded_units"] == 100
    assert contract.get_accounting()["conserved"] is True


def test_no_delivery_after_frozen_deadline_refunds_escrow(
    direct_vm, direct_deploy, direct_owner, direct_alice
):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    accept_terms(contract, direct_vm, direct_alice)
    direct_vm.warp(DELIVERY_DEADLINE)
    with direct_vm.expect_revert("initial delivery is not overdue"):
        contract.expire_initial_delivery()
    direct_vm.warp("2030-01-05T00:00:01Z")
    result = contract.expire_initial_delivery()
    assert result["phase"] == "REFUNDED_NO_DELIVERY"
    assert result["refunded_units"] == 100
    assert contract.get_accounting()["conserved"] is True


def test_no_supplier_acceptance_by_delivery_deadline_refunds_escrow(
    direct_vm, direct_deploy, direct_owner, direct_alice
):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    direct_vm.warp("2030-01-05T00:00:01Z")
    result = contract.expire_initial_delivery()
    assert result["phase"] == "REFUNDED_NO_DELIVERY"
    assert result["refunded_units"] == 100
    assert contract.get_accounting()["conserved"] is True


def test_missed_review_deadline_accepts_all_criteria_without_claim_expansion(
    direct_vm, direct_deploy, direct_owner, direct_alice
):
    contract = deploy(direct_vm, direct_deploy, direct_owner, direct_alice)
    accept_terms(contract, direct_vm, direct_alice)
    submit_initial(contract, direct_vm, direct_alice)
    direct_vm.warp("2030-01-02T12:00:00Z")
    with direct_vm.expect_revert("review deadline has not passed"):
        contract.close_review_without_claims()
    direct_vm.warp("2030-01-02T12:00:01Z")
    result = contract.close_review_without_claims()
    assert result["released_units"] == 100
    assert result["refunded_units"] == 0
    assert contract.get_terms()["phase"] == "SETTLED"


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"total_units": 0}, "escrow budget must be positive"),
        ({"criteria_json": json.dumps([{**CRITERIA[0], "allocation_units": 99}, CRITERIA[1]])}, "allocations must sum"),
        ({"review_window_seconds": 30}, "review window must be"),
        ({"max_repair_versions": 4}, "repair versions must be"),
    ],
)
def test_constructor_rejects_unfunded_allocations_or_unbounded_policy(
    direct_vm, direct_deploy, direct_owner, direct_alice, overrides, message
):
    with direct_vm.expect_revert(message):
        deploy(direct_vm, direct_deploy, direct_owner, direct_alice, **overrides)
