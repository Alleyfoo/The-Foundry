"""The SQLite system of record: seeding, persistence, events, reset."""

from pathlib import Path

from runtime.system_of_record import SystemOfRecord
from runtime.foundry import load_objects

ROOT = Path(__file__).resolve().parents[1]


def _seed():
    return load_objects(str(ROOT / "data" / "objects.json"))


def test_seed_is_idempotent(tmp_path):
    sor = SystemOfRecord(str(tmp_path / "f.db"))
    assert sor.seed_if_empty(_seed()) is True
    assert len(sor.all_objects()) == 24
    assert sor.seed_if_empty(_seed()) is False


def test_state_persists_across_reopen(tmp_path):
    db = str(tmp_path / "f.db")
    sor = SystemOfRecord(db)
    sor.seed_if_empty(_seed())
    obj = dict(sor.get("OBJ-I005"), state="active")
    sor.upsert(obj)
    sor.close()

    reopened = SystemOfRecord(db)
    assert reopened.get("OBJ-I005")["state"] == "active"


def test_events_and_next_id(tmp_path):
    sor = SystemOfRecord(str(tmp_path / "f.db"))
    sor.seed_if_empty(_seed())
    assert sor.next_object_id() == "OBJ-IN1"
    sor.add_event("OBJ-IN1", "intake", None, "draft", "system", "note")
    assert any(e["action"] == "intake" for e in sor.events())


def test_reset_replaces_objects(tmp_path):
    sor = SystemOfRecord(str(tmp_path / "f.db"))
    sor.seed_if_empty(_seed())
    sor.reset(_seed()[:5])
    assert len(sor.all_objects()) == 5
