# The Foundry — Plan & Roadmap

Two plans: what is left to build (programside), and how it should look (visual).
Status as of 2026-06-23.

> **Current status:** P1, P2, P3, the visual reskin, Signal Universe, the two
> guided Scenario walkthroughs, and Governance Coverage are all done. The app now
> tells the core idea as a working concept demo: incoming change becomes a governed
> object, moves through the spine, and is blocked from becoming truth when
> authority, responsibility, or confidence do not line up. Target audience for the
> current share is peers / portfolio. It is a concept demo, not a product.

---

## Where we are (baseline)

Built and working end-to-end:

- Object model — `schema/object_schema.json`, `boxes.json`, `roles.json`
- 27 governed objects across customer / item / supplier streams after runtime
  seeding and scenario data.
- Pipeline (`runtime/foundry.py`): validate → triage (confidence band) → impact
  (bottlenecks + aging) → approval routing → commit status → access mismatches →
  monitoring lenses.
- Stateful runtime over a SQLite system-of-record stand-in (`artifacts/foundry.db`):
  intake can forge draft objects, actions can move state, and commits mint
  system-of-record references with an event log.
- Streamlit app, 8 tabs, with audit trail; MIT licensed; deployable.

**Current limitation:** this is still a concept demo, not an integrated enterprise
product. It proves the governed-change primitive and the authority gate with local
sample data; it does not yet ingest real mailboxes, SAP records, ERP workflows, or
identity/access data.

---

## Programside plan

Ordered by how much each makes the demo *true*, not just prettier.

### P1 — Make the spine actually run  ✅ DONE (commits f3082e0, 5516bf9)

- [x] **1. Intake + triage.** `runtime/actions.py::triage_text/intake` — keyword
      rules sort a raw input into a box with a confidence; the Intake tab shows a
      live preview and forges a draft object.
- [x] **2. Actions + state machine.** `runtime/actions.py` — `draft → active →
      pending → active → (commit) truth`, plus block / unblock / retire. Approve and
      reject are Control actions, guarded by the access model (unauthorised role
      refused). The Actions tab drives it.
- [x] **3. Commit to a system of record.** `runtime/system_of_record.py` — SQLite
      stand-in for SAP, seeded from `objects.json`, persists between runs
      (`artifacts/foundry.db`). Commit flips `commitment → truth` and mints a
      `system_of_record_ref`; every transition is in the event log.

### P2 — Make it analytically real  ✅ DONE (commit fc36bd2)

- [x] **4. Impact statements.** `foundry.py::_impact_statements` — per object: what
      it touches, whether it affects committed truth, and a banded risk (explicit
      additive score). Shown in the Impact & Approvals tab.
- [x] **5. Richer approval routing.** `foundry.py::_route_approval` — routes by
      confidence + risk + ownership; priority reflects urgency (aging); recommends
      fast-track / standard / human-review / reroute (when the approver isn't
      authorised for Control).
- [x] **6. Lifecycle / disposition.** `actions.py` — mark_eol / archive / scrap /
      link_replacement. The Governance Map shows the lifecycle/afterlife.

### P3 — Hardening for public  ✅ DONE

- [x] **7. `/tests`.** pytest suite in `/tests` — schema validation, system of record,
      actions/state-machine/access-guard, and the pipeline (bottlenecks, mismatches,
      coverage, lenses, generalized authority rule) + an AppTest render smoke test.
      24 tests. Run: `pip install -r requirements-dev.txt && python -m pytest`.
- [x] **8. Housekeeping.** Removed the orphaned `definition_of_definition.json` (no
      code used it) and the stale `agent.md`; object-id generation done in P1.

**Status:** P1, P2, P3, the reskin, Signal Universe, the two Scenario walkthroughs,
and Coverage are all done.

---

## Visual plan  ✅ DONE (commit 6e99b35)

> Reskinned to match the designer's mockup (`dashboard/`, gitignored). Light theme,
> Archivo type, navy/orange palette. Implemented in `ui.py` (tokens + CSS +
> component renderers) and wired through `streamlit_app.py`. Verified with
> screenshots against the mockup. The Governance Map uses styled HTML flow cards,
> and Signal Universe uses `streamlit-agraph` for the interactive graph.

Make it look like the deck. The current UI is now polished enough to share as a
concept demo; future work should focus on clarity, pacing, and evidence rather than
adding decorative surface area.

### Design system (do this first)
- Palette from the deck: navy `#0f2a4d`, blue, orange `#e8732a`, teal.
- Status legend, used everywhere: **green = flowing, amber = pending, red ! = stuck,
  dashed = signal flow**.

### Screen by screen

| Screen | Current state |
|---|---|
| **Signal Universe** | Interactive object graph with selectable detail panel |
| **Scenario** | Two guided stories: Meridian onboarding and supplier price-change authority catch |
| **Objects** | Intake plus clickable object explorer |
| **Governance Map** | Stream flow cards with status and stuck markers |
| **Coverage** | Governance grid plus live access mismatches |
| **Bottlenecks & Risk** | Bottlenecks, impact statements, and approval routing |
| **Model & Audit** | Roles, boxes, monitoring lenses, and shadow log |

### Technical choice that matters
The runtime stays pure Python standard library. The demo UI uses Streamlit, pandas,
and `streamlit-agraph`; governance logic remains outside the UI so the interface can
change without rewriting the model.

---

## How the two plans interlock

P1 (intake → state machine → commit) gives the Governance Map and Signal Universe
live objects to render. The visual layer now sits on top of a working local spine,
which is why the demo can show the authority problem instead of merely describing
it.
