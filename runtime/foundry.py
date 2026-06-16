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
    "Finance": "finance",
    "Suppliers": "product",
    "Research": "product",
    "Production": "operations",
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
        objects: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Run the full Foundry pipeline and return a render-ready result.

        If `objects` is given (e.g. the live system-of-record state), the pipeline
        runs over those; otherwise it loads the seed file.
        """
        ctx = RunContext(source_data_path=objects_path, source_schema_path=object_schema_path)
        self.shadow.bind_run(ctx.run_id)
        ctx.status = "running"

        self.shadow.observe_task_start("foundry", "pipeline", objects=objects_path)

        # Load (provided live state, or the seed file)
        objects = objects if objects is not None else load_objects(str(self.base_dir / objects_path))
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

        # 3b. Impact statements — what each change touches, and the risk
        self.shadow.observe_task_start("foundry", "impact_statements")
        obj_by_id = {o["object_id"]: o for o in objects}
        truth_touching = {b["id"] for b in boxes["boxes"] if b.get("touches_live_truth")}
        impact = self._impact_statements(objects, obj_by_id, truth_touching)
        impact_by_id = {i["object_id"]: i for i in impact}
        self.store.write_json(ctx.run_id, "impact.json", impact)
        self.shadow.observe_task_end("foundry", "impact_statements", success=True,
                                     high_risk=sum(1 for i in impact if i["risk"] == "high"))

        # 4. Approval routing — by confidence, risk, and ownership
        self.shadow.observe_task_start("foundry", "approval_routing")
        approvals = []
        for o in objects:
            if not o.get("approver_role") or o.get("commitment") == "truth":
                continue
            approvals.append(self._route_approval(o, impact_by_id, box_access))
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

        # 6b. Governance coverage — which areas are covered by functions, and how well
        self.shadow.observe_task_start("foundry", "coverage")
        coverage = self._coverage(objects, truth_touching, mismatches)
        self.store.write_json(ctx.run_id, "coverage.json", coverage)
        self.shadow.observe_task_end("foundry", "coverage", success=coverage["summary"]["red"] == 0,
                                     gaps=coverage["summary"]["red"])

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
            "impact": impact,
            "approvals": approvals,
            "coverage": coverage,
            "committed": committed,
            "in_flight": in_flight,
            "mismatches": mismatches,
            "lenses": lenses,
            "drift_score": self.shadow.drift_score,
            "metrics": self.shadow.summary(),
        }

    # ------------------------------------------------------------------
    def _impact_statements(
        self,
        objects: list[dict[str, Any]],
        obj_by_id: dict[str, dict[str, Any]],
        truth_touching: set[str],
    ) -> list[dict[str, Any]]:
        """For each object: what it touches, whether it affects truth, and the risk."""
        out = []
        for o in objects:
            downstream = o.get("downstream", [])
            touches = [obj_by_id[d]["title"] for d in downstream if d in obj_by_id]
            affects_truth = any(
                obj_by_id.get(d, {}).get("commitment") == "truth" for d in downstream
            )

            # Risk: explicit additive score, then banded.
            score = 0
            if o["box"] in truth_touching:
                score += 2
            conf = o.get("confidence", 1.0)
            score += 2 if conf < CONFIDENCE_LOW else 1 if conf < CONFIDENCE_HIGH else 0
            if affects_truth:
                score += 1
            if o.get("state") == "blocked":
                score += 1
            risk = "high" if score >= 4 else "medium" if score >= 2 else "low"

            verb = {"create": "Creating", "modify": "Modifying", "control": "Approving",
                    "plan": "Planning", "reference": "Referencing"}.get(o["box"], "Changing")
            parts = [f"{verb} '{o['title']}' touches {len(downstream)} downstream object(s)."]
            if affects_truth:
                parts.append("Affects committed truth.")
            if conf < CONFIDENCE_HIGH:
                parts.append(f"Triage confidence is {conf}.")
            if o.get("state") == "blocked":
                parts.append("Currently blocked.")

            out.append({
                "object_id": o["object_id"],
                "title": o["title"],
                "box": o["box"],
                "touches": touches,
                "downstream_count": len(downstream),
                "affects_truth": affects_truth,
                "risk": risk,
                "statement": " ".join(parts),
            })
        return out

    def _coverage(
        self,
        objects: list[dict[str, Any]],
        truth_touching: set[str],
        mismatches: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Which governed areas (stream x box) are covered by functions, and how well.

        green  = owned, approved where needed, no mismatch
        amber  = owned but weak (missing approver, or work stuck/aging)
        red    = an access mismatch (a segregation-of-duties gap)
        empty  = no objects here yet
        """
        streams = ["customer", "item", "supplier"]
        boxes = ["create", "modify", "plan", "control", "reference"]
        mm_ids = {m["object_id"] for m in mismatches}

        matrix = []
        for s in streams:
            for b in boxes:
                cell = [o for o in objects if o["stream"] == s and o["box"] == b]
                if not cell:
                    matrix.append({"stream": s, "box": b, "count": 0, "status": "empty",
                                   "owners": [], "mismatch_count": 0, "missing_approver": 0})
                    continue
                owners = sorted({o["owner_team"] for o in cell})
                mismatch_count = sum(1 for o in cell if o["object_id"] in mm_ids)
                missing_approver = sum(
                    1 for o in cell
                    if b in truth_touching and not o.get("approver_role") and o.get("commitment") != "truth"
                )
                stuck = sum(1 for o in cell if o.get("state") in ("blocked", "pending"))
                if mismatch_count:
                    status = "red"
                elif missing_approver or stuck:
                    status = "amber"
                else:
                    status = "green"
                matrix.append({"stream": s, "box": b, "count": len(cell), "status": status,
                               "owners": owners, "mismatch_count": mismatch_count,
                               "missing_approver": missing_approver})

        # How each function covers the areas it owns.
        funcs: dict[str, dict[str, Any]] = {}
        for o in objects:
            d = funcs.setdefault(o["owner_team"],
                                 {"owner_team": o["owner_team"], "objects": 0,
                                  "boxes": set(), "mismatches": 0})
            d["objects"] += 1
            d["boxes"].add(o["box"])
            if o["object_id"] in mm_ids:
                d["mismatches"] += 1
        by_function = []
        for d in funcs.values():
            d["boxes"] = sorted(d["boxes"])
            d["status"] = "red" if d["mismatches"] else "green"
            by_function.append(d)
        by_function.sort(key=lambda x: (-x["mismatches"], -x["objects"]))

        summary = {st: sum(1 for c in matrix if c["status"] == st)
                   for st in ("green", "amber", "red", "empty")}
        return {"matrix": matrix, "by_function": by_function, "summary": summary,
                "streams": streams, "boxes": boxes}

    def _route_approval(
        self,
        o: dict[str, Any],
        impact_by_id: dict[str, dict[str, Any]],
        box_access: dict[str, Any],
    ) -> dict[str, Any]:
        """Route a pending object by confidence, risk, and ownership."""
        risk = impact_by_id.get(o["object_id"], {}).get("risk", "low")
        conf = o.get("confidence", 1.0)
        aging = o.get("aging_days", 0)
        approver = o.get("approver_role")

        # Urgency changes priority, not truthfulness.
        priority = "high" if (aging >= AGING_ALERT_DAYS or risk == "high") else "normal"

        # Is the approver actually authorised to act in Control?
        ctrl = box_access.get("control", {})
        ctrl_allowed = {ctrl.get("primary")} | set(ctrl.get("also", []))
        if o["box"] == "control" and approver not in ctrl_allowed:
            recommendation = "reroute — approver not authorised for control"
        elif risk == "high" or conf < CONFIDENCE_LOW:
            recommendation = "needs human review"
        elif risk == "low" and conf >= CONFIDENCE_HIGH and o["box"] != "control":
            recommendation = "fast-track eligible"
        else:
            recommendation = "standard review"

        return {
            "object_id": o["object_id"],
            "title": o["title"],
            "box": o["box"],
            "owner_team": o["owner_team"],
            "routed_to": approver or "(no approver)",
            "confidence": conf,
            "risk": risk,
            "priority": priority,
            "recommendation": recommendation,
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

            # Any change that can become truth, routed to an approver who lacks
            # control authority — not just the control box. A price edit, a new
            # item, a master-data modify: if it touches live truth and the named
            # approver cannot act in control, that is approval without authority.
            if box in touches_truth and approver and not committed:
                allowed = {box_access.get("control", {}).get("primary")}
                allowed |= set(box_access.get("control", {}).get("also", []))
                if approver not in allowed:
                    out.append({"object_id": oid, "type": "approval_without_authority",
                                "detail": f"approver '{approver}' lacks control authority for this {box} change"})

            # Owner is accountable but the object is stuck — responsibility without flow.
            if state == "blocked":
                out.append({"object_id": oid, "type": "ownership_without_flow",
                            "detail": f"owned by {o['owner_team']} but blocked for {o.get('aging_days', 0)}d"})

            # Committed as truth while triage confidence was low.
            if committed and o.get("confidence", 1.0) < CONFIDENCE_HIGH:
                out.append({"object_id": oid, "type": "low_confidence_truth",
                            "detail": f"committed as truth at confidence {o.get('confidence')}"})
        return out
