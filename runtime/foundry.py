"""
The Foundry pipeline.

Takes governed objects (data/objects.json) and runs them through the deck's
spine: intake -> triage -> impact -> approval routing -> commit. Along the way
it surfaces bottlenecks, aging, access mismatches, and monitoring lenses.

Reuses the runtime core: schema validation, the shadow audit log, and the
artifact store. The Foundry orchestrates; it never changes an object silently —
every step is logged.

    from runtime.foundry import Foundry
    result = Foundry(base_dir=".").run()
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runtime.artifact_store import ArtifactStore
from runtime.schema_validator import load_schema, validate_dataset
from runtime.shadow import ShadowAgent
from runtime.models import RunContext

# Operational thresholds — explicit, not magic.
AGING_ALERT_DAYS = 5          # an object older than this in a waiting state is "aging"
CONFIDENCE_HIGH = 0.7         # at or above: high triage confidence
CONFIDENCE_LOW = 0.4          # below: low confidence, needs a human

# Which monitoring lens each owning team rolls up into (slide: monitoring lenses).
LENS_BY_TEAM = {
    "Sales": "sales",
    "Product Data": "product",
    "Product Manager": "product",
    "Product Owner": "product",
    "Operations": "operations",
    "SAP Owner": "operations",
    "Records Owner": "operations",
    "Pricing": "finance",
    "Suppliers": "product",
    "Manager": "operations",
}


def load_objects(path: str) -> list[dict[str, Any]]:
    """Load the governed objects from disk."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return raw.get("objects", raw) if isinstance(raw, dict) else raw


def confidence_band(value: float) -> str:
    """Translate a confidence score into a plain band."""
    if value >= CONFIDENCE_HIGH:
        return "high"
    if value < CONFIDENCE_LOW:
        return "low"
    return "medium"


class Foundry:
    """Orchestrates the governed-change pipeline over the object set."""

    def __init__(self, base_dir: str = ".", artifacts_dir: str = "artifacts"):
        self.base_dir = Path(base_dir)
        self.store = ArtifactStore(artifacts_dir)
        self.shadow = ShadowAgent(self.store)

    # ------------------------------------------------------------------
    def run(
        self,
        objects_path: str = "data/objects.json",
        object_schema_path: str = "schema/object_schema.json",
        boxes_path: str = "schema/boxes.json",
        roles_path: str = "schema/roles.json",
    ) -> dict[str, Any]:
        """Run the full Foundry pipeline and return a render-ready result."""
        ctx = RunContext(source_data_path=objects_path, source_schema_path=object_schema_path)
        self.shadow.bind_run(ctx.run_id)
        ctx.status = "running"

        self.shadow.observe_task_start("foundry", "pipeline", objects=objects_path)

        # Load
        objects = load_objects(str(self.base_dir / objects_path))
        schema = load_schema(str(self.base_dir / object_schema_path))
        boxes = json.loads((self.base_dir / boxes_path).read_text(encoding="utf-8"))
        roles = json.loads((self.base_dir / roles_path).read_text(encoding="utf-8"))
        box_access = roles.get("access_model", {}).get("box_access", {})

        # 1. Validate (typed box — is each object well-formed?)
        self.shadow.observe_task_start("schema_validator", "validate_objects")
        report = validate_dataset(objects, schema, run_id=ctx.run_id, data_path=objects_path)
        self.store.write_json(ctx.run_id, "validation_objects.json", {
            "total_records": report.total_records,
            "valid_records": report.valid_records,
            "violation_count": report.violation_count,
            "is_valid": report.is_valid,
            "violations": report.violations[:50],
        })
        self.shadow.observe_task_end("schema_validator", "validate_objects",
                                     success=report.is_valid,
                                     valid=report.valid_records, total=report.total_records)

        # 2. Triage — confidence banding
        self.shadow.observe_task_start("foundry", "triage")
        triage = [
            {
                "object_id": o["object_id"],
                "box": o["box"],
                "confidence": o.get("confidence", 0.0),
                "band": confidence_band(o.get("confidence", 0.0)),
                "needs_human": confidence_band(o.get("confidence", 0.0)) == "low",
            }
            for o in objects
        ]
        needs_human = [t["object_id"] for t in triage if t["needs_human"]]
        self.store.write_json(ctx.run_id, "triage.json", triage)
        self.shadow.observe_task_end("foundry", "triage", success=True,
                                     low_confidence=len(needs_human))

        # 3. Impact — bottlenecks and aging
        self.shadow.observe_task_start("foundry", "impact")
        bottlenecks = []
        for o in objects:
            blocked = o.get("state") == "blocked"
            aging = o.get("aging_days", 0) >= AGING_ALERT_DAYS and o.get("state") in ("pending", "blocked")
            if blocked or aging:
                bottlenecks.append({
                    "object_id": o["object_id"],
                    "title": o["title"],
                    "owner_team": o["owner_team"],
                    "state": o["state"],
                    "aging_days": o.get("aging_days", 0),
                    "downstream_count": len(o.get("downstream", [])),
                    "reason": "blocked" if blocked else "aging",
                })
        bottlenecks.sort(key=lambda b: (b["state"] != "blocked", -b["aging_days"]))
        self.store.write_json(ctx.run_id, "bottlenecks.json", bottlenecks)
        self.shadow.observe_task_end("foundry", "impact", success=True,
                                     bottleneck_count=len(bottlenecks))

        # 4. Approval routing
        self.shadow.observe_task_start("foundry", "approval_routing")
        approvals = [
            {
                "object_id": o["object_id"],
                "title": o["title"],
                "box": o["box"],
                "owner_team": o["owner_team"],
                "approver_role": o.get("approver_role"),
                "state": o["state"],
                "routed_to": o.get("approver_role") or "(no approver)",
            }
            for o in objects
            if o.get("approver_role") and o.get("commitment") != "truth"
        ]
        self.store.write_json(ctx.run_id, "approvals.json", approvals)
        self.shadow.observe_task_end("foundry", "approval_routing", success=True,
                                     pending_approvals=len(approvals))

        # 5. Commit status — what is trusted truth vs still in flight
        committed = [o["object_id"] for o in objects
                     if o.get("commitment") == "truth" and o.get("system_of_record_ref")]
        in_flight = [o["object_id"] for o in objects if o["object_id"] not in committed]
        self.store.write_json(ctx.run_id, "commit_status.json", {
            "committed_to_truth": committed,
            "in_flight": in_flight,
        })

        # 6. Access mismatches — the access-first payoff
        self.shadow.observe_task_start("foundry", "access_check")
        mismatches = self._detect_mismatches(objects, boxes, box_access)
        self.store.write_json(ctx.run_id, "access_mismatches.json", mismatches)
        for m in mismatches:
            self.shadow.observe("access_mismatch", "foundry", m)
        self.shadow.observe_task_end("foundry", "access_check", success=len(mismatches) == 0,
                                     mismatch_count=len(mismatches))

        # 7. Monitoring lenses — same objects, different maps
        self.shadow.observe_task_start("foundry", "lenses")
        lenses: dict[str, list[str]] = {l: [] for l in roles.get("monitoring_lenses", [])}
        lenses.setdefault("customer", [])
        for o in objects:
            if o.get("stream") == "customer":
                lenses["customer"].append(o["object_id"])
            lens = LENS_BY_TEAM.get(o.get("owner_team", ""))
            if lens and lens in lenses and o["object_id"] not in lenses[lens]:
                lenses[lens].append(o["object_id"])
        self.store.write_json(ctx.run_id, "lenses.json", lenses)
        self.shadow.observe_task_end("foundry", "lenses", success=True)

        # Wrap up
        self.store.save_manifest(ctx.run_id)
        self.store.write_json(ctx.run_id, "shadow_summary.json", self.shadow.summary())
        ctx.status = "completed"
        self.shadow.observe_task_end("foundry", "pipeline", success=True)

        return {
            "run_id": ctx.run_id,
            "status": ctx.status,
            "store": self.store,
            "shadow": self.shadow,
            "objects": objects,
            "boxes": boxes,
            "roles": roles,
            "validation": report,
            "triage": triage,
            "bottlenecks": bottlenecks,
            "approvals": approvals,
            "committed": committed,
            "in_flight": in_flight,
            "mismatches": mismatches,
            "lenses": lenses,
            "drift_score": self.shadow.drift_score,
            "metrics": self.shadow.summary(),
        }

    # ------------------------------------------------------------------
    def _detect_mismatches(
        self,
        objects: list[dict[str, Any]],
        boxes: dict[str, Any],
        box_access: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Where access and responsibility disagree, expose it — don't paper over it."""
        touches_truth = {b["id"] for b in boxes["boxes"] if b.get("touches_live_truth")}
        out = []
        for o in objects:
            oid, box, state = o["object_id"], o["box"], o.get("state")
            approver = o.get("approver_role")
            committed = o.get("commitment") == "truth"

            # Editable object that can change truth, with no declared approver.
            if box in touches_truth and not approver and not committed:
                out.append({"object_id": oid, "type": "editable_without_approver",
                            "detail": f"{box} object can change truth but has no approver"})

            # Control (approval) routed to a role that has no control access.
            if box == "control" and approver:
                allowed = {box_access.get("control", {}).get("primary")}
                allowed |= set(box_access.get("control", {}).get("also", []))
                if approver not in allowed:
                    out.append({"object_id": oid, "type": "approval_without_authority",
                                "detail": f"approver '{approver}' is not authorised for control"})

            # Owner is accountable but the object is stuck — responsibility without flow.
            if state == "blocked":
                out.append({"object_id": oid, "type": "ownership_without_flow",
                            "detail": f"owned by {o['owner_team']} but blocked for {o.get('aging_days', 0)}d"})

            # Committed as truth while triage confidence was low.
            if committed and o.get("confidence", 1.0) < CONFIDENCE_HIGH:
                out.append({"object_id": oid, "type": "low_confidence_truth",
                            "detail": f"committed as truth at confidence {o.get('confidence')}"})
        return out
