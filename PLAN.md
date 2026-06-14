# The Foundry — Plan & Roadmap

Two plans: what is left to build (programside), and how it should look (visual).
Status as of 2026-06-14.

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

### P1 — Make the spine actually run  (highest value)

- [ ] **1. Intake + triage.** Accept a raw input (text/form, e.g. "Customer X wants
      feature Y") and classify it into a box with a confidence score, creating a new
      object. The deck's opening move and the most compelling demo: drop chaos in,
      watch it get sorted.
- [ ] **2. Actions + state machine.** Objects transition
      `draft → active → pending → blocked → retired`. Approve / reject moves an
      object forward — the human-in-the-loop the deck calls first-class.
- [ ] **3. Commit to a system of record.** An approved object flips
      `commitment → truth`, gets a `system_of_record_ref`, and is written to a
      **persistent local store (SQLite = the "SAP" stand-in)**. Today commitment is
      just a label in seed data.

> Note: items 2 and 3 need persistence, so SQLite lands with them. `objects.json`
> becomes the seed; runtime state persists between runs.

### P2 — Make it analytically real

- [ ] **4. Impact statements.** Per change, generate "what this touches, what
      breaks, downstream risk" (we only count downstream now). The deck's Impact box.
- [ ] **5. Richer approval routing.** Route by confidence + risk + ownership
      together, not just "has an approver."
- [ ] **6. Lifecycle / disposition.** Archive / scrap / replacement-linked
      transitions (slide 2: Disposition & Feedback).

### P3 — Hardening for public

- [ ] **7. `/tests`.** Schema validation, pipeline outputs, mismatch detection.
      Verification is a manual AppTest run today.
- [ ] **8. Housekeeping.** Decide the fate of the orphaned
      `definition_of_definition.json`; add object-id generation for intake objects.

**Recommended sequence:** P1 in order (1 → 2 → 3), because it gives the visual
governance map something *live* to draw, then P2, then P3.

---

## Visual plan

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
