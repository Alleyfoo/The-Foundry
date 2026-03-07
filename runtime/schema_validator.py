"""
Schema validation agent logic.
Validates product data against source schema and view schemas.
Ported pattern from Data-agents-demo/agent-base/agents/validation.agent.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from runtime.models import ValidationReport


def load_schema(path: str) -> dict[str, Any]:
    """Load a JSON schema from disk."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_record(record: dict[str, Any], schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate a single record against a schema. Returns list of violations."""
    violations = []
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    # Check required fields
    for field in required:
        if field not in record or record[field] is None:
            violations.append({
                "field": field,
                "rule": "required",
                "message": f"Required field '{field}' is missing or null",
                "severity": "error",
            })

    # Check each field against its schema
    for field, value in record.items():
        if field not in properties:
            violations.append({
                "field": field,
                "rule": "unknown_field",
                "message": f"Field '{field}' not in schema",
                "severity": "warning",
            })
            continue

        if value is None:
            continue  # Already checked in required

        field_schema = properties[field]
        field_violations = _validate_field(field, value, field_schema)
        violations.extend(field_violations)

    return violations


def _validate_field(field: str, value: Any, field_schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate a single field value against its schema definition."""
    violations = []
    expected_types = field_schema.get("type", "string")
    if isinstance(expected_types, str):
        expected_types = [expected_types]

    # Type checking
    type_ok = False
    for t in expected_types:
        if t == "null" and value is None:
            type_ok = True
        elif t == "string" and isinstance(value, str):
            type_ok = True
        elif t == "number" and isinstance(value, (int, float)):
            type_ok = True
        elif t == "integer" and isinstance(value, int) and not isinstance(value, bool):
            type_ok = True
        elif t == "boolean" and isinstance(value, bool):
            type_ok = True
        elif t == "array" and isinstance(value, list):
            type_ok = True
        elif t == "object" and isinstance(value, dict):
            type_ok = True

    if not type_ok:
        violations.append({
            "field": field,
            "rule": "type",
            "message": f"Expected type {expected_types}, got {type(value).__name__}",
            "severity": "error",
            "value": str(value)[:100],
        })
        return violations  # Skip further checks if type is wrong

    # Enum validation
    if "enum" in field_schema and value is not None:
        allowed = field_schema["enum"]
        if value not in allowed:
            violations.append({
                "field": field,
                "rule": "enum",
                "message": f"Value '{value}' not in allowed values: {allowed}",
                "severity": "error",
                "value": str(value),
            })

    # String constraints
    if isinstance(value, str):
        max_len = field_schema.get("maxLength")
        if max_len and len(value) > max_len:
            violations.append({
                "field": field,
                "rule": "maxLength",
                "message": f"String length {len(value)} exceeds max {max_len}",
                "severity": "error",
            })

        pattern = field_schema.get("pattern")
        if pattern and not re.match(pattern, value):
            violations.append({
                "field": field,
                "rule": "pattern",
                "message": f"Value '{value}' does not match pattern '{pattern}'",
                "severity": "error",
            })

    # Numeric constraints
    if isinstance(value, (int, float)):
        minimum = field_schema.get("minimum")
        if minimum is not None and value < minimum:
            violations.append({
                "field": field,
                "rule": "minimum",
                "message": f"Value {value} is below minimum {minimum}",
                "severity": "error",
            })

        maximum = field_schema.get("maximum")
        if maximum is not None and value > maximum:
            violations.append({
                "field": field,
                "rule": "maximum",
                "message": f"Value {value} exceeds maximum {maximum}",
                "severity": "error",
            })

    return violations


def validate_dataset(
    records: list[dict[str, Any]],
    schema: dict[str, Any],
    run_id: str = "",
    data_path: str = "",
) -> ValidationReport:
    """Validate an entire dataset against a schema."""
    all_violations = []
    all_warnings = []
    valid_count = 0

    for i, record in enumerate(records):
        violations = validate_record(record, schema)
        errors = [v for v in violations if v["severity"] == "error"]
        warnings = [v for v in violations if v["severity"] == "warning"]

        for v in errors:
            v["record_index"] = i
            v["product_code"] = record.get("product_code", f"record_{i}")
        for w in warnings:
            w["record_index"] = i
            w["product_code"] = record.get("product_code", f"record_{i}")

        all_violations.extend(errors)
        all_warnings.extend(warnings)

        if not errors:
            valid_count += 1

    return ValidationReport(
        run_id=run_id,
        schema_path="",
        data_path=data_path,
        total_records=len(records),
        valid_records=valid_count,
        violations=all_violations,
        warnings=all_warnings,
        is_valid=len(all_violations) == 0,
    )


def validate_view_coverage(
    source_schema: dict[str, Any],
    view_schemas: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Check that view schemas properly subset the source schema."""
    source_fields = set(source_schema.get("properties", {}).keys())
    report = {"source_field_count": len(source_fields), "views": {}}

    all_covered = set()
    for view_name, view_schema in view_schemas.items():
        view_fields = set(view_schema.get("properties", {}).keys())
        unknown = view_fields - source_fields
        covered = view_fields & source_fields
        all_covered.update(covered)

        report["views"][view_name] = {
            "field_count": len(view_fields),
            "covered": len(covered),
            "unknown_fields": sorted(unknown),
            "is_valid_subset": len(unknown) == 0,
        }

    uncovered = source_fields - all_covered
    report["uncovered_by_any_view"] = sorted(uncovered)
    report["total_coverage_pct"] = round(len(all_covered) / max(1, len(source_fields)) * 100, 1)

    return report
