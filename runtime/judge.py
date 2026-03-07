"""
Judge agent — healing-by-deepening.
Evaluates agent outputs against gates and triggers revision loops.
Ported from agent-learning/app/circuits/comparison_judge.py and review.py.
"""

from __future__ import annotations

from typing import Any

from runtime.models import JudgeDecision, ReviewReport, ValidationReport


class Judge:
    """Judge agent that evaluates outputs and decides accept/revise/escalate.

    Implements the "healing-by-deepening" pattern:
    - If output passes all gates → accept
    - If fixable violations exist and revision budget remains → revise
    - If critical violations or budget exhausted → escalate
    """

    def __init__(self, max_revisions: int = 3):
        self.max_revisions = max_revisions

    def evaluate_validation(
        self,
        report: ValidationReport,
        revision_count: int = 0,
    ) -> JudgeDecision:
        """Evaluate a validation report and decide next action."""
        gate_violations = []
        missing = []
        suggestions = []

        # Gate 1: Any validation errors?
        if not report.is_valid:
            gate_violations.append("validation_errors_present")
            # Categorize violations
            field_errors: dict[str, int] = {}
            for v in report.violations:
                field = v.get("field", "unknown")
                field_errors[field] = field_errors.get(field, 0) + 1

            for field, count in field_errors.items():
                suggestions.append(f"Fix {count} error(s) in field '{field}'")

        # Gate 2: Coverage threshold
        if report.total_records > 0:
            coverage = report.valid_records / report.total_records
            if coverage < 0.8:
                gate_violations.append(f"coverage_below_80pct ({coverage:.0%})")
                suggestions.append("Too many invalid records — check data source quality")

        # Gate 3: Warnings threshold
        if report.warning_count > report.total_records * 0.5:
            gate_violations.append("excessive_warnings")
            suggestions.append("High warning rate — review schema for overly strict constraints")

        # Decision logic
        if not gate_violations:
            verdict = "accept"
            confidence = 1.0
        elif revision_count >= self.max_revisions:
            verdict = "escalate"
            confidence = 0.3
            suggestions.append(f"Max revisions ({self.max_revisions}) reached — human review needed")
        else:
            verdict = "revise"
            confidence = max(0.1, 1.0 - len(gate_violations) * 0.2)

        return JudgeDecision(
            verdict=verdict,
            confidence=confidence,
            gate_violations=gate_violations,
            missing_deliverables=missing,
            suggestions=suggestions,
            revision_count=revision_count,
            max_revisions=self.max_revisions,
        )

    def evaluate_transform(
        self,
        source_records: list[dict],
        transformed_records: list[dict],
        view_schema: dict[str, Any],
        revision_count: int = 0,
    ) -> JudgeDecision:
        """Evaluate a transform output against the target view schema."""
        gate_violations = []
        suggestions = []

        view_fields = set(view_schema.get("properties", {}).keys())
        required = set(view_schema.get("required", []))

        # Gate 1: Record count preserved
        if len(transformed_records) != len(source_records):
            gate_violations.append(
                f"record_count_mismatch (source={len(source_records)}, "
                f"transformed={len(transformed_records)})"
            )

        # Gate 2: All required fields present
        if transformed_records:
            sample = transformed_records[0]
            missing_required = required - set(sample.keys())
            if missing_required:
                gate_violations.append(f"missing_required_fields: {sorted(missing_required)}")
                suggestions.append(f"Add missing required fields: {sorted(missing_required)}")

        # Gate 3: No extra fields outside view schema
        if transformed_records:
            sample = transformed_records[0]
            extra = set(sample.keys()) - view_fields
            # _view_metadata is allowed as a non-data field
            extra.discard("_view_metadata")
            if extra:
                gate_violations.append(f"extra_fields_not_in_schema: {sorted(extra)}")
                suggestions.append(f"Remove fields not in view schema: {sorted(extra)}")

        # Gate 4: No null required fields
        null_required_count = 0
        for record in transformed_records:
            for field in required:
                if record.get(field) is None:
                    null_required_count += 1
        if null_required_count > 0:
            gate_violations.append(f"null_required_fields ({null_required_count} occurrences)")

        # Decision
        if not gate_violations:
            verdict = "accept"
            confidence = 1.0
        elif revision_count >= self.max_revisions:
            verdict = "escalate"
            confidence = 0.3
        else:
            verdict = "revise"
            confidence = max(0.1, 1.0 - len(gate_violations) * 0.2)

        return JudgeDecision(
            verdict=verdict,
            confidence=confidence,
            gate_violations=gate_violations,
            suggestions=suggestions,
            revision_count=revision_count,
            max_revisions=self.max_revisions,
        )

    def review_coverage(
        self,
        expected_sections: list[str],
        actual_sections: list[str],
    ) -> ReviewReport:
        """Review whether all expected sections/deliverables are covered."""
        expected_set = set(expected_sections)
        actual_set = set(actual_sections)
        missing = sorted(expected_set - actual_set)
        covered = expected_set & actual_set

        coverage = len(covered) / max(1, len(expected_set))

        return ReviewReport(
            coverage=round(coverage, 3),
            missing_sections=missing,
            format_ok=True,
            content_ok=coverage >= 0.8,
            decision="accept" if coverage >= 0.9 else "revise",
            notes=f"Coverage: {coverage:.0%}, missing: {missing}" if missing else "Full coverage",
        )
