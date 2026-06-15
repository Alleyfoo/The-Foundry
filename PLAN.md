# The Foundry — Plan & Roadmap

Two plans: what is left to build (programside), and how it should look (visual).
Status as of 2026-06-14.

> **Current status:** P1, P2, the visual reskin, a guided Scenario, and a Governance
> Coverage view are all done. The app now tells the three founding ideas as three
> acts — **Map** (monitoring lenses), **Coverage** (the governance grid), **Flow**
> (bottlenecks / scenario). Target audience: large, audited, listed companies (the
> access mismatches are segregation-of-duties checks). It is a concept demo, not a
> product. Remaining: optional P3 (/tests).

---

## Where we are (baseline)

Built and working end-to-end:

- Object model — `schema/object_schema.json`, `boxes.json`, `roles.json`
- 21 sample objects across customer / item / supplier streams (`data/objects.json`)
- Pipeline (`runtime/foundry.py`) over a **static snapshot**: validate → triage
  (confidence band) → impact (bottlenecks + aging) → approval list → commit status
  → access mismatches → monitoring lenses
- Streamlit app, 7 tabs, with audit trail; MIT licensed; deployable

**The core limitation:** nothing moves. The app is a read-only X-ray of a fixed
object set. The deck's spine (Inputs → Triage → Boxes → Impact → Approval → Commit)
is *visualised* but not *executed* — you cannot drop in an input, approve a stuck
item, or commit something to truth. Closing that gap is the bulk of the work below.

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
      coverage, lenses) + an AppTest render smoke test. 23 tests.
      Run: `pip install -r requirements-dev.txt && pytest`.
- [x] **8. Housekeeping.** Removed the orphaned `definition_of_definition.json` (no
      code used it) and the stale `agent.md`; object-id generation done in P1.

**Status:** P1, P2, P3, the reskin, the Scenario, and Coverage are all done.

---

## Visual plan  ✅ DONE (commit 6e99b35)

> Reskinned to match the designer's mockup (`dashboard/`, gitignored). Light theme,
> Archivo type, navy/orange palette. Implemented in `ui.py` (tokens + CSS +
> component renderers) and wired through `streamlit_app.py`. Verified with Playwright
> screenshots against the mockup. The graphviz governance map was done with styled
> HTML flow cards instead — same effect, no extra dependency.

Make it look like the deck. The current UI is functional but plain (tables + emoji).

### Design system (do this first)
- Palette from the deck: navy `#0f2a4d`, blue, orange `#e8732a`, teal.
- Status legend, used everywhere: **green = flowing, amber = pending, red ! = stuck,
  dashed = signal flow**.

### Screen by screen

| Screen | Today | Target (deck reference) |
|---|---|---|
| **The Story** | plain tables | role **gravity ladder** (levels 5→1), slide 7; org-chart-vs-access side by side |
| **The Spine** | sidebar text line | the 6-step horizontal pipeline graphic, slide 1 |
| **Five Boxes** | text columns | 5 icon cards (meaning + examples + live counts), slide 6 |
| **Governance Map** ⭐ | per-stream tables | **centerpiece**: node→edge **flow diagrams** per stream (slide 4) — coloured arrows, `!` stuck marker, dashed signal flows |
| **Bottlenecks** | text list | red alert cards with aging meters |
| **Operational architecture** (optional new) | — | Experience → Foundry → SAP, slide 3 |

### Technical choice that matters
The Governance Map flow diagrams: start with **`st.graphviz_chart`** — define each
stream as a graph, colour edges by status. Looks like the deck with no custom
component work. HTML/CSS or a custom React component are fancier but far costlier.

---

## How the two plans interlock

P1 (intake → state machine → commit) gives the Governance Map live objects to
render. So: **persistence + state machine first, then the graphviz map on top.**
A reskin done before P1 would still be drawing a frozen snapshot.
