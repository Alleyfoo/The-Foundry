"""
Data cleaning and normalization utilities.
Ported from Data-agents-demo/runtime/data_janitor.py and extended for schema-driven system.
"""

from __future__ import annotations

import re
from typing import Any


def clean_value(value: Any, dtype: str = "string") -> Any:
    """Clean and cast a single value to the target dtype.

    Supported dtypes: string, number, integer, boolean, date, enum, array.
    """
    if value is None:
        return None

    if dtype == "string":
        v = str(value).strip()
        return v if v and v.lower() not in ("null", "none", "n/a", "") else None

    if dtype == "number":
        if isinstance(value, (int, float)):
            return float(value)
        v = str(value).strip().replace(",", ".").replace(" ", "")
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    if dtype == "integer":
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value) if value == int(value) else None
        v = str(value).strip().replace(" ", "")
        try:
            return int(float(v))
        except (ValueError, TypeError):
            return None

    if dtype == "boolean":
        if isinstance(value, bool):
            return value
        v = str(value).strip().lower()
        if v in ("true", "1", "yes", "on", "kyllä"):
            return True
        if v in ("false", "0", "no", "off", "ei"):
            return False
        return None

    if dtype == "date":
        v = str(value).strip()
        # Accept ISO 8601 dates
        if re.match(r"^\d{4}-\d{2}-\d{2}", v):
            return v[:10]
        return v if v else None

    if dtype == "enum":
        v = str(value).strip().lower().replace(" ", "_")
        return v if v else None

    if dtype == "array":
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # Try JSON-like array or comma-separated
            v = value.strip()
            if v.startswith("["):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [x.strip() for x in v.split(",") if x.strip()]
        return [value] if value else []

    return value


def normalize_header(header: str) -> str:
    """Normalize a column/field header to snake_case."""
    h = str(header).strip()
    h = re.sub(r"[^\w\s]", "", h)
    h = re.sub(r"\s+", "_", h)
    h = h.lower().strip("_")
    return h


def clean_record(record: dict[str, Any], schema_dtypes: dict[str, str]) -> dict[str, Any]:
    """Clean all values in a record according to schema dtypes."""
    cleaned = {}
    for key, value in record.items():
        dtype = schema_dtypes.get(key, "string")
        cleaned[key] = clean_value(value, dtype)
    return cleaned


def validate_required(record: dict[str, Any], required_fields: list[str]) -> list[str]:
    """Return list of missing required fields."""
    missing = []
    for field in required_fields:
        if field not in record or record[field] is None:
            missing.append(field)
    return missing


def detect_anomalies(records: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    """Detect statistical anomalies in a numeric field."""
    values = [r[field] for r in records if field in r and isinstance(r[field], (int, float))]
    if len(values) < 3:
        return []

    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = variance ** 0.5

    if std == 0:
        return []

    anomalies = []
    for i, r in enumerate(records):
        v = r.get(field)
        if isinstance(v, (int, float)):
            z_score = abs(v - mean) / std
            if z_score > 3.0:
                anomalies.append({
                    "index": i,
                    "field": field,
                    "value": v,
                    "z_score": round(z_score, 2),
                    "mean": round(mean, 2),
                    "std": round(std, 2),
                })
    return anomalies
