"""
Data models for inter-agent communication.
Ported from agent-learning/app/models.py and adapted for schema-driven product system.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Message:
    """Single message in the agent conversation."""

    role: str  # "user", "agent", "system", "shadow"
    content: str
    agent_name: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskSpec:
    """Specification for a task to be executed by an agent."""

    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_type: str = ""  # "validate", "transform", "clean", "derive_view"
    description: str = ""
    input_artifact_keys: list[str] = field(default_factory=list)
    output_artifact_key: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class SchemaSpec:
    """Schema specification produced by the schema agent."""

    fields: list[dict[str, Any]] = field(default_factory=list)
    required: list[str] = field(default_factory=list)
    dtypes: dict[str, str] = field(default_factory=dict)
    source_schema_path: str = ""
    view_name: str = ""


@dataclass
class TransformPlan:
    """Plan for transforming source data to a view."""

    view_name: str = ""
    include_fields: list[str] = field(default_factory=list)
    exclude_fields: list[str] = field(default_factory=list)
    rename_fields: dict[str, str] = field(default_factory=dict)
    computed_fields: list[dict[str, Any]] = field(default_factory=list)
    filter_rules: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Report from the validation agent."""

    run_id: str = ""
    schema_path: str = ""
    data_path: str = ""
    total_records: int = 0
    valid_records: int = 0
    violations: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    is_valid: bool = True
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


@dataclass
class JudgeDecision:
    """Decision from the judge agent."""

    verdict: str = "accept"  # "accept", "revise", "escalate"
    confidence: float = 1.0
    gate_violations: list[str] = field(default_factory=list)
    missing_deliverables: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    revision_count: int = 0
    max_revisions: int = 3
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def should_revise(self) -> bool:
        return self.verdict == "revise" and self.revision_count < self.max_revisions


@dataclass
class ReviewReport:
    """Review report assessing agent output quality."""

    coverage: float = 0.0  # 0.0 to 1.0
    missing_sections: list[str] = field(default_factory=list)
    format_ok: bool = True
    content_ok: bool = True
    decision: str = "accept"  # "accept", "revise"
    notes: str = ""


@dataclass
class ShadowEntry:
    """Single entry in the shadow log (JSONL)."""

    run_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    event_type: str = ""  # "task_start", "task_end", "decision", "error", "drift"
    agent_name: str = ""
    detail: dict[str, Any] = field(default_factory=dict)
    drift_score: float = 0.0


@dataclass
class RunContext:
    """Context for a single orchestration run."""

    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source_data_path: str = ""
    source_schema_path: str = ""
    view_schemas: dict[str, str] = field(default_factory=dict)  # view_name -> path
    artifacts: dict[str, str] = field(default_factory=dict)  # artifact_key -> path
    messages: list[Message] = field(default_factory=list)
    shadow_log: list[ShadowEntry] = field(default_factory=list)
    status: str = "pending"  # "pending", "running", "completed", "failed"
    error: str = ""

    def add_message(self, role: str, content: str, agent_name: str = "") -> Message:
        msg = Message(role=role, content=content, agent_name=agent_name)
        self.messages.append(msg)
        return msg

    def add_shadow(self, event_type: str, agent_name: str, detail: dict | None = None) -> ShadowEntry:
        entry = ShadowEntry(
            run_id=self.run_id,
            event_type=event_type,
            agent_name=agent_name,
            detail=detail or {},
        )
        self.shadow_log.append(entry)
        return entry
