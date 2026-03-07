"""
Shadow agent — the invisible eye.
Observes all agent activity, logs to JSONL, tracks drift metrics.
Ported from agent-learning/app/agents/shadow.py and Data-agents-demo/agent-base/agents/shadow.agent.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from runtime.artifact_store import ArtifactStore
from runtime.models import ShadowEntry


@dataclass
class DriftMetrics:
    """Metrics tracked by the shadow agent for drift detection."""

    format_violations: int = 0
    schema_mismatches: int = 0
    revision_count: int = 0
    validation_failures: int = 0
    total_events: int = 0
    error_count: int = 0

    @property
    def drift_score(self) -> float:
        """Calculate overall drift score (0.0 = no drift, 1.0 = severe drift)."""
        if self.total_events == 0:
            return 0.0
        penalties = (
            self.format_violations * 0.3
            + self.schema_mismatches * 0.25
            + self.revision_count * 0.15
            + self.validation_failures * 0.2
            + self.error_count * 0.4
        )
        raw = penalties / max(1, self.total_events)
        return min(1.0, raw)


class ShadowAgent:
    """Pure observer that records all agent activity.

    Contract (from shadow.agent.md):
    - NEVER intervene or modify data
    - Record every event, decision, and drift note
    - Write to JSONL shadow log
    - Calculate drift metrics on demand
    """

    def __init__(self, artifact_store: ArtifactStore | None = None):
        self._store = artifact_store
        self._entries: list[ShadowEntry] = []
        self._metrics = DriftMetrics()
        self._run_id: str = ""

    def bind_run(self, run_id: str) -> None:
        """Bind to a specific run for logging."""
        self._run_id = run_id
        self._entries.clear()
        self._metrics = DriftMetrics()

    def observe(
        self,
        event_type: str,
        agent_name: str,
        detail: dict[str, Any] | None = None,
    ) -> ShadowEntry:
        """Record an observation."""
        entry = ShadowEntry(
            run_id=self._run_id,
            event_type=event_type,
            agent_name=agent_name,
            detail=detail or {},
            drift_score=self._metrics.drift_score,
        )
        self._entries.append(entry)
        self._metrics.total_events += 1

        # Update drift metrics based on event type
        if event_type == "error":
            self._metrics.error_count += 1
        elif event_type == "format_violation":
            self._metrics.format_violations += 1
        elif event_type == "schema_mismatch":
            self._metrics.schema_mismatches += 1
        elif event_type == "revision":
            self._metrics.revision_count += 1
        elif event_type == "validation_failure":
            self._metrics.validation_failures += 1

        # Persist to JSONL if store is available
        if self._store and self._run_id:
            self._store.append_shadow(self._run_id, {
                "run_id": entry.run_id,
                "timestamp": entry.timestamp,
                "event_type": entry.event_type,
                "agent_name": entry.agent_name,
                "detail": entry.detail,
                "drift_score": entry.drift_score,
            })

        return entry

    def observe_task_start(self, agent_name: str, task_type: str, **kwargs) -> ShadowEntry:
        return self.observe("task_start", agent_name, {"task_type": task_type, **kwargs})

    def observe_task_end(self, agent_name: str, task_type: str, success: bool = True, **kwargs) -> ShadowEntry:
        return self.observe("task_end", agent_name, {"task_type": task_type, "success": success, **kwargs})

    def observe_decision(self, agent_name: str, decision: str, **kwargs) -> ShadowEntry:
        return self.observe("decision", agent_name, {"decision": decision, **kwargs})

    def observe_error(self, agent_name: str, error: str, **kwargs) -> ShadowEntry:
        return self.observe("error", agent_name, {"error": error, **kwargs})

    def observe_drift(self, agent_name: str, drift_type: str, **kwargs) -> ShadowEntry:
        return self.observe("drift", agent_name, {"drift_type": drift_type, **kwargs})

    @property
    def drift_score(self) -> float:
        return self._metrics.drift_score

    @property
    def metrics(self) -> DriftMetrics:
        return self._metrics

    @property
    def entries(self) -> list[ShadowEntry]:
        return list(self._entries)

    def summary(self) -> dict[str, Any]:
        """Produce a summary of the current run's observations."""
        return {
            "run_id": self._run_id,
            "total_events": self._metrics.total_events,
            "error_count": self._metrics.error_count,
            "format_violations": self._metrics.format_violations,
            "schema_mismatches": self._metrics.schema_mismatches,
            "revision_count": self._metrics.revision_count,
            "validation_failures": self._metrics.validation_failures,
            "drift_score": round(self._metrics.drift_score, 4),
            "event_types": _count_by(self._entries, lambda e: e.event_type),
            "agents_involved": _count_by(self._entries, lambda e: e.agent_name),
        }


def _count_by(entries: list[ShadowEntry], key_fn) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in entries:
        k = key_fn(e)
        counts[k] = counts.get(k, 0) + 1
    return counts
