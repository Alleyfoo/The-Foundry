"""Intake/triage, the state machine, the access guard, commit, disposition."""

import json
from pathlib import Path

from runtime.system_of_record import SystemOfRecord
from runtime.actions import triage_text, intake, available_actions, apply_action
from runtime.foundry import load_objects

ROOT = Path(__file__).resolve().parents[1]
ACCESS = json.loads((ROOT / "schema" / "roles.json").read_text(encoding="utf-8"))["access_model"]


def _sor(tmp_path):
    sor = SystemOfRecord(str(tmp_path / "f.db"))
    sor.seed_if_empty(load_objects(str(ROOT / "data" / "objects.json")))
    return sor


def test_triage_classifies_into_boxes():
    assert triage_text("new customer request")["box"] == "create"
    assert triage_text("update the price")["box"] == "modify"
    assert triage_text("approve the exception")["box"] == "control"
    assert triage_text("roadmap for next quarter")["box"] == "plan"
    assert triage_text("attached datasheet certificate")["box"] == "reference"


def test_intake_creates_draft(tmp_path):
    sor = _sor(tmp_path)
    obj = intake(sor, "new item request")
    assert obj["state"] == "draft"
    assert obj["object_id"] == "OBJ-IN1"
    assert sor.get("OBJ-IN1") is not None


def test_state_machine_advances(tmp_path):
    sor = _sor(tmp_path)
    oid = intake(sor, "new item request")["object_id"]
    assert "activate" in available_actions(sor.get(oid))
    assert apply_action(sor, oid, "activate", "Data Entry / Operations", ACCESS)["ok"]
    assert apply_action(sor, oid, "submit", "Data Entry / Operations", ACCESS)["ok"]
    assert sor.get(oid)["state"] == "pending"


def test_access_guard_blocks_unauthorised_approve(tmp_path):
    sor = _sor(tmp_path)
    oid = intake(sor, "new item request")["object_id"]
    apply_action(sor, oid, "activate", "Data Entry / Operations", ACCESS)
    apply_action(sor, oid, "submit", "Data Entry / Operations", ACCESS)
    refused = apply_action(sor, oid, "approve", "Data Entry / Operations", ACCESS)
    assert refused["ok"] is False
    assert "mismatch" in refused["message"].lower()
    assert apply_action(sor, oid, "approve", "Manager", ACCESS)["ok"]


def test_commit_reaches_truth(tmp_path):
    sor = _sor(tmp_path)
    oid = intake(sor, "new item request")["object_id"]
    for act, actor in [("activate", "SAP Owner"), ("submit", "SAP Owner"),
                       ("approve", "Manager"), ("commit", "SAP Owner")]:
        apply_action(sor, oid, act, actor, ACCESS)
    final = sor.get(oid)
    assert final["commitment"] == "truth"
    assert final["system_of_record_ref"]


def test_disposition_sets_lifecycle(tmp_path):
    sor = _sor(tmp_path)
    res = apply_action(sor, "OBJ-L004", "archive", "Records Owner", ACCESS)  # retired
    assert res["ok"]
    assert res["object"]["lifecycle"] == "archived"


def test_scenario_resolves_to_truth(tmp_path):
    sor = _sor(tmp_path)
    steps = [("OBJ-I004", "unblock", "Manager"), ("OBJ-I005", "activate", "SAP Owner"),
             ("OBJ-I005", "submit", "SAP Owner"), ("OBJ-I005", "approve", "Manager"),
             ("OBJ-I005", "commit", "SAP Owner")]
    for oid, act, actor in steps:
        assert apply_action(sor, oid, act, actor, ACCESS)["ok"]
    assert sor.get("OBJ-I005")["commitment"] == "truth"
