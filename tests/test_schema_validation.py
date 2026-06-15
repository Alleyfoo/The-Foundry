"""Schema validation is the contract — these lock it in."""

from pathlib import Path

from runtime.schema_validator import load_schema, validate_dataset
from runtime.foundry import load_objects

ROOT = Path(__file__).resolve().parents[1]


def _schema():
    return load_schema(str(ROOT / "schema" / "object_schema.json"))


def _objects():
    return load_objects(str(ROOT / "data" / "objects.json"))


def test_seed_objects_all_valid():
    report = validate_dataset(_objects(), _schema())
    assert report.total_records == 24
    assert report.is_valid
    assert report.violation_count == 0


def test_catches_missing_required():
    report = validate_dataset([{"object_id": "OBJ-X1"}], _schema())
    assert not report.is_valid
    assert any(v["rule"] == "required" for v in report.violations)


def test_catches_bad_enum():
    obj = dict(_objects()[0], box="not_a_box")
    report = validate_dataset([obj], _schema())
    assert any(v["rule"] == "enum" and v["field"] == "box" for v in report.violations)


def test_catches_bad_type():
    obj = dict(_objects()[0], confidence="high")  # should be a number
    report = validate_dataset([obj], _schema())
    assert any(v["rule"] == "type" and v["field"] == "confidence" for v in report.violations)
