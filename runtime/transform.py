"""
Transform agent — derives view data from source data using view schemas.
Ported pattern from Data-agents-demo/agent-base/agents/transform.agent.md.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def derive_view(
    source_records: list[dict[str, Any]],
    view_schema: dict[str, Any],
) -> list[dict[str, Any]]:
    """Transform source records into a view by keeping only fields in the view schema.

    This is the core transform: project source → view fields.
    Does NOT modify values, only selects which fields appear.
    """
    view_fields = set(view_schema.get("properties", {}).keys())
    transformed = []
    for record in source_records:
        projected = {k: v for k, v in record.items() if k in view_fields}
        transformed.append(projected)
    return transformed


def derive_all_views(
    source_records: list[dict[str, Any]],
    view_schemas: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Transform source records into all views."""
    return {
        view_name: derive_view(source_records, schema)
        for view_name, schema in view_schemas.items()
    }


def build_transform_plan(
    source_schema: dict[str, Any],
    view_schema: dict[str, Any],
    view_name: str = "",
) -> dict[str, Any]:
    """Build a transform plan describing how to go from source to view."""
    source_fields = set(source_schema.get("properties", {}).keys())
    view_fields = set(view_schema.get("properties", {}).keys())

    include = sorted(view_fields & source_fields)
    exclude = sorted(source_fields - view_fields)
    unknown = sorted(view_fields - source_fields)

    return {
        "view_name": view_name,
        "source_field_count": len(source_fields),
        "view_field_count": len(view_fields),
        "include_fields": include,
        "exclude_fields": exclude,
        "unknown_in_view": unknown,
        "is_pure_projection": len(unknown) == 0,
    }


def load_source_data(path: str) -> list[dict[str, Any]]:
    """Load product data from JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "products" in data:
        return data["products"]
    if isinstance(data, list):
        return data
    raise ValueError(f"Unexpected data format in {path}")


def load_view_schemas(views_dir: str) -> dict[str, dict[str, Any]]:
    """Load all view schemas from a directory."""
    schemas = {}
    views_path = Path(views_dir)
    if not views_path.exists():
        return schemas
    for f in sorted(views_path.glob("*_view.json")):
        name = f.stem.replace("_view", "")
        schemas[name] = json.loads(f.read_text(encoding="utf-8"))
    return schemas


def compute_field_matrix(
    source_schema: dict[str, Any],
    view_schemas: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build a field-by-view matrix showing which fields appear in which views.

    Returns a list of dicts, one per source field, with view presence flags.
    """
    source_props = source_schema.get("properties", {})
    matrix = []

    for field_name, field_def in sorted(source_props.items()):
        row = {
            "field": field_name,
            "type": field_def.get("type", "unknown"),
            "description": field_def.get("description", ""),
        }
        for view_name, view_schema in sorted(view_schemas.items()):
            row[f"in_{view_name}"] = field_name in view_schema.get("properties", {})

        view_count = sum(1 for vn in view_schemas if row.get(f"in_{vn}", False))
        row["view_count"] = view_count
        matrix.append(row)

    return matrix
