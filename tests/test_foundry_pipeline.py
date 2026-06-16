"""The pipeline end to end: validation, bottlenecks, mismatches, coverage, lenses."""

from pathlib import Path

from runtime.foundry import Foundry

ROOT = Path(__file__).resolve().parents[1]


def _run(tmp_path):
    return Foundry(base_dir=str(ROOT), artifacts_dir=str(tmp_path)).run()


def test_pipeline_completes_and_validates(tmp_path):
    r = _run(tmp_path)
    assert r["status"] == "completed"
    assert r["validation"].valid_records == 27
    assert r["validation"].is_valid


def test_finds_known_bottlenecks(tmp_path):
    ids = {b["object_id"] for b in _run(tmp_path)["bottlenecks"]}
    assert {"OBJ-I004", "OBJ-X001"} <= ids


def test_detects_access_mismatches(tmp_path):
    types = {m["type"] for m in _run(tmp_path)["mismatches"]}
    assert "ownership_without_flow" in types
    assert "approval_without_authority" in types


def test_authority_rule_covers_all_truth_touching_boxes(tmp_path):
    """A modify/create change routed to a non-control approver is flagged too —
    not just the control box. A legitimate SAP Owner commit is not."""
    f = Foundry(base_dir=str(ROOT), artifacts_dir=str(tmp_path))
    boxes = {"boxes": [{"id": "modify", "touches_live_truth": True}]}
    box_access = {"control": {"primary": "Manager", "also": ["SAP Owner"]}}
    base = {"object_id": "OBJ-T", "box": "modify", "state": "pending",
            "owner_team": "Pricing", "commitment": "workflow", "confidence": 0.6}

    unauthorised = f._detect_mismatches(
        [dict(base, approver_role="Pricing")], boxes, box_access)
    assert any(m["type"] == "approval_without_authority" for m in unauthorised)

    authorised = f._detect_mismatches(
        [dict(base, approver_role="SAP Owner")], boxes, box_access)
    assert not any(m["type"] == "approval_without_authority" for m in authorised)


def test_coverage_flags_control_gap(tmp_path):
    cov = _run(tmp_path)["coverage"]
    by_area = {(c["stream"], c["box"]): c for c in cov["matrix"]}
    assert by_area[("item", "control")]["status"] == "red"
    assert cov["summary"]["red"] >= 1


def test_impact_and_approvals_present(tmp_path):
    r = _run(tmp_path)
    assert any(i["risk"] == "high" for i in r["impact"])
    assert r["approvals"] and all("recommendation" in a for a in r["approvals"])


def test_all_lenses_present(tmp_path):
    lenses = _run(tmp_path)["lenses"]
    assert {"customer", "sales", "product", "operations", "finance"} <= set(lenses)


def test_pipeline_runs_over_live_objects(tmp_path):
    """Passing an explicit object set (the live SoR state) is honoured."""
    r = Foundry(base_dir=str(ROOT), artifacts_dir=str(tmp_path)).run(objects=[])
    assert r["status"] == "completed"
    assert r["validation"].total_records == 0
