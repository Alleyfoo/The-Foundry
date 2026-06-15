# CLAUDE.md — The Foundry
## Session contract for Claude Code / Opus

---

## What we are building

**The Foundry** turns incoming business chaos into trusted, structured change.
Most systems describe a company through job titles. The Foundry describes it
through **access** — which governed action a role can take — and treats every
important object as something with an **owner, a state, and a lifecycle**.

> Org charts show hierarchy. The Foundry shows how work actually happens.
> Users see tools. The system sees governed change.

It is a Streamlit app over a pure-Python runtime. The runtime does the governance;
the UI is a thin shell. Swapping the UI should require zero runtime changes.

(Originally "The-spring", a fastener product-schema system. Evolved into The Foundry
from an 8-slide design deck. The fastener code lives in git history.)

---

## Core philosophy

- Documents are inputs, not the truth. The truth is the structured record.
- Every important object has an owner, a state, and a lifecycle.
- Urgency changes priority, not truthfulness.
- Access is a claim about responsibility. Where they disagree, expose the mismatch.
- Simple boxes. Clear routing. Lower chaos.
- Fast enough for the business. Structured enough for shared truth.

---

## Coding standards

- Readable by a kindergartener. Explicit over clever.
- Security and readability first, performance second.
- Every decision that touches data is logged (the shadow / invisible eye).
- Schema validation is the contract, not optional.
- No hidden state. No silent failures.
- If it cannot be expressed in a schema, it is not yet defined.

---

## The model

### The spine (every change travels this)
```
Inputs → Triage → Five Boxes → Impact → Approval → Commit
```
- **Inputs** — email, PDF, Excel, chat, form, API.
- **Triage** — what is it, what does it affect, how sure are we (confidence band).
- **Five Boxes** — sort into one governed action family.
- **Impact** — bottlenecks, aging, downstream effects.
- **Approval** — routed by confidence, risk, and ownership.
- **Commit** — written to the system of record + audit trail.

### The five boxes (governed action families)
`create` · `modify` · `plan` · `control` · `reference`
Defined in `schema/boxes.json`. A box is a governed route, not a folder.

### The governed object (`schema/object_schema.json`)
Every object carries: `world` (outside/internal), `object_type`, `box`, `stream`
(customer/item/supplier), `owner_team`, `state` (draft/active/pending/blocked/
retired), `commitment` (proposal/workflow/truth), `confidence`, `aging_days`,
`approver_role`, `lifecycle`, `evidence`, `downstream`, `system_of_record_ref`.

### Access (the org chart through access — `schema/roles.json`)
Roles have *gravity* — a dominant box — but touch adjacent boxes. `box_access`
records who can act in each box. Access ≠ title. Primary ownership ≠ exclusive
permission. Reference cuts across every level.

### Mismatches the pipeline exposes (`runtime/foundry.py`)
- `approval_without_authority` — control routed to a non-control role
- `ownership_without_flow` — owned but blocked
- `editable_without_approver` — can touch truth, no approver
- `low_confidence_truth` — committed as truth at low confidence

---

## Repo structure

```
/schema
    object_schema.json            — the governed object (source of truth)
    boxes.json                    — the five action families
    roles.json                    — role gravity + box access (the access model)
/data
    objects.json                  — sample in-flight objects across the three streams
/runtime
    foundry.py          — the pipeline: triage, impact, approval, access checks, lenses
    schema_validator.py — typed-box validation (generic, stdlib only)
    shadow.py           — the invisible eye (JSONL audit trail, drift metrics)
    artifact_store.py   — run artifacts + shadow log
    models.py           — dataclasses (RunContext, ShadowEntry, ValidationReport, ...)
/artifacts              — run outputs (gitignored)
/docs
    access_model.md     — the access model + the mismatches, in prose
streamlit_app.py        — the web frontend (thin shell)
requirements.txt        — streamlit + pandas (runtime is pure stdlib)
```

---

## Frontend (Streamlit)

`streamlit_app.py` — light theme matching the design mockup, components in `ui.py`.
Seven tabs: **Scenario** (guided walkthrough), **Objects** (intake + the clickable
Object Explorer with a detail panel), **Governance Map** (the signal/flow view),
**Ownership** (by domain), **Coverage** (governance grid + access mismatches),
**Bottlenecks & Risk** (bottlenecks + impact/approvals), **Model & Audit** (roles +
five boxes + monitoring lenses + audit trail). The pipeline runs automatically over
the live system-of-record state; the sidebar has Re-run + Reset-to-seed.

Run: `streamlit run streamlit_app.py`. Deploy: Streamlit Community Cloud, main file
`streamlit_app.py`, no secrets. NOTE: after changing `ui.py`, **reboot** the cloud
app (not just rerun) — Streamlit caches imported modules.

---

## Definition of done (current state — all met)

- Governed objects load and validate against the object schema (24/24 valid).
- The pipeline triages, finds bottlenecks/aging, routes approvals, and reports commit status.
- Access mismatches are detected for real and shown in the app + shadow log.
- Monitoring lenses (customer/sales/product/operations/finance) derive from the same objects.
- Streamlit app renders every tab (verified via `streamlit.testing.v1.AppTest`).
- README explains the model in plain language. MIT licensed.

---

## Notes

- Local first. No cloud dependency for core function. No Ollama needed.
- The shadow agent logs to JSONL always, no exceptions.
- Verify UI changes with `AppTest` (it executes the render path; a headless boot does not).
- Tests live in `/tests` (pytest). Run: `pip install -r requirements-dev.txt && pytest`.

---

*Documents are inputs, not the truth. The truth is the structured record.*
*Every important object has an owner, a state, and a lifecycle.*
*Fast enough for the business. Structured enough for shared truth.*
