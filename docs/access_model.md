# The Access Model

How The Foundry models a company through access, and the mismatches it exposes.

This is the conceptual reference. The contract lives in the schema
([`object_schema.json`](../schema/object_schema.json),
[`boxes.json`](../schema/boxes.json), [`roles.json`](../schema/roles.json)) and
the detection lives in [`runtime/foundry.py`](../runtime/foundry.py).

---

## Access, not titles

An org chart shows a company as boxes of titles. It does not tell you what anyone
can *affect*. The Foundry describes the company through **access**: which of the
five governed boxes a role can act in.

- **Actors** own objects (`owner_team`) and approve changes (`approver_role`).
- **Objects** flow through **boxes** (create / modify / plan / control / reference).
- **Roles** have *gravity* — a dominant box — but touch adjacent boxes too.
- **Evidence** (the `shadow.jsonl` audit trail) records what actually happened.

## Access as a claim, not a guarantee

The central rule:

> Access should be treated as a claim about responsibility. If access and
> responsibility do not match, the system exposes the mismatch.

Access is recorded in `roles.json` (`box_access`: who can act in each box).
Responsibility is recorded on each object (`owner_team`, `approver_role`). Because
they are separate, they can disagree — and that delta is the point.

---

## The mismatches the pipeline detects

Each is produced by `Foundry._detect_mismatches` and surfaced in the app's
**Access Mismatches** tab and the shadow log.

### 1. Approval without authority — `approval_without_authority`
A truth-touching change (create / modify / control), not yet committed, is routed to
an `approver_role` that has no control access in `roles.json`
(`box_access.control` = Manager, Director, SAP Owner).
**Reading:** someone is approving a change they are not authorised to govern — whether
it is a control approval, a price modify, or a new-item create. A supplier price list
routed to *Pricing* lands here: Pricing owns the number, but cannot make it truth.

### 2. Ownership without flow — `ownership_without_flow`
An object is `blocked`. Its `owner_team` is accountable, but it cannot move.
**Reading:** responsibility exists, but the work is stuck — a bottleneck with a name.

### 3. Editable without an approver — `editable_without_approver`
A box that can touch live truth (create / modify / control) has no `approver_role`
and is not yet committed.
**Reading:** a change can reach truth with nobody required to sign off.

### 4. Low-confidence truth — `low_confidence_truth`
An object is committed as `truth` while its triage `confidence` was below the high
band (0.7).
**Reading:** something was locked in as truth that the Foundry was unsure about.

---

## Why these, and not more

The model stays small on purpose: *simple boxes, clear routing, lower chaos.* Each
mismatch maps to a question a real operator asks when a field is wrong — *who could
change this, who was supposed to own it, who approved it, and how sure were we?*
The Foundry answers all four from the structured record, not from an org chart.

> Org charts show hierarchy. The Foundry shows how work actually happens.
