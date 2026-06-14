"""
Actions — the state machine and the intake/triage that make the spine run.

Intake turns a raw input into a governed object (triage sorts it into a box with a
confidence). Actions move an object along its lifecycle:

    draft -> active -> pending -> active -> (commit) truth
                          \-> blocked -> active

Every action checks access (approving is a Control action — only a control-
authorised role may do it) and is recorded in the system-of-record event log.
Standard library only; no LLM needed.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from runtime.system_of_record import SystemOfRecord

# --- Triage: keyword rules that sort raw text into one of the five boxes. -------
BOX_KEYWORDS = {
    "control": ["approve", "reject", "escalat", "exception", "release", "sign off", "sign-off"],
    "plan": ["roadmap", "plan", "future", "next quarter", "draft launch", "strategy"],
    "modify": ["update", "change", "price", "lead time", "correct", "fix", "revise", "adjust"],
    "reference": ["spec", "certificate", "datasheet", "attach", "evidence", "document", "manual"],
    "create": ["new", "add", "create", "request", "onboard", "introduce"],
}

# Defaults applied to a freshly triaged object, per box.
DEFAULT_OWNER = {
    "create": "Sales", "modify": "Product Data", "plan": "Product Manager",
    "control": "Manager", "reference": "Suppliers",
}
TRUTH_TOUCHING = {"create", "modify", "control"}

STREAM_KEYWORDS = {
    "customer": ["customer", "client", "signal", "feature", "contact"],
    "supplier": ["supplier", "vendor", "datasheet", "material", "certificate"],
    "item": ["item", "product", "sku", "price", "availability"],
}


def triage_text(raw_text: str) -> dict[str, Any]:
    """Classify a raw input into a box + stream, with a confidence score."""
    text = (raw_text or "").lower()

    box_hits = {box: sum(1 for k in kws if k in text) for box, kws in BOX_KEYWORDS.items()}
    best_box = max(box_hits, key=box_hits.get)
    top = box_hits[best_box]
    if top == 0:
        best_box, confidence = "reference", 0.3          # can't tell — park it as reference
    else:
        # more / clearer matches = higher confidence, capped sensibly
        confidence = min(0.95, 0.5 + 0.2 * top)

    stream_hits = {s: sum(1 for k in kws if k in text) for s, kws in STREAM_KEYWORDS.items()}
    best_stream = max(stream_hits, key=stream_hits.get)
    if stream_hits[best_stream] == 0:
        best_stream = "item"

    return {"box": best_box, "stream": best_stream, "confidence": round(confidence, 2)}


def intake(sor: SystemOfRecord, raw_text: str, source_input: str = "form") -> dict[str, Any]:
    """Forge a raw input into a new governed object and store it."""
    t = triage_text(raw_text)
    box = t["box"]
    today = date.today().isoformat()
    obj = {
        "object_id": sor.next_object_id(),
        "object_type": "Item Request" if box == "create" else "Reference Object",
        "world": "outside",
        "title": raw_text.strip()[:200] or "Untitled input",
        "box": box,
        "stream": t["stream"],
        "owner_team": DEFAULT_OWNER[box],
        "state": "draft",
        "commitment": "proposal",
        "confidence": t["confidence"],
        "aging_days": 0,
        "approver_role": "Manager" if box in TRUTH_TOUCHING else None,
        "source_input": source_input,
        "lifecycle": "none",
        "evidence": [],
        "downstream": [],
        "system_of_record_ref": None,
        "created_at": today,
        "updated_at": today,
    }
    sor.upsert(obj)
    sor.add_event(obj["object_id"], "intake", None, "draft", "system",
                  f"triaged into {box} (confidence {t['confidence']})")
    return obj


# --- State machine -------------------------------------------------------------
# action -> (allowed from states, resulting state)
TRANSITIONS: dict[str, dict[str, Any]] = {
    "activate": {"from": ["draft"], "to": "active"},
    "submit":   {"from": ["active"], "to": "pending"},
    "approve":  {"from": ["pending"], "to": "active", "commitment": "workflow", "control": True},
    "reject":   {"from": ["pending"], "to": "blocked", "control": True},
    "block":    {"from": ["draft", "active", "pending"], "to": "blocked"},
    "unblock":  {"from": ["blocked"], "to": "active"},
    "commit":   {"from": ["active"], "to": "active", "commitment": "truth", "needs_workflow": True},
    "mark_eol": {"from": ["active"], "to": "active", "lifecycle": "end_of_life"},
    "retire":   {"from": ["active", "blocked"], "to": "retired"},
    # Disposition — how an object leaves (the deck's afterlife).
    "archive":          {"from": ["retired"], "to": "retired", "lifecycle": "archived"},
    "scrap":            {"from": ["retired"], "to": "retired", "lifecycle": "scrap"},
    "link_replacement": {"from": ["retired"], "to": "retired", "lifecycle": "replacement_linked"},
}


def available_actions(obj: dict[str, Any]) -> list[str]:
    """Which actions are valid from this object's current state right now."""
    out = []
    for action, rule in TRANSITIONS.items():
        if obj.get("state") not in rule["from"]:
            continue
        if rule.get("needs_workflow") and obj.get("commitment") != "workflow":
            continue  # can only commit something that has been approved into workflow
        out.append(action)
    return out


def _control_authorised(actor_role: str, access_model: dict[str, Any]) -> bool:
    ctrl = access_model.get("box_access", {}).get("control", {})
    allowed = {ctrl.get("primary")} | set(ctrl.get("also", []))
    return actor_role in allowed


def apply_action(
    sor: SystemOfRecord,
    object_id: str,
    action: str,
    actor_role: str,
    access_model: dict[str, Any],
) -> dict[str, Any]:
    """Apply an action to an object. Returns {ok, message, object}."""
    obj = sor.get(object_id)
    if obj is None:
        return {"ok": False, "message": f"{object_id} not found", "object": None}

    rule = TRANSITIONS.get(action)
    if rule is None or action not in available_actions(obj):
        return {"ok": False, "message": f"'{action}' not allowed from state '{obj.get('state')}'",
                "object": obj}

    # Access guard: approving / rejecting is a Control action.
    if rule.get("control") and not _control_authorised(actor_role, access_model):
        sor.add_event(object_id, action + "_refused", obj.get("state"), obj.get("state"),
                      actor_role, "access mismatch: not authorised for control")
        return {"ok": False,
                "message": f"Access mismatch — '{actor_role}' is not authorised to act in Control.",
                "object": obj}

    from_state = obj.get("state")
    obj["state"] = rule["to"]
    if "commitment" in rule:
        obj["commitment"] = rule["commitment"]
    if "lifecycle" in rule:
        obj["lifecycle"] = rule["lifecycle"]
    if action == "commit":
        obj["commitment"] = "truth"
        obj["system_of_record_ref"] = _sor_ref(obj)
    obj["aging_days"] = 0
    obj["updated_at"] = date.today().isoformat()

    sor.upsert(obj)
    sor.add_event(object_id, action, from_state, obj["state"], actor_role,
                  f"commitment={obj.get('commitment')}")
    return {"ok": True, "message": f"{object_id}: {action} → {obj['state']}", "object": obj}


def _sor_ref(obj: dict[str, Any]) -> str:
    """Mint a system-of-record reference, e.g. SAP-ITEMREQUEST-IN1."""
    kind = obj.get("object_type", "OBJ").upper().replace(" ", "")
    tail = obj["object_id"].split("-")[-1]
    return f"SAP-{kind}-{tail}"
