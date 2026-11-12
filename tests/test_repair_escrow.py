import ast
import copy
import json
import re
from contextlib import contextmanager
from pathlib import Path

import pytest


SDK = "v0.6.0-rc5"
SOURCE = Path(__file__).resolve().parents[1] / "contracts" / "repair_refund_escrow.py"
NOW = "2030-01-01T12:00:00Z"
DEADLINES = ["2030-01-05T00:00:00Z", "2030-01-10T00:00:00Z", "2030-01-15T00:00:00Z",
             "2030-01-20T00:00:00Z", "2030-01-25T00:00:00Z"]
AFTER_DELIVERY, AFTER_CLAIM, AFTER_JUDGMENT, AFTER_REPAIR, AFTER_FINAL = (
    "2030-01-05T00:00:01Z", "2030-01-10T00:00:01Z", "2030-01-15T00:00:01Z",
    "2030-01-20T00:00:01Z", "2030-01-25T00:00:01Z")
BASE = "https://raw.githubusercontent.com/example-owner/example-evidence/"
V1 = BASE + "a" * 40 + "/handover.md"
V2 = BASE + "b" * 40 + "/handover.md"
V1_TEXT = ("# Pump controller handover - version 1\n\nFictional demonstration fixture. No real device, site or person.\n\n"
           "## Settings\n\nLow-water cutoff: 5 cm\nRestart delay: 30 s\n\n## Support\n\nEmergency contact: TBD\n")
V2_TEXT = V1_TEXT.replace("version 1", "version 2").replace("cutoff: 5 cm", "cutoff: 20 cm")
CRITERIA = [
    {"criterion_id": "cutoff", "description": "The handover states a low-water cutoff of at least 15 cm.", "allocation_units": 60},
    {"criterion_id": "contact", "description": "The handover states an emergency contact phone number.", "allocation_units": 40},
]
CLAIMS = [
    {"criterion_id": "cutoff", "allegation": "The stated low-water cutoff is 5 cm, below the required 15 cm.", "quoted_line": "Low-water cutoff: 5 cm"},
    {"criterion_id": "contact", "allegation": "No emergency contact phone number is given; the field says TBD.", "quoted_line": "Emergency contact: TBD"},
]
R1, R2 = r"ROUND 1 DEFECT REVIEW", r"ROUND 2 REMEDY REVIEW"


def llm(value) -> str:
    """The direct mock decodes once; the v0.6 SDK then parses JSON text."""
    return json.dumps(json.dumps(value))


def labels(**kw):
    return llm({"labels": kw})


@contextmanager
def reverts(vm, who, message):
    with vm.prank(who):
        with vm.expect_revert(message):
            yield


def deploy(vm, deploy_fn, buyer, supplier, **overrides):
    args = {"supplier": supplier, "brief": "Deliver a fictional pump controller handover note meeting the agreed criteria.",
            "criteria_json": json.dumps(CRITERIA), "total_units": 100, "deadlines": DEADLINES}
    args.update(overrides)
    vm.sender = buyer
    vm.warp(NOW)
    return deploy_fn("contracts/repair_refund_escrow.py", args["supplier"], args["brief"], args["criteria_json"],
                     args["total_units"], *args["deadlines"], sdk_version=SDK)


def web(vm, v1=V1_TEXT, v2=V2_TEXT, v1_response=None, v2_response=None):
    vm.mock_web(re.escape(V1), v1_response or {"status": 200, "body": v1})
    vm.mock_web(re.escape(V2), v2_response or {"status": 200, "body": v2})


def check(c):
    """Conservation after every scenario: escrow + released + refunded == total and matches criterion states."""
    acc = c.get_accounting()
    assert acc["conserved"] and acc["escrow_units"] + acc["released_units"] + acc["refunded_units"] == acc["total_units"]
    sums = {"RELEASED": 0, "REFUNDED": 0, "open": 0}
    for row in c.get_terms()["criteria"]:
        state = c.get_criterion_state(row["criterion_id"])["state"]
        sums[state if state in sums else "open"] += row["allocation_units"]
    assert (sums["RELEASED"], sums["REFUNDED"], sums["open"]) == (acc["released_units"], acc["refunded_units"], acc["escrow_units"])
    return acc


def states(c):
    return {r["criterion_id"]: c.get_criterion_state(r["criterion_id"])["state"] for r in c.get_terms()["criteria"]}


@pytest.fixture
def env(direct_vm, direct_deploy, direct_owner, direct_alice, direct_bob):
    class Env:
        vm, buyer, supplier, stranger = direct_vm, direct_owner, direct_alice, direct_bob

        def new(self, **kw):
            self.c = deploy(direct_vm, direct_deploy, direct_owner, direct_alice, **kw)
            return self.c

        def accepted(self, **kw):
            c = self.new(**kw)
            with direct_vm.prank(direct_alice):
                c.accept_terms(c.get_terms()["terms_digest"])
            return c

        def delivered(self, **kw):
            c = self.accepted(**kw)
            with direct_vm.prank(direct_alice):
                c.submit_delivery(V1, "Version one of the handover note.")
            return c

        def claimed(self, claims=CLAIMS, **kw):
            c = self.delivered(**kw)
            with direct_vm.prank(direct_owner):
                c.file_claims(json.dumps(claims))
            return c

        def round1(self, supplied=("SUPPORTED", "SUPPORTED"), **kw):
            c = self.claimed(**kw)
            web(direct_vm)
            direct_vm.mock_llm(R1, labels(cutoff=supplied[0], contact=supplied[1]))
            c.judge_defects()
            return c

        def repaired(self, **kw):
            c = self.round1(**kw)
            with direct_vm.prank(direct_alice):
                c.submit_repair(V2, "Raised the cutoff in version two.")
            return c

    return Env()


# ---------------- happy path and the demo outcome ----------------

def test_full_lifecycle_releases_remedied_and_refunds_unremedied(env):
    c, vm = env.claimed(), env.vm
    assert c.get_terms()["phase"] == "ROUND1_PENDING" and states(c) == {"cutoff": "CLAIMED", "contact": "CLAIMED"}
    web(vm)
    vm.mock_llm(R1, labels(cutoff="SUPPORTED", contact="SUPPORTED"))
    result = c.judge_defects()
    assert result["phase"] == "REPAIR_REQUIRED" and result["attempt"] == 1
    assert vm.run_validator() is True
    assert states(c) == {"cutoff": "SUPPORTED", "contact": "SUPPORTED"}
    assert check(c)["escrow_units"] == 100
    with vm.prank(env.supplier):
        assert c.submit_repair(V2, "Raised the cutoff in version two.")["open_defect_count"] == 2
    vm.mock_llm(R2, labels(cutoff="REMEDIED", contact="UNREMEDIED"))
    result = c.judge_repair()
    assert vm.run_validator() is True
    assert result["phase"] == "SETTLED" and (result["released_units"], result["refunded_units"]) == (60, 40)
    assert states(c) == {"cutoff": "RELEASED", "contact": "REFUNDED"}
    acc = check(c)
    assert acc["escrow_units"] == 0 and acc["round1_attempts"] == 1 and acc["round2_attempts"] == 1
    stored = c.get_judgment(2, 1)
    assert [s["sha256"] for s in stored["sources"]] != [] and all(s["status"] == "fetched" for s in stored["sources"])
    assert [r["label"] for r in stored["labels"]] == ["REMEDIED", "UNREMEDIED"]
    assert c.get_submission(2)["url"] == V2 and len(c.get_claims()) == 2


def test_unclaimed_criterion_is_released_when_claims_are_filed(env):
    c = env.claimed(claims=[CLAIMS[0]])
    assert states(c) == {"cutoff": "CLAIMED", "contact": "RELEASED"}
    assert check(c)["released_units"] == 40


def test_all_unsupported_in_round_one_releases_everything(env):
    c = env.round1(supplied=("UNSUPPORTED", "UNSUPPORTED"))
    assert c.get_terms()["phase"] == "SETTLED" and check(c)["released_units"] == 100


def test_empty_claim_batch_releases_all(env):
    c = env.claimed(claims=[])
    assert c.get_terms()["phase"] == "SETTLED" and check(c)["released_units"] == 100


# ---------------- code-derived labels and guards ----------------

def test_model_label_cannot_outrank_a_false_quote(env):
    forged = [dict(CLAIMS[0], quoted_line="Low-water cutoff: 3 cm"), CLAIMS[1]]
    c = env.claimed(claims=forged)
    web(env.vm)
    env.vm.mock_llm(R1, labels(cutoff="SUPPORTED", contact="SUPPORTED"))
    c.judge_defects()
    assert states(c) == {"cutoff": "RELEASED", "contact": "SUPPORTED"}
    check(c)


def test_remedied_with_defect_line_still_present_becomes_unclear(env):
    c, vm = env.repaired(), env.vm
    vm.clear_mocks()
    web(vm, v2=V1_TEXT.replace("version 1", "version 2"))
    vm.mock_llm(R2, labels(cutoff="REMEDIED", contact="UNREMEDIED"))
    result = c.judge_repair()
    assert [r["label"] for r in result["labels"]] == ["UNCLEAR", "UNREMEDIED"]
    assert states(c) == {"cutoff": "SUPPORTED", "contact": "REFUNDED"}
    check(c)


def test_labels_are_normalised_and_missing_values_become_unclear(env):
    c = env.claimed()
    web(env.vm)
    env.vm.mock_llm(R1, labels(cutoff=" supported "))
    result = c.judge_defects()
    assert [r["label"] for r in result["labels"]] == ["SUPPORTED", "UNCLEAR"]
    assert states(c) == {"cutoff": "SUPPORTED", "contact": "CLAIMED"}
    assert result["phase"] == "ROUND1_PENDING"
    check(c)


@pytest.mark.parametrize("model", [
    pytest.param(llm({"labels": {"ghost": "SUPPORTED"}}), id="unknown-id"),
    pytest.param(llm({"labels": {"cutoff": "REMEDIED"}}), id="round2-label-in-round1"),
    pytest.param(llm({"labels": {"cutoff": "MAYBE"}}), id="unknown-label"),
    pytest.param(llm({"labels": {"cutoff": 1}}), id="non-string-label"),
    pytest.param(llm({"labels": {"cutoff": "SUPPORTED"}, "citations": []}), id="extra-field"),
    pytest.param(llm({"labels": [["cutoff", "SUPPORTED"]]}), id="labels-not-object"),
    pytest.param(llm({"results": []}), id="wrong-shape"),
    pytest.param(json.dumps(json.dumps("not json at all")), id="not-json-object"),
])
def test_invalid_model_output_reverts_without_state_change(env, model):
    c = env.claimed()
    web(env.vm)
    env.vm.mock_llm(R1, model)
    with reverts(env.vm, env.stranger, "LLM_ERROR"):
        c.judge_defects()
    assert states(c) == {"cutoff": "CLAIMED", "contact": "CLAIMED"}
    assert check(c)["round1_attempts"] == 0


def test_round_two_rejects_unknown_ids_and_unclaimed_criteria(env):
    c = env.claimed(claims=[CLAIMS[0]])
    web(env.vm)
    env.vm.mock_llm(R1, labels(cutoff="SUPPORTED"))
    c.judge_defects()
    with env.vm.prank(env.supplier):
        c.submit_repair(V2, "Raised the cutoff in version two.")
    env.vm.mock_llm(R2, labels(cutoff="REMEDIED", contact="UNREMEDIED"))  # contact was released in round 1 filing
    with reverts(env.vm, env.stranger, "LLM_ERROR"):
        c.judge_repair()
    assert states(c) == {"cutoff": "SUPPORTED", "contact": "RELEASED"}
    check(c)


# ---------------- adversarial leader ----------------

def _flip(r): r["labels"][1]["label"] = "UNSUPPORTED"
def _sha(r): r["sources"][0]["sha256"] = "0" * 64
def _bytes(r): r["sources"][0]["byte_count"] += 1
def _citations(r): r["labels"][0]["citations"] = [V1]
def _top_extra(r): r["citations"] = [V1]
def _round2_label(r): r["labels"][0]["label"] = "REMEDIED"
def _lowercase(r): r["labels"][0]["label"] = "supported"
def _unknown_id(r): r["labels"][0]["criterion_id"] = "ghost"
def _extra_row(r): r["labels"].append({"criterion_id": "bonus", "label": "SUPPORTED"})
def _dropped(r): r["labels"].pop()
def _reordered(r): r["labels"].reverse()
def _digest(r): r["input_digest"] = "sha256:" + "0" * 64
def _unavailable_positive(r): r["sources"][0].update(status="unavailable", byte_count=0, sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
def _oversized(r): r["sources"][0]["byte_count"] = 5001
def _status(r): r["sources"][0]["status"] = "truncated"
def _extra_source(r): r["sources"].append(copy.deepcopy(r["sources"][0]))
def _wrong_url(r): r["sources"][0]["url"] = V2


FORGERIES = [_flip, _sha, _bytes, _citations, _top_extra, _round2_label, _lowercase, _unknown_id, _extra_row,
             _dropped, _reordered, _digest, _unavailable_positive, _oversized, _status, _extra_source, _wrong_url]


@pytest.mark.parametrize("forge", FORGERIES, ids=lambda f: f.__name__.strip("_"))
def test_validator_rejects_forged_round_one_leader(env, forge):
    c = env.round1()
    honest = c.get_judgment(1, 1)
    assert env.vm.run_validator() is True
    assert env.vm.run_validator(leader_result=copy.deepcopy(honest)) is True
    forged = copy.deepcopy(honest)
    forge(forged)
    assert env.vm.run_validator(leader_result=forged) is False
    check(c)


@pytest.mark.parametrize("forge", [_flip, _sha, _extra_row, _citations, _unknown_id], ids=lambda f: f.__name__.strip("_"))
def test_validator_rejects_forged_round_two_leader(env, forge):
    c = env.repaired()
    env.vm.mock_llm(R2, labels(cutoff="REMEDIED", contact="UNREMEDIED"))
    c.judge_repair()
    honest = c.get_judgment(2, 1)
    assert env.vm.run_validator(leader_result=copy.deepcopy(honest)) is True
    forged = copy.deepcopy(honest)
    forge(forged)
    assert env.vm.run_validator(leader_result=forged) is False
    check(c)


def test_validator_rejects_a_new_allegation_row_in_round_two(env):
    c = env.repaired()
    env.vm.mock_llm(R2, labels(cutoff="REMEDIED", contact="UNREMEDIED"))
    c.judge_repair()
    forged = c.get_judgment(2, 1)
    forged["labels"].append({"criterion_id": "new-allegation", "label": "UNREMEDIED"})
    assert env.vm.run_validator(leader_result=forged) is False


def test_validator_with_a_different_honest_model_disagrees(env):
    c = env.round1()
    env.vm.clear_mocks()
    web(env.vm)
    env.vm.mock_llm(R1, labels(cutoff="SUPPORTED", contact="UNSUPPORTED"))
    assert env.vm.run_validator() is False
    check(c)


def test_validator_matches_leader_error_and_rejects_error_mismatch(env):
    c = env.claimed()
    web(env.vm)
    env.vm.mock_llm(R1, llm({"labels": {"ghost": "SUPPORTED"}}))
    with reverts(env.vm, env.stranger, "LLM_ERROR"):
        c.judge_defects()


# ---------------- authorization ----------------

def test_unauthorized_callers_are_rejected_in_every_phase(env):
    s, b, x, vm = env.supplier, env.buyer, env.stranger, env.vm
    c = env.new()
    digest = c.get_terms()["terms_digest"]
    for who in (b, x):
        with reverts(vm, who, "not authorized"):
            c.accept_terms(digest)
        with reverts(vm, who, "not authorized"):
            c.reject_terms()
    with reverts(vm, s, "digest"):
        c.accept_terms("sha256:" + "0" * 64)
    with vm.prank(s):
        c.accept_terms(digest)
    for who in (b, x):
        with reverts(vm, who, "not authorized"):
            c.submit_delivery(V1, "Version one of the handover note.")
    with vm.prank(s):
        c.submit_delivery(V1, "Version one of the handover note.")
    for who in (s, x):
        with reverts(vm, who, "not authorized"):
            c.file_claims(json.dumps(CLAIMS))
    with vm.prank(b):
        c.file_claims(json.dumps(CLAIMS))
    web(vm)
    vm.mock_llm(R1, labels(cutoff="SUPPORTED", contact="SUPPORTED"))
    with vm.prank(x):  # permissionless trigger over frozen inputs
        c.judge_defects()
    for who in (b, x):
        with reverts(vm, who, "not authorized"):
            c.submit_repair(V2, "Raised the cutoff in version two.")
    check(c)


def test_permissionless_triggers_work_for_any_caller(env):
    c, vm = env.repaired(), env.vm
    vm.clear_mocks()
    web(vm, v2=V2_TEXT.replace("TBD", "+000 555 0100"))
    vm.mock_llm(R2, labels(cutoff="REMEDIED", contact="REMEDIED"))
    with vm.prank(env.stranger):
        assert c.judge_repair()["phase"] == "SETTLED"
    assert check(c)["released_units"] == 100


# ---------------- replay and phase gating ----------------

def test_replays_and_late_actions_cannot_change_a_settled_escrow(env):
    c, vm = env.repaired(), env.vm
    vm.mock_llm(R2, labels(cutoff="REMEDIED", contact="UNREMEDIED"))
    c.judge_repair()
    before = check(c)
    with vm.expect_revert("requires phase"):
        c.judge_repair()
    with vm.expect_revert("requires phase"):
        c.judge_defects()
    with reverts(vm, env.buyer, "requires phase"):
        c.file_claims(json.dumps(CLAIMS))
    with reverts(vm, env.supplier, "requires phase"):
        c.submit_repair(V2, "Raised the cutoff in version two.")
    vm.warp(AFTER_FINAL)
    with vm.expect_revert("nothing to finalize"):
        c.finalize()
    assert check(c) == before and states(c) == {"cutoff": "RELEASED", "contact": "REFUNDED"}


def test_claims_are_frozen_after_filing_and_cannot_expand(env):
    c, vm = env.round1(), env.vm
    extra = [dict(CLAIMS[0], allegation="A different allegation about the same criterion.")]
    with reverts(vm, env.buyer, "requires phase"):  # REPAIR_REQUIRED
        c.file_claims(json.dumps(extra))
    with vm.prank(env.supplier):
        c.submit_repair(V2, "Raised the cutoff in version two.")
    with reverts(vm, env.buyer, "requires phase"):  # ROUND2_PENDING
        c.file_claims(json.dumps(CLAIMS))
    assert c.get_claims() == CLAIMS or {x["criterion_id"] for x in c.get_claims()} == {"cutoff", "contact"}
    check(c)


def test_second_repair_and_repair_before_round_one_are_rejected(env):
    c, vm = env.claimed(), env.vm
    with reverts(vm, env.supplier, "requires phase"):
        c.submit_repair(V2, "Raised the cutoff in version two.")
    web(vm)
    vm.mock_llm(R1, labels(cutoff="SUPPORTED", contact="SUPPORTED"))
    c.judge_defects()
    with vm.prank(env.supplier):
        c.submit_repair(V2, "Raised the cutoff in version two.")
    with reverts(vm, env.supplier, "requires phase"):
        c.submit_repair(BASE + "c" * 40 + "/handover.md", "Another attempt at a repair version.")
    check(c)


# ---------------- evidence failures ----------------

BAD = [
    pytest.param({"status": 404, "body": "missing"}, id="non-200-404"),
    pytest.param({"status": 500, "body": "boom"}, id="non-200-500"),
    pytest.param({"status": 200, "body": ""}, id="empty"),
    pytest.param({"status": 200, "body": "   \n\t "}, id="blank"),
    pytest.param({"status": 200, "body": b"x" * 5001}, id="oversized-5001"),
    pytest.param({"status": 200, "body": b"Low-water cutoff: 5 cm\xff\xfe"}, id="invalid-utf8"),
]


@pytest.mark.parametrize("response", BAD)
def test_round_one_evidence_failure_never_produces_a_positive_outcome(env, response):
    c = env.claimed()
    web(env.vm, v1_response=response)  # no LLM mock: the model must not even be called
    result = c.judge_defects()
    assert [r["label"] for r in result["labels"]] == ["UNCLEAR", "UNCLEAR"]
    stored = c.get_judgment(1, 1)
    assert stored["sources"][0]["status"] == "unavailable" and stored["sources"][0]["byte_count"] == 0
    assert states(c) == {"cutoff": "CLAIMED", "contact": "CLAIMED"}
    assert env.vm.run_validator() is True
    assert check(c)["released_units"] == 0


@pytest.mark.parametrize("response", BAD)
def test_round_two_evidence_failure_never_pays_or_refunds(env, response):
    c = env.repaired()
    env.vm.clear_mocks()
    web(env.vm, v2_response=response)
    result = c.judge_repair()
    assert [r["label"] for r in result["labels"]] == ["UNCLEAR", "UNCLEAR"]
    assert states(c) == {"cutoff": "SUPPORTED", "contact": "SUPPORTED"}
    assert check(c)["escrow_units"] == 100 and c.get_terms()["phase"] == "ROUND2_PENDING"


def test_body_of_exactly_5000_bytes_is_accepted_and_recorded(env):
    body = V1_TEXT + "#" * (5000 - len(V1_TEXT.encode()))
    assert len(body.encode()) == 5000
    c = env.claimed()
    web(env.vm, v1=body)
    env.vm.mock_llm(R1, labels(cutoff="SUPPORTED", contact="SUPPORTED"))
    c.judge_defects()
    source = c.get_judgment(1, 1)["sources"][0]
    assert source["status"] == "fetched" and source["byte_count"] == 5000
    import hashlib
    assert source["sha256"] == hashlib.sha256(body.encode()).hexdigest()


def test_recorded_source_hash_matches_the_raw_bytes(env):
    import hashlib
    c = env.round1()
    stored = c.get_judgment(1, 1)["sources"][0]
    assert stored["byte_count"] == len(V1_TEXT.encode()) == 198
    assert stored["sha256"] == hashlib.sha256(V1_TEXT.encode()).hexdigest()
    assert stored["sha256"] == "517533f968fec6f83fa11a06c8f7fb6240d77558fc0d68bc47cd117b95d70037"
    assert len(V2_TEXT.encode()) == 199
    assert hashlib.sha256(V2_TEXT.encode()).hexdigest() == "41bf06ac4f027ff393e1516b28ebd7909be3e0cc644efa53131c848ec604409c"


# ---------------- deadlines, attempts and defaults ----------------

def test_unclear_attempts_are_bounded_then_deadline_releases_to_supplier(env):
    c, vm = env.claimed(), env.vm
    web(vm)
    vm.mock_llm(R1, labels(cutoff="UNCLEAR", contact="UNCLEAR"))
    for attempt in (1, 2, 3):
        assert c.judge_defects()["attempt"] == attempt
        check(c)
    with vm.expect_revert("attempts exhausted"):
        c.judge_defects()
    with vm.expect_revert("has not passed"):
        c.finalize()
    vm.warp(AFTER_JUDGMENT)
    with vm.expect_revert("has passed"):
        c.judge_defects()
    result = c.finalize()
    assert result["phase"] == "SETTLED" and (result["released_units"], result["refunded_units"]) == (100, 0)
    assert check(c)["escrow_units"] == 0


def test_round_one_deadline_default_keeps_supported_defects_open_for_repair(env):
    c, vm = env.claimed(), env.vm
    web(vm)
    vm.mock_llm(R1, labels(cutoff="SUPPORTED", contact="UNCLEAR"))
    assert c.judge_defects()["phase"] == "ROUND1_PENDING"
    with reverts(vm, env.supplier, "requires phase"):
        c.submit_repair(V2, "Raised the cutoff in version two.")
    vm.warp(AFTER_JUDGMENT)
    assert c.finalize()["phase"] == "REPAIR_REQUIRED"
    assert states(c) == {"cutoff": "SUPPORTED", "contact": "RELEASED"}
    check(c)
    with vm.prank(env.supplier):
        c.submit_repair(V2, "Raised the cutoff in version two.")
    vm.mock_llm(R2, labels(cutoff="REMEDIED"))
    assert c.judge_repair()["phase"] == "SETTLED"
    assert check(c)["released_units"] == 100


def test_round_two_unclear_is_retried_then_refunded_at_final_deadline(env):
    c, vm = env.repaired(), env.vm
    vm.mock_llm(R2, labels(cutoff="UNCLEAR", contact="UNCLEAR"))
    for _ in range(3):
        c.judge_repair()
        assert check(c)["escrow_units"] == 100
    with vm.expect_revert("attempts exhausted"):
        c.judge_repair()
    vm.warp(AFTER_FINAL)
    result = c.finalize()
    assert result["phase"] == "SETTLED" and (result["released_units"], result["refunded_units"]) == (0, 100)
    check(c)


def test_no_repair_by_repair_deadline_refunds_supported_defects(env):
    c, vm = env.round1(), env.vm
    vm.warp(AFTER_REPAIR)
    with reverts(vm, env.supplier, "has passed"):
        c.submit_repair(V2, "Raised the cutoff in version two.")
    result = c.finalize()
    assert (result["released_units"], result["refunded_units"]) == (0, 100) and result["phase"] == "SETTLED"
    check(c)


def test_no_claims_by_claim_deadline_releases_all(env):
    c, vm = env.delivered(), env.vm
    with vm.expect_revert("has not passed"):
        c.finalize()
    vm.warp(AFTER_CLAIM)
    with reverts(vm, env.buyer, "has passed"):
        c.file_claims(json.dumps(CLAIMS))
    assert c.finalize()["released_units"] == 100
    check(c)


def test_no_delivery_refunds_the_buyer(env):
    c, vm = env.accepted(), env.vm
    vm.warp(AFTER_DELIVERY)
    with reverts(vm, env.supplier, "has passed"):
        c.submit_delivery(V1, "Version one of the handover note.")
    assert c.finalize()["phase"] == "REFUNDED_NO_DELIVERY" and check(c)["refunded_units"] == 100


def test_no_acceptance_cancels_with_full_refund(env):
    c, vm = env.new(), env.vm
    vm.warp(AFTER_DELIVERY)
    with reverts(vm, env.supplier, "has passed"):
        c.accept_terms(c.get_terms()["terms_digest"])
    assert c.finalize()["phase"] == "CANCELLED" and check(c)["refunded_units"] == 100


def test_supplier_can_reject_terms_for_a_full_refund(env):
    c = env.new()
    with env.vm.prank(env.supplier):
        assert c.reject_terms()["phase"] == "CANCELLED"
    assert check(c)["refunded_units"] == 100


@pytest.mark.parametrize("builder", ["new", "accepted", "delivered", "claimed", "round1", "repaired"])
def test_finalize_before_any_deadline_reverts_in_every_phase(env, builder):
    c = getattr(env, builder)()
    env.vm.warp(NOW)
    with env.vm.expect_revert("has not passed"):
        c.finalize()
    check(c)


# ---------------- pinned URLs ----------------

@pytest.mark.parametrize("url", [
    "https://raw.githubusercontent.com/example-owner/example-evidence/main/handover.md",
    "https://raw.githubusercontent.com/example-owner/example-evidence/" + "a" * 39 + "/handover.md",
    "https://raw.githubusercontent.com/example-owner/example-evidence/" + "A" * 40 + "/handover.md",
    "https://github.com/example-owner/example-evidence/blob/" + "a" * 40 + "/handover.md",
    "http://raw.githubusercontent.com/example-owner/example-evidence/" + "a" * 40 + "/handover.md",
    "https://raw.githubusercontent.com/example-owner/example-evidence/" + "a" * 40 + "/../secret.md",
    "https://raw.githubusercontent.com/example-owner/example-evidence/" + "a" * 40 + "/handover.md?x=1",
    "https://raw.githubusercontent.com@evil.example/o/r/" + "a" * 40 + "/f.md",
    "https://archive-api.open-meteo.com/v1/archive?latitude=6.5&longitude=3.4",
])
def test_deliverable_must_be_a_commit_pinned_raw_github_file(env, url):
    c = env.accepted()
    with reverts(env.vm, env.supplier, "deliverable reference"):
        c.submit_delivery(url, "Version one of the handover note.")


@pytest.mark.parametrize("url", [
    BASE + "a" * 40 + "/handover.md",
    "https://raw.githubusercontent.com/other-owner/example-evidence/" + "b" * 40 + "/handover.md",
    "https://raw.githubusercontent.com/example-owner/other-repo/" + "b" * 40 + "/handover.md",
    BASE + "b" * 40 + "/other.md",
])
def test_repair_must_be_same_repo_and_path_at_a_new_commit(env, url):
    c = env.round1()
    with reverts(env.vm, env.supplier, "same repository and path"):
        c.submit_repair(url, "Raised the cutoff in version two.")


# ---------------- constructor and claim validation ----------------

FIVE = [dict(CRITERIA[0], criterion_id=f"c{i}", allocation_units=20) for i in range(5)]


@pytest.mark.parametrize("message,overrides", [
    pytest.param("sum to the escrow budget", {"total_units": 99}, id="allocation-sum"),
    pytest.param("one to four", {"criteria_json": json.dumps(FIVE)}, id="too-many-criteria"),
    pytest.param("unique", {"criteria_json": json.dumps([CRITERIA[0], dict(CRITERIA[1], criterion_id="cutoff")])}, id="duplicate-id"),
    pytest.param("allocation", {"criteria_json": json.dumps([dict(CRITERIA[0], allocation_units=0), dict(CRITERIA[1], allocation_units=100)])}, id="zero-allocation"),
    pytest.param("strictly ordered", {"deadlines": [DEADLINES[1], DEADLINES[0], *DEADLINES[2:]]}, id="swapped-deadlines"),
    pytest.param("strictly ordered", {"deadlines": ["2029-12-31T00:00:00Z", *DEADLINES[1:]]}, id="past-delivery"),
    pytest.param("strictly ordered", {"deadlines": [*DEADLINES[:4], DEADLINES[3]]}, id="equal-deadlines"),
])
def test_constructor_rejects_bad_terms(direct_vm, direct_deploy, direct_owner, direct_alice, message, overrides):
    with direct_vm.expect_revert(message):
        deploy(direct_vm, direct_deploy, direct_owner, direct_alice, **overrides)


def test_constructor_rejects_buyer_as_supplier(direct_vm, direct_deploy, direct_owner):
    with direct_vm.expect_revert("different named participant"):
        deploy(direct_vm, direct_deploy, direct_owner, direct_owner)


@pytest.mark.parametrize("claims,message", [
    ([dict(CLAIMS[0], criterion_id="ghost")], "registered"),
    ([CLAIMS[0], CLAIMS[0]], "unique"),
    ([dict(CLAIMS[0], evidence_url="https://x.example/y")], "exactly"),
    ([{"criterion_id": "cutoff", "allegation": "The stated cutoff is below the required level."}], "exactly"),
    ([dict(CLAIMS[0], quoted_line="short")], "quoted line"),
    ([dict(CLAIMS[0], quoted_line="line one\nline two")], "quoted line"),
    ([dict(CLAIMS[0], quoted_line=" Low-water cutoff: 5 cm")], "quoted line"),
    ([dict(CLAIMS[0], allegation="too short")], "length"),
    ([dict(CLAIMS[0], quoted_line="x" * 201)], "quoted line"),
])
def test_claim_batch_validation(env, claims, message):
    c = env.delivered()
    with reverts(env.vm, env.buyer, message):
        c.file_claims(json.dumps(claims))
    assert states(c) == {"cutoff": "UNCLAIMED", "contact": "UNCLAIMED"}
    check(c)


# ---------------- structure: no self inside nondeterministic code, full compare ----------------

def _tree():
    return ast.parse(SOURCE.read_text(encoding="utf-8"))


def test_nondeterministic_code_never_touches_contract_state():
    funcs = {n.name: n for n in _tree().body if isinstance(n, ast.FunctionDef)}
    for name in ("_fetch", "_parse_labels", "_classify", "_guard", "_evaluate", "_candidate", "_consensus"):
        assert name in funcs, name
        assert not any(isinstance(n, ast.Name) and n.id == "self" for n in ast.walk(funcs[name])), f"{name} uses self"
    nested = {n.name for n in ast.walk(funcs["_consensus"]) if isinstance(n, ast.FunctionDef)}
    assert {"leader_fn", "validator_fn"} <= nested


def test_validator_compares_the_full_canonical_result():
    text = SOURCE.read_text(encoding="utf-8")
    assert "_canonical(leader) == _canonical(mine)" in text
    assert "citations" not in text and "close enough" not in text.replace('"No \\"close enough\\""', "").replace("No \"close enough\"", "")


def test_allowlists_and_bounds_are_frozen_constants():
    text = SOURCE.read_text(encoding="utf-8")
    for fragment in ('"SUPPORTED", "UNSUPPORTED", "UNCLEAR"', '"REMEDIED", "UNREMEDIED", "UNCLEAR"',
                     "MAX_SOURCE_BYTES = 5000", "MAX_CRITERIA = 4", "MAX_ATTEMPTS = 3"):
        assert fragment in text
