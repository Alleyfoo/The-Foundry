"""
Puhemies — the orchestrator agent.
Plans, delegates, and manages the agent pipeline.
Ported pattern from Data-agents-demo/agent-base/agents/orchestrator.agent.md
and agent-learning/app/speaker.py.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from runtime.artifact_store import ArtifactStore
from runtime.data_janitor import clean_record, validate_required, detect_anomalies
from runtime.judge import Judge
from runtime.models import RunContext, TaskSpec, ValidationReport
from runtime.schema_validator import (
    load_schema,
    validate_dataset,
    validate_view_coverage,
)
from runtime.shadow import ShadowAgent
from runtime.transform import (
    derive_all_views,
    load_source_data,
    load_view_schemas,
    build_transform_plan,
    compute_field_matrix,
)

logger = logging.getLogger(__name__)


class Puhemies:
    """Orchestrator agent for the schema-driven product data system.

    Responsibilities:
    - Plan the processing pipeline
    - Delegate to specialist agents (validator, transform, janitor, judge)
    - Manage revision loops when judge says "revise"
    - Never modify data directly — only delegate
    - Always require human confirmation before writes
    """

    def __init__(
        self,
        base_dir: str = ".",
        artifacts_dir: str = "artifacts",
    ):
        self.base_dir = Path(base_dir)
        self.store = ArtifactStore(artifacts_dir)
        self.shadow = ShadowAgent(self.store)
        self.judge = Judge(max_revisions=3)
        self._ctx: RunContext | None = None

    @property
    def context(self) -> RunContext | None:
        return self._ctx

    def run_pipeline(
        self,
        source_data_path: str = "data/products.json",
        source_schema_path: str = "schema/source_schema.json",
        views_dir: str = "schema/views",
    ) -> RunContext:
        """Execute the full processing pipeline.

        Steps:
        1. Load source data and schemas
        2. Validate source data against source schema
        3. Clean data (janitor)
        4. Build transform plans
        5. Derive all views
        6. Validate each view
        7. Judge evaluates results
        8. Save all artifacts
        """
        ctx = RunContext(
            source_data_path=source_data_path,
            source_schema_path=source_schema_path,
        )
        self._ctx = ctx
        self.shadow.bind_run(ctx.run_id)

        self.shadow.observe_task_start("puhemies", "pipeline", data_path=source_data_path)
        ctx.status = "running"

        try:
            # Step 1: Load data and schemas
            self.shadow.observe_task_start("puhemies", "load_data")
            source_data = load_source_data(str(self.base_dir / source_data_path))
            source_schema = load_schema(str(self.base_dir / source_schema_path))
            view_schemas = load_view_schemas(str(self.base_dir / views_dir))
            ctx.view_schemas = {name: str(self.base_dir / views_dir / f"{name}_view.json")
                                for name in view_schemas}
            self.shadow.observe_task_end("puhemies", "load_data", success=True,
                                         record_count=len(source_data),
                                         view_count=len(view_schemas))

            # Step 2: Validate source data
            self.shadow.observe_task_start("schema_validator", "validate_source")
            source_report = validate_dataset(
                source_data, source_schema, run_id=ctx.run_id, data_path=source_data_path
            )
            self.store.write_json(ctx.run_id, "validation_source.json", {
                "total_records": source_report.total_records,
                "valid_records": source_report.valid_records,
                "violation_count": source_report.violation_count,
                "warning_count": source_report.warning_count,
                "is_valid": source_report.is_valid,
                "violations": source_report.violations[:50],
                "warnings": source_report.warnings[:50],
            })
            self.shadow.observe_task_end("schema_validator", "validate_source",
                                         success=source_report.is_valid,
                                         valid=source_report.valid_records,
                                         total=source_report.total_records)

            # Step 2b: Judge evaluates source validation
            source_decision = self.judge.evaluate_validation(source_report)
            self.shadow.observe_decision("judge", source_decision.verdict,
                                          confidence=source_decision.confidence,
                                          gate_violations=source_decision.gate_violations)
            self.store.write_json(ctx.run_id, "judge_source.json", {
                "verdict": source_decision.verdict,
                "confidence": source_decision.confidence,
                "gate_violations": source_decision.gate_violations,
                "suggestions": source_decision.suggestions,
            })

            # Step 3: Clean data (janitor)
            self.shadow.observe_task_start("janitor", "clean_data")
            schema_dtypes = _extract_dtypes(source_schema)
            required_fields = source_schema.get("required", [])
            cleaned_data = []
            cleaning_notes = []
            for i, record in enumerate(source_data):
                cleaned = clean_record(record, schema_dtypes)
                missing = validate_required(cleaned, required_fields)
                if missing:
                    cleaning_notes.append({
                        "record_index": i,
                        "product_code": record.get("product_code", ""),
                        "missing_required": missing,
                    })
                cleaned_data.append(cleaned)

            self.store.write_json(ctx.run_id, "cleaning_notes.json", cleaning_notes)
            self.shadow.observe_task_end("janitor", "clean_data", success=True,
                                         records_cleaned=len(cleaned_data),
                                         notes_count=len(cleaning_notes))

            # Step 4: Build transform plans
            self.shadow.observe_task_start("transform", "build_plans")
            transform_plans = {}
            for view_name, view_schema in view_schemas.items():
                plan = build_transform_plan(source_schema, view_schema, view_name)
                transform_plans[view_name] = plan

            self.store.write_json(ctx.run_id, "transform_plans.json", transform_plans)

            # Field matrix
            field_matrix = compute_field_matrix(source_schema, view_schemas)
            self.store.write_json(ctx.run_id, "field_matrix.json", field_matrix)
            self.shadow.observe_task_end("transform", "build_plans", success=True,
                                         view_count=len(transform_plans))

            # Step 5: Derive all views
            self.shadow.observe_task_start("transform", "derive_views")
            all_views = derive_all_views(cleaned_data, view_schemas)
            for view_name, view_data in all_views.items():
                self.store.write_json(ctx.run_id, f"view_{view_name}.json", view_data)
                ctx.artifacts[f"view_{view_name}"] = f"view_{view_name}.json"

            self.shadow.observe_task_end("transform", "derive_views", success=True,
                                         views_produced=list(all_views.keys()))

            # Step 6: Validate each view
            self.shadow.observe_task_start("schema_validator", "validate_views")
            view_reports = {}
            for view_name, view_schema in view_schemas.items():
                view_data = all_views.get(view_name, [])
                report = validate_dataset(
                    view_data, view_schema, run_id=ctx.run_id, data_path=f"view_{view_name}"
                )
                view_reports[view_name] = report
                self.store.write_json(ctx.run_id, f"validation_{view_name}.json", {
                    "view": view_name,
                    "total_records": report.total_records,
                    "valid_records": report.valid_records,
                    "violation_count": report.violation_count,
                    "is_valid": report.is_valid,
                    "violations": report.violations[:20],
                })

            # View coverage check
            coverage = validate_view_coverage(source_schema, view_schemas)
            self.store.write_json(ctx.run_id, "view_coverage.json", coverage)
            self.shadow.observe_task_end("schema_validator", "validate_views", success=True,
                                         coverage_pct=coverage.get("total_coverage_pct", 0))

            # Step 7: Judge evaluates all view transforms
            self.shadow.observe_task_start("judge", "evaluate_views")
            all_accepted = True
            for view_name, view_schema in view_schemas.items():
                view_data = all_views.get(view_name, [])
                decision = self.judge.evaluate_transform(
                    cleaned_data, view_data, view_schema
                )
                self.store.write_json(ctx.run_id, f"judge_{view_name}.json", {
                    "view": view_name,
                    "verdict": decision.verdict,
                    "confidence": decision.confidence,
                    "gate_violations": decision.gate_violations,
                    "suggestions": decision.suggestions,
                })
                if decision.verdict != "accept":
                    all_accepted = False
                    self.shadow.observe_decision("judge", decision.verdict,
                                                  view=view_name,
                                                  violations=decision.gate_violations)

            self.shadow.observe_task_end("judge", "evaluate_views", success=all_accepted)

            # Step 8: Detect anomalies in numeric fields
            self.shadow.observe_task_start("janitor", "detect_anomalies")
            numeric_fields = [f for f, t in schema_dtypes.items()
                              if t in ("number", "integer")]
            all_anomalies = []
            for field in numeric_fields:
                anomalies = detect_anomalies(cleaned_data, field)
                all_anomalies.extend(anomalies)
            self.store.write_json(ctx.run_id, "anomalies.json", all_anomalies)
            self.shadow.observe_task_end("janitor", "detect_anomalies",
                                         anomaly_count=len(all_anomalies))

            # Step 9: Save manifest and shadow summary
            self.store.save_manifest(ctx.run_id)
            shadow_summary = self.shadow.summary()
            self.store.write_json(ctx.run_id, "shadow_summary.json", shadow_summary)

            ctx.status = "completed"
            self.shadow.observe_task_end("puhemies", "pipeline", success=True)

            ctx.add_message("system", f"Pipeline completed: {ctx.run_id}")
            ctx.add_message("system", f"Views produced: {list(all_views.keys())}")
            ctx.add_message("system", f"Drift score: {self.shadow.drift_score:.4f}")

        except Exception as e:
            ctx.status = "failed"
            ctx.error = str(e)
            self.shadow.observe_error("puhemies", str(e))
            logger.exception("Pipeline failed")
            ctx.add_message("system", f"Pipeline failed: {e}")

        return ctx


def _extract_dtypes(schema: dict[str, Any]) -> dict[str, str]:
    """Extract field → dtype mapping from a JSON schema."""
    dtypes = {}
    for field, definition in schema.get("properties", {}).items():
        raw_type = definition.get("type", "string")
        if isinstance(raw_type, list):
            # Pick first non-null type
            raw_type = next((t for t in raw_type if t != "null"), "string")
        dtypes[field] = raw_type
    return dtypes
